import asyncio
import contextlib
import json
import os
import sqlite3
import subprocess
import sys

import chess
import pytest
from aiohttp.test_utils import TestClient,TestServer
from arena.server import create_app
from arena.store import Store
from arena.opening_policy import prepare
from test_core import profile


@pytest.fixture
def store(tmp_path):
    with contextlib.closing(Store(tmp_path)) as s:yield s


def draft(s,**settings):
    return s.create_tournament('Saved test',[profile('A'),profile('B')],settings,backup=False)


def test_edit_in_place_rebuilds_schedule_rankings_and_report(store):
    t=draft(store);tid=t['id']
    result=store.edit_tournament(tid,'Revised RR',{'format':'round_robin','cycles':7,
        'time_control':{'kind':'nodes','nodes':1000},'paired':False,'seeding':'random'},0,
        [profile(str(i)) for i in range(5)],backup=False)
    assert result['id']==tid and result['created']==t['created']
    assert result['state']=='paused' and result['total']==70 and result['participants']==5
    assert result['setup_revision']==1 and result['can_edit']
    assert not store.rows('SELECT * FROM games') and not store.rows('SELECT * FROM attempts')
    assert len(store.rows('SELECT * FROM rankings'))==len(store.rows('SELECT * FROM aggregates'))==5
    snap=store.snapshot(tid);assert snap['official_games']==0 and snap['total']==70
    from arena.tournament_report import render
    report=render(store.path,tid,technical=False)
    assert 'Revised RR' in report and '1,000' in report
    assert store.one('SELECT revision FROM report_revisions WHERE tid=?',(tid,))['revision']==1


def test_keep_recorded_profiles_and_shuffled_openings(store):
    items=[{'fen':chess.Board.from_chess960_pos(i).fen(),'name':str(i)} for i in range(10)]
    t=store.create_tournament('Original',[profile('A')|{'options':{'Threads':3},'time_control':{'kind':'depth','depth':8}},profile('B')],
        {'chess960':True,'opening_order':'shuffle','opening_policy':'pair','seed':92,'retry_reasons':['crash'],
         'sprt':{'elo0':0,'elo1':3,'alpha':.1,'beta':.02},'resign_plies':12,
         'opening_source':{'name':'missing-book.pgn','depth':16}},items,backup=False)
    original=[store.participant(t['id'],i) for i in range(2)]
    updated=store.edit_tournament(t['id'],'Renamed',{},0,backup=False)
    assert updated['settings']==t['settings']
    assert [store.participant(t['id'],i) for i in range(2)]==original
    updated=store.edit_tournament(t['id'],'New seed',{'seed':93},1,backup=False)
    assert updated['settings']['openings']==prepare(updated['settings'],items)
    updated=store.edit_tournament(t['id'],'Sequential',{'opening_order':'sequential'},2,backup=False)
    assert updated['settings']['openings']==items


def test_replacing_opening_clears_metadata_and_persists_backup(store):
    t=draft(store,opening_source={'name':'old.pgn'},opening_inventory={'unique_positions':2})
    result=store.edit_tournament(t['id'],'Initial position',{},0,keep_openings=False)
    assert 'opening_source' not in result['settings'] and 'opening_inventory' not in result['settings']
    with sqlite3.connect(store.backup_file) as db:
        name,revision=db.execute('SELECT name,setup_revision FROM tournaments WHERE id=?',(t['id'],)).fetchone()
        assert (name,revision)==('Initial position',1)


@pytest.mark.parametrize('change',[{'cycles':0},{'time_control':{'kind':'nodes','nodes':0}}, {'opening_order':'invalid'}])
def test_invalid_edit_is_atomic(store,change):
    t=draft(store)
    with pytest.raises(ValueError):store.edit_tournament(t['id'],'Bad',change,0,backup=False)
    assert store.tournament(t['id'])==t
    assert not store.rows("SELECT * FROM audit WHERE action='setup_edited'")


def test_transaction_failure_rolls_back_participants_and_rankings(store,monkeypatch):
    import arena.rankings
    t=draft(store)
    def fail(*args):raise ValueError('Injected save failure')
    monkeypatch.setattr(arena.rankings,'create',fail)
    with pytest.raises(ValueError,match='Injected'):store.edit_tournament(t['id'],'Bad',{},0,[profile('New'),profile('Other')],backup=False)
    assert store.tournament(t['id'])==t
    assert store.participant(t['id'],0)['name']=='A'
    assert len(store.rows('SELECT * FROM rankings'))==2


def test_stale_editor_and_concurrency_change_are_rejected(store):
    t=draft(store);tid=t['id']
    store.edit_tournament(tid,'First editor',{},0,backup=False)
    with pytest.raises(ValueError,match='changed'):store.edit_tournament(tid,'Second editor',{},0,backup=False)
    store.set_concurrency(tid,2)
    with pytest.raises(ValueError,match='changed'):store.edit_tournament(tid,'Old limit',{},1,backup=False)
    assert store.tournament(tid)['settings']['concurrency']==2
    with pytest.raises(ValueError):store.edit_tournament(tid,'Missing version',{},None,backup=False)


@pytest.mark.parametrize('history',['start_pause','pending','attempt','invalidated','completed','pairing'])
def test_run_or_game_history_locks_setup(store,history):
    t=draft(store);tid=t['id']
    if history=='start_pause':store.set_state(tid,'running');store.set_state(tid,'paused')
    elif history=='pairing':store.execute('INSERT INTO round_state VALUES(?,0,?)',(tid,'{}'))
    elif history=='completed':store.execute("UPDATE tournaments SET state='completed' WHERE id=?",(tid,))
    else:
        with store.tx():store._insert_pair(tid,0,0,1,0,t['settings'])
        if history in ('attempt','invalidated'):
            store.set_state(tid,'running');store.claim(tid);store.set_state(tid,'paused')
        if history=='invalidated':store.execute('UPDATE games SET invalid=1 WHERE tid=?',(tid,))
    assert not store.tournament(tid)['can_edit']
    with pytest.raises(ValueError,match='never started'):store.tournament_setup(tid)
    with pytest.raises(ValueError,match='never started'):store.edit_tournament(tid,'No',{},0,backup=False)


def test_migrate_existing_paused_and_previously_started(tmp_path):
    with contextlib.closing(Store(tmp_path)) as s:
        fresh=draft(s);started=draft(s)
        s.set_state(started['id'],'running');s.set_state(started['id'],'paused')
    with sqlite3.connect(tmp_path/'arena.sqlite3') as db:
        db.execute('ALTER TABLE tournaments DROP COLUMN started_once')
        db.execute('ALTER TABLE tournaments DROP COLUMN setup_revision')
    with contextlib.closing(Store(tmp_path)) as s:
        assert s.tournament(fresh['id'])['can_edit']
        assert not s.tournament(started['id'])['can_edit']


def test_committed_edit_survives_abrupt_process_exit(tmp_path):
    script="""import os,sys
from arena.store import Store
s=Store(sys.argv[1]);t=s.create_tournament('Before',[{'name':'A'},{'name':'B'}],{},backup=False)
s.edit_tournament(t['id'],'After',{'cycles':12},0,backup=False)
print(t['id'],flush=True);os._exit(0)
"""
    tid=subprocess.check_output([sys.executable,'-c',script,str(tmp_path)],text=True).strip()
    with contextlib.closing(Store(tmp_path)) as s:
        t=s.tournament(tid);assert t['name']=='After' and t['total']==24 and t['can_edit']


def test_large_field_edit_is_incremental(store):
    t=draft(store)
    result=store.edit_tournament(t['id'],'10k engines',{'format':'round_robin','cycles':1},0,
        [profile(str(i)) for i in range(10000)],backup=False)
    assert result['total']==99990000 and result['participants']==10000
    assert store.one('SELECT count(*) n FROM games')['n']==0


def test_setup_api_preview_replace_and_start_guard(tmp_path):
    async def run():
        app=await create_app(tmp_path,'edit');db=app['db'];runner=app['runner']
        runner.scheduler.cancel()
        with contextlib.suppress(asyncio.CancelledError):await runner.scheduler
        async with TestClient(TestServer(app),headers={'X-Arena-Token':'edit'}) as client:
            t=await db.call('create_tournament','Ready',[profile('A'),profile('B')],{'concurrency':1})
            tid=t['id'];url=f'/api/tournaments/{tid}/setup'
            response=await client.get(url);data=await response.json()
            assert response.status==200 and 'openings' not in data['settings'] and data['opening_count']==1
            body={'name':'Edited','settings':{'cycles':5},'setup_revision':0}
            response=await client.post(url,json=body);result=await response.json()
            assert response.status==200,result
            assert result['id']==tid and result['total']==10 and result['state']=='paused'
            assert (await client.post(url,json=body)).status==400
            preview=await client.post('/api/opening-preview',json={'recorded_tournament':tid,'participants':2,'settings':{}})
            assert preview.status==200 and (await preview.json())['unique_positions']==1
            resources=await client.post('/api/resource-preview',json={'recorded_participants':tid,'settings':{}})
            assert resources.status==200 and (await resources.json())['worst_pair_threads']>=1
            response=await asyncio.wait_for(client.post(url,json={**body,'setup_revision':1,'name':'Background backup'}),5)
            assert response.status==200 and runner.backup_requested
            assert not runner.lifecycle_lock.locked()
            assert (await db.call('tournament',tid))['name']=='Background backup'
            await db.call('set_state',tid,'running');await db.call('set_state',tid,'paused')
            assert (await client.get(url)).status==400
            body['setup_revision']=1
            assert (await client.post(url,json=body)).status==400
    asyncio.run(run())


def test_edited_tournament_runs_updated_schedule_and_pgn(tmp_path):
    from arena.runner import Database,Runner
    from test_core import read_pgn
    import time
    async def run():
        db=await Database().open(tmp_path);runner=Runner(db)
        try:
            t=await db.call('create_tournament','Draft',[profile('Old A'),profile('Old B')],{'concurrency':1})
            t=await db.call('edit_tournament',t['id'],'Edited test',{'cycles':3,'concurrency':2,'max_plies':4,
                'time_control':{'kind':'nodes','nodes':77}},0,[profile('New A'),profile('New B')])
            await db.call('set_state',t['id'],'running');await runner.start()
            deadline=time.monotonic()+20
            while time.monotonic()<deadline:
                snap=await db.call('snapshot',t['id'])
                assert not runner.error,runner.error
                if snap['state']=='completed':break
                await asyncio.sleep(.02)
            assert snap['state']=='completed' and snap['official_games']==6 and snap['complete_pairs']==3
            assert not snap['can_edit']
            attempts=await db.call('rows','SELECT * FROM attempts')
            assert len(attempts)==6 and all(a['reason']=='max_plies_adjudication' for a in attempts)
            await db.call('export_pending')
            games=read_pgn((tmp_path/'games.pgn').read_text(encoding='utf-8'))
            assert len(games)==6
            assert all({g.headers['White'],g.headers['Black']}=={'New A','New B'} for g in games)
        finally:await runner.close()
    asyncio.run(run())
