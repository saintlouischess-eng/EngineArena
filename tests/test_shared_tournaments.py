import asyncio
import contextlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import pytest
from aiohttp.test_utils import TestClient,TestServer
from arena.resources import usage,game_cost,fits
from arena.runner import Database,Runner
from arena.server import create_app
from arena.store import Store
from arena.shared_scheduler import FairShare
from arena.tournament_report import render
from test_core import profile,read_pgn

LIMITS={'cpu_budget':4,'memory_budget_mb':4096,'concurrency':4,'gpu_limits':{'gpu0':1}}


def setup(s,**kw):
    return s.queue_call('configure',s.queue_call('summary')['revision'],'parallel',LIMITS|kw)


def draft(s,name='Test',**kw):
    return s.create_tournament(name,[profile(name+' A',wait=.025),profile(name+' B',wait=.025)],
        {'cycles':3,'concurrency':3,'max_plies':8,'time_control':{'kind':'nodes','nodes':100},**kw},backup=False)['id']


def command(s,action,**kw):return s.queue_call('command',action,s.queue_call('summary')['revision'],**kw)


def manage(s,action,ids,**kw):return s.queue_call('manage',s.queue_call('summary')['revision'],action,ids,**kw)


def test_configuration_migration_validation_and_no_accidental_start(tmp_path):
    with contextlib.closing(Store(tmp_path)) as s:
        tid=draft(s);s.queue_call('add',[tid]);assert s.queue_call('summary')['execution_mode']=='sequential'
        for value in [0,-1,True,1.5,'4',None]:
            with pytest.raises(ValueError):setup(s,cpu_budget=value)
        for value in [{'gpu0':-1},{'gpu0':True},{' ':1},[]]:
            with pytest.raises(ValueError):setup(s,gpu_limits=value)
        setup(s);assert s.tournament(tid)['can_edit'] and not s.rows('SELECT * FROM games')
        old=s.queue_call('summary')['revision'];setup(s,cpu_budget=8)
        with pytest.raises(ValueError,match='changed'):s.queue_call('configure',old,'parallel',LIMITS)
        s.set_state(tid,'running')
        with pytest.raises(ValueError,match='drain'):s.queue_call('configure',s.queue_call('summary')['revision'],'sequential',LIMITS)
    with contextlib.closing(Store(tmp_path)) as s:
        assert s.queue_call('summary')['execution_mode']=='parallel'
        assert s.queue_call('summary')['resources']['cpu_budget']==8
        assert s.tournament(tid)['state']=='paused'


def test_bulk_actions_atomic_independent_and_timed_start(tmp_path):
    with contextlib.closing(Store(tmp_path)) as s:
        a,b=[draft(s,n) for n in ('Alpha','Beta')];s.queue_call('add',[a,b]);setup(s)
        command(s,'run',not_before=time.time()+3600);assert not s.queue_call('candidates')
        manage(s,'resume_selected',[a]);assert s.tournament(a)['state']=='running' and s.tournament(b)['can_edit']
        with pytest.raises(ValueError):manage(s,'set_limits',[a,'missing'],priority=4,concurrency=7)
        assert s.tournament(a)['settings']['concurrency']==3 and s.tournament(a)['queue']['priority']==2
        manage(s,'set_limits',[a,b],priority=4,concurrency=2)
        assert all(s.tournament(i)['settings']['concurrency']==2 for i in (a,b))
        manage(s,'pause_selected',[b]);assert s.tournament(a)['state']=='running' and s.tournament(b)['queue']['held']
        command(s,'pause');assert s.tournament(a)['state']=='draining' and s.queue_call('summary')['mode']=='paused'
        assert s.queue_call('page',0,'Al','', 'name','desc')['filtered_total']==1
        assert s.queue_call('page',0,'','paused')['items'][0]['tid']==b


def test_paging_sorting_and_large_waiting_list_does_not_materialize_games(tmp_path):
    with contextlib.closing(Store(tmp_path)) as s:
        for i in range(125):draft(s,f'Test {i:03}')
        s.queue_call('add',all_ready=True);setup(s)
        p=s.queue_call('page',50,'','', 'name','desc')
        assert p['filtered_total']==125 and len(p['items'])==50 and p['items'][0]['name']=='Test 074'
        command(s,'run');s.queue_call('tick');assert len(s.queue_call('candidates'))==125
        assert not s.rows('SELECT * FROM games')
        assert s.one('SELECT sum(started_once) n FROM tournaments')['n']==0


def test_ponder_and_snapshot_costs_are_counted_per_game():
    a=profile('A')|{'threads':3,'hash':10,'extra_memory_mb':5,'gpu_group':'gpu0'}
    b=profile('B')|{'threads':2,'hash':20,'extra_memory_mb':6}
    views=[{'white':a,'black':b,'ponder':False},{'white':a,'black':b,'ponder':True}]
    assert usage(views)=={'threads':8,'memory_mb':82,'gpu':{'gpu0':2}}
    views[0]['resource_cost']=game_cost(a,b,False);a['threads']=99
    assert usage(views)['threads']==104  # frozen first reservation + current second


def test_resource_time_priority_and_initial_spread():
    fair=FairShare();now=fair.last
    candidates=[{'id':'low','priority':1,'position':1},{'id':'high','priority':4,'position':2}]
    p=profile()|{'threads':2,'extra_memory_mb':0}
    fair.update([],candidates,LIMITS,now)
    fair.update([{'tid':'low','white':p,'black':p},{'tid':'high','white':p,'black':p}],candidates,LIMITS,now+10)
    assert fair.service['low']==pytest.approx(4*fair.service['high'])
    assert fair.order(candidates)[0]['id']=='high'


def test_gpu_reservation_leaves_unrelated_cpu_capacity_available():
    gpu={'threads':1,'memory_mb':100,'gpu':{'gpu0':1}}
    cpu={'threads':1,'memory_mb':50,'gpu':{}}
    limits=LIMITS|{'_reservation_cost':gpu}
    assert fits(cpu,gpu,limits)[0]
    assert not fits(gpu,gpu,limits)[0]
    assert not fits(cpu,{'threads':3,'memory_mb':200,'gpu':{'gpu0':1}},limits)[0]


def test_unfit_tournament_holds_independently_and_global_failure_drains(tmp_path):
    async def run():
        db=await Database().open(tmp_path);r=Runner(db)
        try:
            bad=await db.call('create_tournament','Too large',[profile('A')|{'threads':8},profile('B')|{'threads':8}],{'cycles':1,'concurrency':1,'max_plies':2},backup=False)
            good=await db.call('create_tournament','Fits',[profile('C',wait=.04),profile('D',wait=.04)],{'cycles':2,'concurrency':2,'max_plies':4},backup=False)
            await db.call('queue_call','add',[bad['id'],good['id']]);await db.call('queue_call','configure',(await db.call('queue_call','summary'))['revision'],'parallel',LIMITS)
            await db.call('queue_call','command','run',(await db.call('queue_call','summary'))['revision']);await r.start();deadline=time.monotonic()+15
            while time.monotonic()<deadline:
                assert not r.error,r.error
                if (await db.call('tournament',good['id']))['state']=='completed':break
                await asyncio.sleep(.02)
            assert (await db.call('snapshot',good['id']))['official_games']==4
            t=await db.call('tournament',bad['id']);assert t['state']=='paused' and t['queue']['held'] and 'CPU' in t['note']
            assert (await db.call('queue_call','summary'))['mode']=='running'
            async with r.lifecycle_lock:
                await db.call('queue_call','configure',(await db.call('queue_call','summary'))['revision'],'parallel',LIMITS|{'cpu_budget':8})
                await db.call('queue_call','manage',(await db.call('queue_call','summary'))['revision'],'resume_selected',[bad['id']])
                await db.call('queue_call','hold','Simulated saving failure')
            await asyncio.sleep(.3);assert not r.live and (await db.call('queue_call','summary'))['mode']=='paused'
            assert (await db.call('tournament',bad['id']))['state']=='paused'
        finally:await r.close()
    asyncio.run(run())


def test_finish_active_keeps_waiting_jobs_editable_and_manual_start_registers(tmp_path):
    with contextlib.closing(Store(tmp_path)) as s:
        a,b=[draft(s,n) for n in ('Active','Waiting')];s.queue_call('add',[a,b]);setup(s)
        manage(s,'resume_selected',[a]);command(s,'finish_current')
        assert [c['id'] for c in s.queue_call('candidates')]==[a] and s.tournament(b)['can_edit']
        s.execute("UPDATE tournaments SET state='completed' WHERE id=?",(a,));s.queue_call('tick')
        assert s.queue_call('summary')['mode']=='paused' and s.tournament(b)['can_edit']
        tid=draft(s,'Manual');s.queue_call('manual_action',tid,'start');s.set_state(tid,'running')
        assert s.tournament(tid)['queue'] is not None


def test_parallel_runner_mixed_costs_gpu_pause_changes_and_reports(tmp_path):
    async def run():
        db=await Database().open(tmp_path);r=Runner(db);samples=[]
        try:
            ids=[]
            for n,ponder,gpu,threads in [('GPU',False,True,1),('CPU',False,False,1),('Ponder',True,False,1)]:
                profiles=[profile(n+' A',wait=.06)|{'threads':threads,'extra_memory_mb':0,'gpu_group':'gpu0' if gpu else ''},profile(n+' B',wait=.06)|{'threads':threads,'extra_memory_mb':0}]
                t=await db.call('create_tournament',n,profiles,{'cycles':5,'concurrency':3,'ponder':ponder,'max_plies':8,'time_control':{'kind':'nodes','nodes':100}},backup=False);ids.append(t['id'])
            await db.call('queue_call','add',ids)
            await db.call('queue_call','configure',(await db.call('queue_call','summary'))['revision'],'parallel',LIMITS)
            await db.call('queue_call','command','run',(await db.call('queue_call','summary'))['revision'])
            await r.start()
            async def until(predicate,timeout=40):
                deadline=time.monotonic()+timeout
                while time.monotonic()<deadline:
                    assert not r.error,r.error
                    u=usage(r.live.values());assert u['threads']<=4 and u['gpu'].get('gpu0',0)<=1 and len(r.live)<=4
                    samples.append({v['tid'] for v in r.live.values()})
                    if await predicate():return
                    await asyncio.sleep(.02)
                raise AssertionError('Timed out: '+str(await db.call('queue_call','page'))+' '+str(r.scheduling_status))
            async def all_seen():return len(set.union(set(),*samples))==3
            await until(all_seen);assert any(len(v)>=2 for v in samples)
            async with r.lifecycle_lock:
                await db.call('queue_call','manage',(await db.call('queue_call','summary'))['revision'],'pause_selected',[ids[0]])
            kept={aid for aid,v in r.live.items() if v['tid']==ids[0]}
            async def drained():
                assert {aid for aid,v in r.live.items() if v['tid']==ids[0]}<=kept
                return (await db.call('tournament',ids[0]))['state']=='paused'
            await until(drained)
            assert (await db.call('queue_call','summary'))['mode']=='running'
            async with r.lifecycle_lock:
                await db.call('queue_call','manage',(await db.call('queue_call','summary'))['revision'],'resume_selected',[ids[0]])
                await db.call('queue_call','manage',(await db.call('queue_call','summary'))['revision'],'set_limits',[ids[0]],4,1)
            async def complete():return (await db.call('queue_call','summary'))['mode']=='completed'
            await until(complete,60)
            for tid in ids:
                snap=await db.call('snapshot',tid);assert snap['official_games']==10 and snap['complete_pairs']==5
                html=await asyncio.to_thread(render,db.store.path,tid,technical=False)
                assert 'Shared tournament scheduling' in html
            await db.call('export_pending');games=read_pgn((tmp_path/'games.pgn').read_text(encoding='utf-8'))
            assert len(games)==30 and len({g.headers['AttemptId'] for g in games})==30
            assert all(not g.errors for g in games)
            assert not await db.call('rows',"SELECT * FROM attempts WHERE reason IN ('timeout','illegal_move','crash')")
        finally:await r.close()
    asyncio.run(run())


def test_api_configure_limits_pause_all_and_validation(tmp_path):
    async def run():
        app=await create_app(tmp_path,'manager');db=app['db']
        async with TestClient(TestServer(app),headers={'X-Arena-Token':'manager'}) as client:
            ids=[(await db.call('create_tournament',n,[profile('A',wait=.1),profile('B',wait=.1)],{'cycles':8,'max_plies':8,'concurrency':2},backup=False))['id'] for n in ('A','B')]
            async def post(action,**kw):
                q=await (await client.get('/api/tournament-queue')).json()
                response=await client.post('/api/tournament-queue',json={'action':action,'revision':q['revision'],**kw})
                assert response.status==200,await response.text();return await response.json()
            await post('add',ids=ids);await post('configure',execution_mode='parallel',resources=LIMITS);await post('run')
            deadline=time.monotonic()+15
            while len({v['tid'] for v in app['runner'].live.values()})<2 and time.monotonic()<deadline:await asyncio.sleep(.02)
            assert len({v['tid'] for v in app['runner'].live.values()})==2
            await post('configure',execution_mode='parallel',resources=LIMITS|{'concurrency':1})
            await post('set_limits',ids=ids,priority=4,concurrency=2)
            for tid in ids:
                evidence=app['runner'].runtime.sessions[tid]['body']
                assert evidence['shared_scheduler']['limits']['concurrency']==1 and evidence['shared_scheduler']['priority']==4
                assert len(evidence['shared_scheduler_history'])>=3
            existing=set(app['runner'].live)
            while len(app['runner'].live)>1:
                assert set(app['runner'].live)<=existing;await asyncio.sleep(.02)
            await post('pause')
            while app['runner'].live:await asyncio.sleep(.02)
            await asyncio.sleep(.3)
            assert not app['runner'].live
            for tid in ids:assert (await db.call('tournament',tid))['state']=='paused'
    asyncio.run(run())


def test_abrupt_exit_preserves_shared_configuration_attempts_and_holds(tmp_path):
    script='''import sys,os,json
from arena.store import Store
s=Store(sys.argv[1]);ids=[s.create_tournament(n,[{'name':'A'},{'name':'B'}],{'cycles':2},backup=False)['id'] for n in ['A','B']]
s.queue_call('add',ids);s.queue_call('configure',s.queue_call('summary')['revision'],'parallel',json.loads(sys.argv[2]))
s.queue_call('manage',s.queue_call('summary')['revision'],'set_limits',ids,4,2)
s.queue_call('manage',s.queue_call('summary')['revision'],'resume_selected',ids)
for tid in ids:
 s.fill_queue(tid,4);g=s.claim(tid);s.finish(g['aid'],'1/2-1/2','test','committed');s.claim(tid)
s.queue_call('manage',s.queue_call('summary')['revision'],'pause_selected',[ids[1]])
s.export_pending();print(json.dumps(ids),flush=True);os._exit(0)
'''
    ids=json.loads(subprocess.check_output([sys.executable,'-c',script,str(tmp_path),json.dumps(LIMITS)],text=True))
    with contextlib.closing(Store(tmp_path)) as s:
        q=s.queue_call('page');assert q['execution_mode']=='parallel' and q['mode']=='paused' and q['resources']==LIMITS
        assert s.tournament(ids[1])['queue']['held'] and all(s.tournament(t)['queue']['priority']==4 for t in ids)
        assert not s.queue_call('candidates')
        assert s.one("SELECT count(*) n FROM attempts WHERE reason='interrupted'")['n']==2
        for tid in ids:assert s.snapshot(tid)['official_games']==1
        assert len(read_pgn((tmp_path/'games.pgn').read_text(encoding='utf-8')))==2


def test_reservation_eventually_admits_large_game(tmp_path):
    async def run():
        db=await Database().open(tmp_path);r=Runner(db)
        try:
            ids=[]
            for name,threads in [('Small',1),('Large',4)]:
                p=[profile(name+str(i),wait=.04)|{'threads':threads,'extra_memory_mb':0} for i in range(2)]
                t=await db.call('create_tournament',name,p,{'cycles':100,'concurrency':4,'cpu_budget':4,'max_plies':12},backup=False);ids.append(t['id'])
            await db.call('queue_call','add',ids);await db.call('queue_call','configure',(await db.call('queue_call','summary'))['revision'],'parallel',LIMITS)
            await db.call('queue_call','command','run',(await db.call('queue_call','summary'))['revision']);await r.start()
            seen=set();deadline=time.monotonic()+20
            while time.monotonic()<deadline and len(seen)<2:
                assert not r.error,r.error;assert usage(r.live.values())['threads']<=4
                seen.update(v['tid'] for v in r.live.values());await asyncio.sleep(.02)
            assert seen==set(ids)
        finally:await r.close()
    asyncio.run(run())
