import asyncio
import contextlib
import csv
import io
import sys
from pathlib import Path

import pytest
from aiohttp.test_utils import TestClient,TestServer

from arena.progress import Progress
from arena.server import create_app
from arena.standings import read_snapshot,SORTS
from arena.stats import summarize,critical_value
from arena.store import Store
from arena.tournament_report import render


def population(store,n=120):
    t=store.create_tournament('Sorting fixture',[{'name':f'Engine {n-i:04}', 'path':sys.executable} for i in range(n)],{'format':'round_robin','cycles':1,'paired':False})
    with store.tx():
        for i in range(n-1):
            store.db.execute('UPDATE aggregates SET w=?,d=3,l=2 WHERE tid=? AND a=? AND b=-1',(i,t['id'],i))
            store.db.execute('UPDATE rankings SET score=?,wins=? WHERE tid=? AND slot=?',(i+1.5,i,t['id'],i))
    return t


def test_sort_all_participants_before_paging_and_keep_official_rank(tmp_path):
    with contextlib.closing(Store(tmp_path)) as store:
        t=population(store)
        ranked=store.snapshot(t['id'],0,120)['standings'];ranks={s['slot']:s['rank'] for s in ranked}
        for key in SORTS:
            for direction in ('asc','desc'):
                full=read_snapshot(store.path,t['id'],0,120,key,direction,99)['standings']
                pages=[read_snapshot(store.path,t['id'],o,50,key,direction,99)['standings'] for o in (0,50,100)]
                assert [r['slot'] for page in pages for r in page]==[r['slot'] for r in full]
                assert all(r['rank']==ranks[r['slot']] for r in full)
                if key in ('elo','los','ci','score_pct','draw_pct'):assert full[-1]['slot']==119
        assert read_snapshot(store.path,t['id'],0,50,'name','asc')['standings'][0]['name']=='Engine 0001'
        assert read_snapshot(store.path,t['id'],0,50,'wins','desc')['standings'][0]['wins']==118
        with pytest.raises(ValueError):store.snapshot(t['id'],sort='DROP TABLE rankings')


def test_elo_sort_handles_infinities_and_missing_selfplay(tmp_path):
    with contextlib.closing(Store(tmp_path)) as store:
        t=population(store,4)
        with store.tx():
            store.db.execute('UPDATE aggregates SET w=4,d=0,l=0 WHERE tid=? AND a=0',(t['id'],))
            store.db.execute('UPDATE aggregates SET w=0,d=0,l=4 WHERE tid=? AND a=1',(t['id'],))
        asc=store.snapshot(t['id'],sort='elo')['standings'];desc=store.snapshot(t['id'],sort='elo',direction='desc')['standings']
        assert asc[0]['elo']=='-infinity' and desc[0]['elo']=='+infinity'
        assert asc[-1]['elo'] is None and desc[-1]['elo'] is None
        single=store.create_tournament('Self',[{'name':'Self'}],{'format':'self_play','cycles':1})
        row=store.snapshot(single['id'],confidence=99)['standings'][0]
        assert row['elo'] is None and row['ci'] is None and row['ci_conservative'] is None


@pytest.mark.parametrize('paired',[False,True])
def test_confidence_levels_change_bounds_not_elo_los_or_legacy_fields(paired):
    args=(70,60,50,[8,12,25,30,15] if paired else None)
    low,usual,high=(summarize(*args,confidence=c) for c in (80,95,99.9))
    for key in ('ci','ci_conservative'):
        assert high[key][0]<usual[key][0]<low[key][0]<low[key][1]<usual[key][1]<high[key][1]
    assert low['elo']==high['elo'] and low['los']==high['los']
    assert low['ci95']==high['ci95']==usual['ci']
    assert critical_value(90)==pytest.approx(1.6448536269514722)
    assert critical_value(99)==pytest.approx(2.5758293035489004)
    assert summarize(0,0,0,confidence=99)['confidence']==99
    for bad in (0,49.99,100,99.999,float('nan'),True):
        with pytest.raises(ValueError):summarize(*args,confidence=bad)


def test_delete_clones_preserves_files_snapshots_and_atomic_selection(tmp_path):
    with contextlib.closing(Store(tmp_path/'data')) as store:
        executable=tmp_path/'engine.exe';executable.write_bytes(b'fixture executable')
        profiles=[store.save_profile({'name':name,'path':str(executable)}) for name in ('Original','Clone','Keep')]
        t=store.create_tournament('Immutable participants',profiles[:2],{'cycles':1})
        before=[store.participant(t['id'],i) for i in range(2)]
        with pytest.raises(ValueError):store.delete_profiles([profiles[0]['id'],'missing'])
        assert store.profiles()['total']==3
        assert store.profile_deletion_preview([p['id'] for p in profiles[:2]])['count']==2
        deleted=store.delete_profiles([profiles[0]['id'],profiles[1]['id'],profiles[1]['id']])
        assert deleted['count']==2 and store.profiles()['total']==1 and executable.exists()
        assert before==[store.participant(t['id'],i) for i in range(2)]
        store.set_state(t['id'],'running');store.fill_queue(t['id'],2);game=store.claim(t['id'])
        store.finish(game['aid'],'1/2-1/2','fixture')
        assert store.snapshot(t['id'])['official_games']==1
    with contextlib.closing(Store(tmp_path/'data')) as reopened:assert reopened.profiles()['total']==1


def test_progress_pause_resume_replacement_queued_and_early_stop():
    p=Progress();t={'id':'a','state':'running','total':100,'official_games':0}
    assert p.observe(t,0,now=100)['status']=='waiting'
    assert p.observe(t,2,now=1000)['eta_seconds'] is None
    t['official_games']=2
    r=p.observe(t,2,now=1010);assert r['percent']==2 and r['eta_seconds']==490
    assert p.observe(t|{'state':'paused'},0,now=2000)['eta_seconds'] is None
    assert p.observe(t,2,now=3000)['eta_seconds'] is None
    t['official_games']=4;assert p.observe(t,2,now=3010)['eta_seconds']==480
    assert p.observe(t|{'official_games':1},2,now=3011)['eta_seconds'] is None
    assert Progress().observe(t,2,now=9999)['eta_seconds'] is None
    finished=p.observe(t|{'official_games':100,'state':'completed'},0,now=3020)
    assert finished['percent']==100 and finished['eta_seconds']==0
    early=p.observe(t|{'state':'completed'},0,now=3030)
    assert early['percent']==4 and early['status']=='ended_early'
    assert p.observe(t|{'official_games':100},1,now=3040)['status']=='replays'


def test_http_sort_export_confidence_and_profile_delete(tmp_path):
    async def run():
        app=await create_app(tmp_path,'results');runner=app['runner'];runner.scheduler.cancel()
        with contextlib.suppress(asyncio.CancelledError):await runner.scheduler
        db=app['db'];t=await db.call('create_tournament','HTTP',[{'name':'Zed'},{'name':'Alpha'}],{'cycles':1,'paired':False})
        await db.call('set_state',t['id'],'running');await db.call('fill_queue',t['id'],2)
        g=await db.call('claim',t['id']);await db.call('finish',g['aid'],'1/2-1/2','fixture')
        p=await db.call('save_profile',{'name':'Disposable clone','path':sys.executable})
        async with TestClient(TestServer(app),headers={'X-Arena-Token':'results'}) as client:
            r=await client.get(f'/api/tournaments/{t["id"]}?sort=name&confidence=90');v=await r.json()
            assert r.status==200 and v['standings'][0]['name']=='Alpha'
            assert v['standings'][0]['confidence']==90 and v['progress']['percent']==100
            r=await client.get(f'/api/export/{t["id"]}/csv?sort=name&confidence=90');rows=list(csv.DictReader(io.StringIO(await r.text())))
            assert rows[0]['name']=='Alpha' and rows[0]['confidence']=='90.0'
            r=await client.get(f'/api/tournaments/{t["id"]}/h2h/0?confidence=99');assert (await r.json())['items'][0]['confidence']==99
            r=await client.get(f'/api/tournaments/{t["id"]}/crosstable?confidence=80');assert (await r.json())['cells'][0]['confidence']==80
            for query in ('sort=bad','direction=bad','confidence=100','method=bad'):
                assert (await client.get(f'/api/tournaments/{t["id"]}?{query}')).status==400
            assert (await client.post('/api/profiles/delete',json={'ids':[p['id']]})).status==400
            preview=await client.post('/api/profiles/delete',json={'ids':[p['id']],'preview':True});assert (await preview.json())['names']==['Disposable clone']
            deleted=await client.post('/api/profiles/delete',json={'ids':[p['id']],'confirmed':True});assert (await deleted.json())['count']==1
            assert (await client.get('/assets/results.js')).status==200
        assert 'Normal 90% CI' in render(tmp_path/'arena.sqlite3',t['id'],90)
    asyncio.run(run())


def test_confidence_propagates_through_cached_curves_and_pool(tmp_path):
    from arena.ratings import pool_report
    from arena.trends import tournament_series
    with contextlib.closing(Store(tmp_path)) as store:
        t=store.create_tournament('Confidence propagation',[{'name':'A'},{'name':'B'}],{'cycles':10})
        tid=t['id'];store.set_state(tid,'running');store.fill_queue(tid,20)
        for i in range(20):
            g=store.claim(tid)
            score=(1,.5,0,.5,1)[i//2%5]
            result='1/2-1/2' if score==.5 else '1-0' if (g['white']==0)==(score==1) else '0-1'
            store.finish(g['aid'],result,'fixture')
        for calculate,get in ((pool_report,lambda r:r['items'][1]),(tournament_series,lambda r:r['points'][-1])):
            low=get(calculate(store.path,tid,confidence=80))
            high=get(calculate(store.path,tid,confidence=99))
            assert high['ci'][0]<low['ci'][0]<low['ci'][1]<high['ci'][1]
            assert high['ci95']==low['ci95'] and high['los']==low['los']
            assert get(calculate(store.path,tid,confidence=80))==low


def test_slow_standings_read_does_not_block_result_commit(tmp_path,monkeypatch):
    import threading
    import arena.standings
    entered=threading.Event();release=threading.Event();original=arena.standings.read_snapshot
    def slow(*args,**kwargs):
        entered.set()
        assert release.wait(5)
        return original(*args,**kwargs)
    monkeypatch.setattr(arena.standings,'read_snapshot',slow)
    async def run():
        app=await create_app(tmp_path,'background');runner=app['runner'];runner.scheduler.cancel()
        with contextlib.suppress(asyncio.CancelledError):await runner.scheduler
        db=app['db'];t=await db.call('create_tournament','Nonblocking',[{'name':'A'},{'name':'B'}],{'cycles':1})
        await db.call('set_state',t['id'],'running');await db.call('fill_queue',t['id'],2);g=await db.call('claim',t['id'])
        async with TestClient(TestServer(app),headers={'X-Arena-Token':'background'}) as client:
            request=asyncio.create_task(client.get(f'/api/tournaments/{t["id"]}?sort=los'))
            try:
                assert await asyncio.to_thread(entered.wait,3)
                await asyncio.wait_for(db.call('finish',g['aid'],'1/2-1/2','fixture'),2)
                assert not request.done()
            finally:release.set()
            response=await request
            assert (await response.json())['official_games']==1
    asyncio.run(run())
