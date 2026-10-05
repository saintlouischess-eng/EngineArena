import asyncio
import contextlib
import json
import subprocess
import sys
import time
import pytest
from arena.store import Store
from arena.runner import Database,Runner
from test_core import profile,read_pgn


def definition(**kw):
    return {'kind':'multistage','groups':[[0,1,2],[3,4,5]],'initial_format':'round_robin','final_format':'knockout','advance':2,
            'initial_cycles':1,'final_cycles':1,'initial_rounds':2,**kw}


def create(s,d=None,n=6,**settings):
    t=s.create_tournament('Source',[{'name':str(i)} for i in range(n)],{'format':'round_robin','cycles':1,**settings},backup=False)
    return s.event_call('create','Test event',t['id'],d or definition())


def command(s,eid,action):return s.event_call('command',eid,action,s.event_call('detail',eid)['revision'])


def play_current(s,eid):
    e=s.event_call('detail',eid)
    if not e['active_tid']:return
    tid=e['active_tid'];t=s.tournament(tid)
    if t['state']!='running':return
    s.fill_queue(tid,64)
    while g:=s.claim(tid):s.finish(g['aid'],'1-0' if g['white']<g['black'] else '0-1','fixture')
    t=s.tournament(tid)
    if t['settings']['format'] not in ('knockout','swiss') and t['cursor']*2>=t['total']:
        s.execute("UPDATE tournaments SET state='completed' WHERE id=?",(tid,))


def drive(s,eid):
    command(s,eid,'run')
    for _ in range(100):
        s.event_call('tick');play_current(s,eid)
        if s.event_call('detail',eid)['state']=='completed':return s.event_call('detail',eid)
    raise AssertionError(s.event_call('detail',eid))


@pytest.mark.parametrize('final',['knockout','round_robin'])
def test_groups_qualify_counts_stage_stats_and_preserved_template(tmp_path,final):
    with contextlib.closing(Store(tmp_path)) as s:
        e=create(s,definition(final_format=final));assert e['regular_games']==(18 if final=='knockout' else 24)
        result=drive(s,e['id']);assert result['official_games']==e['regular_games']
        assert result['decisions'][0]['qualified']==[0,3,1,4]
        assert len(result['children'])==3
        for c in result['children']:
            assert not s.tournament(c['tid'])['can_edit']
            assert s.snapshot(c['tid'])['complete_pairs']==c['total']//2
        assert s.one("SELECT count(*) n FROM tournaments WHERE name='Source' AND started_once=0")['n']==1


def test_swiss_to_ko_and_final_control_override(tmp_path):
    with contextlib.closing(Store(tmp_path)) as s:
        e=create(s,definition(groups=[list(range(4))],initial_format='swiss',initial_rounds=3,final_time_control={'kind':'nodes','nodes':77}),n=4)
        e=drive(s,e['id']);final=s.tournament(e['children'][-1]['tid'])
        assert final['settings']['time_control']['nodes']==77 and e['official_games']==14


def test_replacement_requires_explicit_event_invalidation(tmp_path):
    with contextlib.closing(Store(tmp_path)) as s:
        e=drive(s,create(s)['id']);old_final=e['children'][-1]['tid'];tid=e['children'][0]['tid']
        g=s.one('SELECT id FROM games WHERE tid=? ORDER BY number',(tid,))
        r=s.requeue(tid,[g['id']],mode='replacement');assert r['dependency'] and r['queued']==0
        assert s.requeue(tid,[g['id']],mode='replacement',invalidate=True)['queued']==1
        assert not s.one('SELECT valid FROM event_children WHERE tid=?',(old_final,))['valid']
        assert s.snapshot(old_final)['official_games']==6
        with pytest.raises(ValueError,match='event'):s.queue_call('manual_action',old_final,'start')
        e=drive(s,e['id']);assert len(e['children'])==4 and e['official_games']==18
        assert s.one('SELECT count(*) n FROM attempts WHERE gid=?',(g['id'],))['n']==2


def test_queue_and_stage_ownership(tmp_path):
    with contextlib.closing(Store(tmp_path)) as s:
        e=create(s);command(s,e['id'],'run');s.event_call('tick');c=s.event_call('detail',e['id'])['children'][0]
        with pytest.raises(ValueError):s.queue_call('add',[c['tid']])
        with pytest.raises(ValueError):s.queue_call('manual_action',c['tid'],'start')
        command(s,e['id'],'pause');assert s.event_call('detail',e['id'])['state']=='paused'
        command(s,e['id'],'retire')
        with pytest.raises(ValueError):command(s,e['id'],'run')


def test_diagnostic_replay_keeps_event_decisions_and_official_scores(tmp_path):
    with contextlib.closing(Store(tmp_path)) as s:
        e=drive(s,create(s)['id']);tid=e['children'][0]['tid'];g=s.one('SELECT id FROM games WHERE tid=?',(tid,))
        before=e['decisions'];s.requeue(tid,[g['id']],mode='diagnostic')
        assert s.tournament(tid)['event']['can_diagnostic_start']
        s.queue_call('manual_action',tid,'start');s.set_state(tid,'running');game=s.claim(tid);s.finish(game['aid'],'1/2-1/2','fixture')
        assert s.event_call('detail',e['id'])['decisions']==before
        assert s.event_call('detail',e['id'])['official_games']==18


def test_advancement_is_atomic_if_child_creation_fails(tmp_path,monkeypatch):
    with contextlib.closing(Store(tmp_path)) as s:
        e=create(s);command(s,e['id'],'run');original=s.insert_tournament;count=0
        def fail(name,prepared):
            nonlocal count
            count+=1
            if count==2:raise RuntimeError('Injected stage write interruption')
            return original(name,prepared)
        monkeypatch.setattr(s,'insert_tournament',fail)
        with pytest.raises(RuntimeError):s.event_call('tick')
        assert not s.event_call('detail',e['id'])['children']
        assert s.one('SELECT count(*) n FROM tournaments')['n']==1
        monkeypatch.setattr(s,'insert_tournament',original);s.event_call('tick')
        assert len(s.event_call('detail',e['id'])['children'])==2


def test_large_field_creates_only_groups_and_pages_children(tmp_path):
    with contextlib.closing(Store(tmp_path)) as s:
        groups=[list(range(i,i+100)) for i in range(0,10000,100)]
        e=create(s,definition(groups=groups,advance=1),n=10000)
        assert e['regular_games']==990198
        command(s,e['id'],'run');s.event_call('tick')
        assert not s.one('SELECT 1 FROM games')
        assert len(s.event_call('detail',e['id'])['children'])==50
        assert len(s.event_call('detail',e['id'],0,True)['children'])==100


def test_deletion_requires_retirement_and_scrubs_event_references(tmp_path):
    with contextlib.closing(Store(tmp_path)) as s:
        e=drive(s,create(s)['id'])
        with pytest.raises(ValueError,match='Retire'):s.delete_tournament(e['children'][0]['tid'],e['children'][0]['name'])
        command(s,e['id'],'retire');s.backup()
        for c in e['children']:s.delete_tournament(c['tid'],c['name'])
        assert not s.one('SELECT 1 FROM events WHERE id=?',(e['id'],))
        assert not s.one('SELECT 1 FROM event_children')


def test_forced_termination_recovers_current_stage_and_committed_games(tmp_path):
    script='''import os,sys
from arena.store import Store
s=Store(sys.argv[1]);t=s.create_tournament('Source',[{'name':str(i)} for i in range(4)],{'format':'round_robin'},backup=False)
e=s.event_call('create','Event',t['id'],{'groups':[[0,1],[2,3]],'initial_format':'round_robin','final_format':'knockout','advance':1})
s.event_call('command',e['id'],'run',e['revision']);s.event_call('tick');s.event_call('tick');tid=s.event_call('detail',e['id'])['active_tid'];s.fill_queue(tid,4)
g=s.claim(tid);s.finish(g['aid'],'1-0','fixture');s.claim(tid);s.export_pending();print(e['id'],flush=True);os._exit(0)
'''
    eid=subprocess.check_output([sys.executable,'-c',script,str(tmp_path)],text=True).strip()
    with contextlib.closing(Store(tmp_path)) as s:
        e=s.event_call('detail',eid);assert e['state']=='paused' and e['official_games']==1
        assert s.one("SELECT count(*) n FROM attempts WHERE reason='interrupted'")['n']==1
        assert drive(s,eid)['official_games']==6
        s.export_pending();assert len(read_pgn((tmp_path/'games.pgn').read_text(encoding='utf-8')))==6


def test_actual_uci_worker_runs_stages_and_node_only_pgn(tmp_path):
    async def run():
        db=await Database().open(tmp_path);r=Runner(db)
        try:
            t=await db.call('create_tournament','Source',[profile(str(i),wait=.001) for i in range(4)],{'format':'round_robin','cycles':1,'concurrency':2,'cpu_budget':2,'max_plies':4,'time_control':{'kind':'nodes','nodes':77}})
            e=await db.call('event_call','create','Worker event',t['id'],definition(groups=[[0,1],[2,3]],advance=1,final_format='round_robin'))
            await db.call('event_call','command',e['id'],'run',e['revision']);await r.start();deadline=time.monotonic()+20
            while time.monotonic()<deadline:
                assert not r.error,r.error
                e=await db.call('event_call','detail',e['id'])
                assert len({v['tid'] for v in r.live.values()})<=1
                if e['state']=='completed':break
                await asyncio.sleep(.02)
            assert e['state']=='completed' and e['official_games']==6
            await db.call('export_pending');games=read_pgn((tmp_path/'games.pgn').read_text(encoding='utf-8'));assert len(games)==6
        finally:await r.close()
    asyncio.run(run())
