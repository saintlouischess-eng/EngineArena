"""League season finals, reproducible openings and shared-budget lifecycle."""
import asyncio
import contextlib
import json
import os
import subprocess
import sys
import time

import chess
import pytest
from arena.store import Store
from arena.runner import Database,Runner
from arena.resources import usage
from test_core import profile,read_pgn
from test_events import command


def definition(**kw):
    return dict(kind='league',groups=[[0,1],[2,3],[4,5]],movement=[1,1],seasons=2,
        initial_cycles=1,season_openings='advance',execution_mode='parallel',
        resources={'cpu_budget':2,'memory_budget_mb':4096,'concurrency':3,'gpu_limits':{}},
        championship={'enabled':True,'games':4,'tiebreak_games':2,'controls':[
            {'kind':'fischer','seconds':60,'increment':1},{'kind':'fischer','seconds':30,'increment':.5}]},**kw)


def create(s,d=None):
    openings=[]
    for move in chess.Board().legal_moves:
        b=chess.Board();b.push(move);openings.append({'fen':b.fen(),'name':move.uci(),'moves':[move.uci()],'start_fen':chess.STARTING_FEN})
    t=s.create_tournament('Template',[{'name':str(i)} for i in range(6)],
        {'format':'round_robin','cycles':1,'opening_order':'shuffle','opening_policy':'pair','seed':42},openings,backup=False)
    return s.event_call('create','Season final test',t['id'],d or definition())


def finish_active(s,eid,ties=0):
    for c in s.event_call('detail',eid,0,True)['children']:
        if not c['valid'] or c['state']!='running':continue
        tid=c['tid'];s.fill_queue(tid,64)
        while g:=s.claim(tid):
            # Regular season is won by the lower seed; the championship is won
            # by the other finalist only after the requested number of tied stages.
            stage=g['opening'].get('playoff_stage',0)
            result='1/2-1/2' if c['role']=='championship' and stage<ties else ('1-0' if (g['white']>g['black'])==(c['role']=='championship') else '0-1')
            s.finish(g['aid'],result,'fixture')
        t=s.tournament(tid)
        if c['role']!='championship' and t['cursor']*2>=t['total']:s.execute("UPDATE tournaments SET state='completed' WHERE id=?",(tid,))


def drive(s,eid,ties=0):
    if s.event_call('detail',eid)['state']!='running':command(s,eid,'run')
    for _ in range(150):
        s.event_call('tick');finish_active(s,eid,ties)
        e=s.event_call('detail',eid,0,True)
        if e['state']=='completed':return e
    raise AssertionError(e)


def test_final_after_divisions_and_two_tiebreaks_report_counts_openings(tmp_path):
    with contextlib.closing(Store(tmp_path)) as s:
        e=create(s);assert e['regular_games']==20 and e['unbounded']
        command(s,e['id'],'run');s.event_call('tick');s.event_call('tick')
        e=s.event_call('detail',e['id']);assert len([c for c in e['children'] if c['state']=='running'])==3
        assert not e['decisions']
        e=drive(s,e['id'],ties=2)
        assert e['official_games']==e['scheduled_games']==28 and e['regular_games']==20
        assert len(e['decisions'])==2
        first=e['decisions'][0]
        assert first['regular_winner']=='0' and first['champion']=='1'
        assert first['next_groups']==[[0,2],[1,4],[3,5]]  # final loser still stays; winner relegated
        assert first['championship']['games']==8
        assert first['championship']['matches'][0]['stages'][-1]['time_control']['seconds']==30
        assert first['next_opening_offset']==5
        for c in e['children']:
            t=s.tournament(c['tid']);offset=t['settings']['event_opening_offset']
            expected=(0 if c['stage']==0 else 5)+(1 if c['role']=='championship' else 0)
            assert offset==expected
            assert s.snapshot(c['tid'])['complete_pairs']==c['total']//2
            for pair in s.rows('SELECT pair_no,opening FROM games WHERE tid=? AND leg=0 ORDER BY pair_no',(c['tid'],)):
                o=json.loads(pair['opening']);assert o['assignment']==expected+pair['pair_no']
        s.export_pending();pgns=read_pgn((tmp_path/'games.pgn').read_text(encoding='utf-8'))
        assert len(pgns)==28 and len({p.headers['AttemptId'] for p in pgns})==28
        assert sum('Championship final' in p.headers['Event'] for p in pgns)==16
        command(s,e['id'],'next_season');e=s.event_call('detail',e['id'])
        assert e['regular_games']==30 and e['scheduled_games']==38


@pytest.mark.parametrize('role',['division','championship'])
def test_correction_archives_dependents_and_keeps_original_attempts(tmp_path,role):
    with contextlib.closing(Store(tmp_path)) as s:
        e=drive(s,create(s)['id']);before=s.one('SELECT count(*) n FROM attempts')['n']
        c=next(c for c in e['children'] if c['stage']==0 and c['role']==role)
        game=s.one('SELECT id,official FROM games WHERE tid=? ORDER BY number',(c['tid'],))
        assert s.requeue(c['tid'],[game['id']],mode='replacement')['dependency']
        s.requeue(c['tid'],[game['id']],mode='replacement',invalidate=True)
        finals=s.rows("SELECT valid FROM event_children WHERE eid=? AND stage=0 AND role='championship'",(e['id'],))
        assert finals[0]['valid']==(role=='championship')
        assert s.one('SELECT count(*) n FROM attempts')['n']==before
        e=drive(s,e['id']);assert e['official_games']==e['scheduled_games']==20
        assert s.one('SELECT id FROM attempts WHERE id=?',(game['official'],))
        assert len([c for c in e['children'] if c['valid']])==8
        assert s.one('SELECT count(*) n FROM attempts WHERE gid=?',(game['id'],))['n']==2


def test_reproducible_fresh_seasons_and_wrap_only_after_exhaustion(tmp_path):
    with contextlib.closing(Store(tmp_path)) as s:
        first=drive(s,create(s)['id']);second=drive(s,create(s)['id'])
        def selections(e):
            return [[json.loads(g['opening'])['fen'] for g in s.rows('SELECT opening FROM games WHERE tid=? AND leg=0 ORDER BY pair_no',(c['tid'],))] for c in e['children']]
        assert selections(first)==selections(second)
        chosen=[json.loads(g['opening']) for c in first['children'] if c['bucket']==0 or c['role']=='championship'
            for g in s.rows('SELECT opening FROM games WHERE tid=? AND leg=0 ORDER BY pair_no',(c['tid'],))]
        assert len({o['fen'] for o in chosen})==len(chosen)


@pytest.mark.parametrize('change',[{'championship':{'enabled':True,'games':3}}, {'championship':{'enabled':True,'games':True}},
    {'championship':{'enabled':True,'tiebreak_games':0}},{'championship':{'enabled':True,'controls':[{}]}},
    {'resources':{'cpu_budget':0}},{'execution_mode':'bad'},{'season_openings':'bad'}])
def test_invalid_configuration_has_no_partial_event(tmp_path,change):
    with contextlib.closing(Store(tmp_path)) as s:
        with pytest.raises(ValueError):create(s,definition()|change)
        assert not s.one('SELECT 1 FROM events')


def test_64_engine_preview_includes_finals_and_no_materialized_games(tmp_path):
    with contextlib.closing(Store(tmp_path)) as s:
        t=s.create_tournament('64 engines',[{'name':str(i)} for i in range(64)],{'format':'round_robin','cycles':1},backup=False)
        d=definition()|{'groups':[list(range(i,i+8)) for i in range(0,64,8)],'movement':[1]*7,
            'championship':{'enabled':True,'games':8}}
        e=s.event_call('create','64 engine league',t['id'],d)
        assert e['regular_games']==912 and not s.one('SELECT 1 FROM games')
        assert not e['children']


def test_forced_termination_during_final_recovers_without_duplicate_results(tmp_path):
    script='''import os,sys
sys.path.insert(0,'tests')
from test_league_update import create,finish_active
from test_events import command
from arena.store import Store
s=Store(sys.argv[1]);e=create(s);command(s,e['id'],'run')
for _ in range(5):
 s.event_call('tick')
 finals=s.rows("SELECT t.id FROM event_children c JOIN tournaments t ON t.id=c.tid WHERE role='championship' AND t.state='running'")
 if finals:
  tid=finals[0]['id'];s.fill_queue(tid,8);g=s.claim(tid);s.finish(g['aid'],'1/2-1/2','fixture');s.claim(tid);s.export_pending();print(e['id'],flush=True);os._exit(0)
 finish_active(s,e['id'])
raise RuntimeError('No final started')
'''
    eid=subprocess.check_output([sys.executable,'-c',script,str(tmp_path)],text=True).strip()
    with contextlib.closing(Store(tmp_path)) as s:
        e=s.event_call('detail',eid);assert e['state']=='paused' and e['official_games']==7
        saved=s.rows('SELECT id,result FROM attempts WHERE ended IS NOT NULL AND result<>\'*\'')
        assert s.one("SELECT count(*) n FROM attempts WHERE reason='interrupted'")['n']==1
        e=drive(s,eid);assert e['official_games']==20
        assert all(s.one('SELECT result FROM attempts WHERE id=?',(a['id'],))['result']==a['result'] for a in saved)
        s.export_pending();assert len(read_pgn((tmp_path/'games.pgn').read_text(encoding='utf-8')))==20
        assert len(read_pgn((tmp_path/'interrupted.pgn').read_text(encoding='utf-8')))==1


def test_parallel_runner_shares_budget_drains_and_resumes_all_divisions(tmp_path):
    async def run():
        db=await Database().open(tmp_path);r=Runner(db)
        try:
            profiles=[profile(str(i),wait=.04) for i in range(6)]
            profiles[0]['gpu_group']=profiles[2]['gpu_group']='gpu0'
            t=await db.call('create_tournament','Source',profiles,{'format':'round_robin','cycles':2,'concurrency':3,'cpu_budget':3,'max_plies':6,'time_control':{'kind':'nodes','nodes':77}},backup=False)
            d=definition()|{'championship':{'enabled':False},'seasons':1,'initial_cycles':2}
            d['resources']['gpu_limits']={'gpu0':1}
            e=await db.call('event_call','create','Parallel league',t['id'],d);eid=e['id']
            q_before=await db.call('queue_call','summary')
            await db.call('event_call','command',eid,'run',e['revision']);await r.start()
            deadline=time.monotonic()+25;overlap=False;paused=False
            while time.monotonic()<deadline:
                assert not r.error,r.error
                used=usage(r.live.values());assert used['threads']<=2 and used['memory_mb']<=4096 and used['gpu'].get('gpu0',0)<=1
                overlap|=len({g['tid'] for g in r.live.values()})>1
                e=await db.call('event_call','detail',eid)
                if overlap and not paused:
                    async with r.lifecycle_lock:
                        e=await db.call('event_call','set_resources',eid,e['revision'],d['resources']|{'cpu_budget':1,'concurrency':1})
                    async with r.lifecycle_lock:await db.call('event_call','command',eid,'pause',e['revision'])
                    while r.tasks:await asyncio.sleep(.02)
                    for _ in range(20):
                        if not await db.call('one',"SELECT 1 FROM tournaments WHERE state='draining'"):break
                        await asyncio.sleep(.1)
                    assert not await db.call('one',"SELECT 1 FROM tournaments WHERE state IN ('running','draining')")
                    e=await db.call('event_call','detail',eid)
                    async with r.lifecycle_lock:await db.call('event_call','command',eid,'run',e['revision'])
                    paused=True
                if paused:assert len(r.tasks)<=1
                if e['state']=='completed':break
                await asyncio.sleep(.02)
            assert e['state']=='completed' and e['official_games']==12 and overlap and paused
            assert (await db.call('queue_call','summary'))['resources']==q_before['resources']
        finally:await r.close()
    asyncio.run(run())


def test_legacy_schema_migration_keeps_results_and_rules(tmp_path):
    import sqlite3
    from test_events import create as old_create,drive as old_drive
    from test_leagues import league
    with contextlib.closing(Store(tmp_path)) as s:
        e=old_drive(s,old_create(s,league())['id']);s.export_pending()
        saved=s.rows('SELECT id,official FROM games ORDER BY id');pgn=(tmp_path/'games.pgn').read_bytes()
    with sqlite3.connect(tmp_path/'arena.sqlite3') as db:
        for table,col in [('events','execution_mode'),('events','resources'),('event_children','role'),('event_children','activated')]:db.execute(f'ALTER TABLE {table} DROP COLUMN {col}')
    with contextlib.closing(Store(tmp_path)) as s:
        after=s.event_call('detail',e['id']);assert after['execution_mode']=='sequential' and not after['unbounded']
        assert after['decisions']==e['decisions'] and after['official_games']==18
        assert s.rows('SELECT id,official FROM games ORDER BY id')==saved
        s.export_pending();assert (tmp_path/'games.pgn').read_bytes()==pgn


def test_championship_creation_is_atomic_and_final_control_repeats(tmp_path,monkeypatch):
    with contextlib.closing(Store(tmp_path)) as s:
        e=create(s);command(s,e['id'],'run');s.event_call('tick');s.event_call('tick');finish_active(s,e['id'])
        original=s.insert_tournament
        def fail(*args,**kwargs):raise RuntimeError('Injected championship commit interruption')
        monkeypatch.setattr(s,'insert_tournament',fail)
        with pytest.raises(RuntimeError):s.event_call('tick')
        assert not s.event_call('detail',e['id'])['decisions']
        assert not s.one("SELECT 1 FROM event_children WHERE role='championship'")
        monkeypatch.setattr(s,'insert_tournament',original)
        e=drive(s,e['id'],ties=4);assert e['official_games']==36
        stages=e['decisions'][0]['championship']['matches'][0]['stages']
        assert len(stages)==5 and stages[-1]['time_control']==stages[-2]['time_control']


def test_event_budget_validation_and_stale_edits(tmp_path):
    with contextlib.closing(Store(tmp_path)) as s:
        e=create(s);before=e['resources']
        with pytest.raises(ValueError):s.event_call('set_resources',e['id'],e['revision'],before|{'concurrency':0})
        assert s.event_call('detail',e['id'])['resources']==before
        after=s.event_call('set_resources',e['id'],e['revision'],before|{'concurrency':1})
        assert after['resources']['concurrency']==after['definition']['resources']['concurrency']==1
        with pytest.raises(ValueError):s.event_call('set_resources',e['id'],e['revision'],before)


def test_replacement_of_tied_final_reconciles_counts_and_archives_old_playoffs(tmp_path):
    with contextlib.closing(Store(tmp_path)) as s:
        e=drive(s,create(s)['id'],ties=2)
        final=next(c for c in e['children'] if c['stage']==0 and c['role']=='championship')
        g=s.one('SELECT id FROM games WHERE tid=? ORDER BY number',(final['tid'],))
        original=s.rows('SELECT a.id,a.result FROM attempts a JOIN games g ON g.id=a.gid WHERE g.tid=?',(final['tid'],))
        s.requeue(final['tid'],[g['id']],mode='replacement',invalidate=True)
        e=drive(s,e['id'])
        assert e['official_games']==e['scheduled_games']
        assert all(s.one('SELECT result FROM attempts WHERE id=?',(a['id'],))['result']==a['result'] for a in original)
        for c in e['children']:
            if c['valid']:assert s.snapshot(c['tid'])['official_games']==c['total']==2*s.snapshot(c['tid'])['complete_pairs']
