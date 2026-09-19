import asyncio
from contextlib import closing
import sqlite3
import subprocess
import sys
from unittest.mock import patch
import chess
import chess.pgn
import pytest
from aiohttp.test_utils import TestClient,TestServer
from arena.store import Store,SavingError
from arena.server import create_app


def tournament(s,name):
    return s.create_tournament(name,[{'name':'A','path':'a.exe'},{'name':'B','path':'b.exe'}],{'cycles':2},backup=False)['id']


def finish(s,tid,result='1-0',reason='checkmate'):
    s.set_state(tid,'running');s.fill_queue(tid,4);g=s.claim(tid)
    board=chess.Board();board.push_uci('e2e4')
    s.move(g['aid'],1,'e2e4','e4',board.fen(),.1,{'white':{'remaining':10},'black':{'remaining':11}},{'nodes':100})
    s.log(g['aid'],['fixture log']);s.finish(g['aid'],result,reason);s.set_state(tid,'paused')
    return g


def pgn_ids(path):
    result=[]
    with path.open(encoding='utf-8') as f:
        while g:=chess.pgn.read_game(f):
            assert not g.errors
            result.append((g.headers['TournamentId'],g.headers['AttemptId']))
    return result


def assert_absent(db,tid):
    for table in ('tournaments','participants','games','aggregates','audit','round_state','game_counts',
                  'rankings','ranking_meta','sequential_state','sequential_samples','rating_anchors','report_revisions'):
        key='id' if table=='tournaments' else 'tid'
        assert db.execute(f'SELECT count(*) FROM {table} WHERE {key}=?',(tid,)).fetchone()[0]==0,table
    for table,key,parent in [('attempts','gid','games'),('moves','aid','attempts'),('logs','aid','attempts'),('outbox','aid','attempts')]:
        assert db.execute(f'SELECT count(*) FROM {table} WHERE {key} NOT IN (SELECT id FROM {parent})').fetchone()[0]==0,table


def test_delete_preserves_other_tournaments_and_removes_all_attempts_and_backups(tmp_path):
    s=Store(tmp_path)
    try:
        s.save_profile({'name':'Library stays','path':'engine.exe'})
        deleted=tournament(s,'Delete me');keep=tournament(s,'Keep me')
        g=finish(s,deleted,'0-1','timeout');finish(s,keep)
        s.requeue(deleted,[g['id']],mode='replacement');finish(s,deleted)
        s.requeue(deleted,[g['id']],mode='diagnostic');finish(s,deleted,'*','interrupted')
        s.export_pending();s.backup();s.backup()
        before=s.snapshot(keep);stamps={p.name:p.stat().st_mtime_ns for p in (tmp_path/'backups').glob('recovery-*.sqlite3')}
        preview=s.deletion_preview(deleted);assert preview['attempts']==3 and preview['official']==1
        s.delete_tournament(deleted,'Delete me');assert_absent(s.db,deleted)
        assert s.snapshot(keep)['standings']==before['standings']
        assert s.profiles()['total']==1 and s.one('SELECT count(*) n FROM presets')['n']>0
        assert [tid for tid,_ in pgn_ids(tmp_path/'games.pgn')]==[keep]
        assert not pgn_ids(tmp_path/'interrupted.pgn')
        for p in (tmp_path/'backups').glob('recovery-*.sqlite3'):
            assert p.stat().st_mtime_ns==stamps[p.name]
            with closing(sqlite3.connect(p)) as db:
                assert_absent(db,deleted);assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        finish(s,keep);s.export_pending();s.export_pending()
        ids=pgn_ids(tmp_path/'games.pgn');assert len(ids)==len(set(ids))==2
    finally:s.close()
    s=Store(tmp_path)
    try:assert_absent(s.db,deleted);assert s.snapshot(keep)['official_games']==2
    finally:s.close()


@pytest.mark.parametrize('failure_point',['replace','fsync'])
def test_failed_pgn_cleanup_finishes_after_restart(tmp_path,failure_point):
    s=Store(tmp_path);tid=tournament(s,'Delete me');finish(s,tid);s.export_pending()
    try:
        with patch('os.'+failure_point,side_effect=OSError('Injected storage failure')):
            with pytest.raises(SavingError):s.delete_tournament(tid,'Delete me')
        assert s.failure
    finally:s.close()
    s=Store(tmp_path)
    try:
        assert not s.failure;assert_absent(s.db,tid)
        assert not pgn_ids(tmp_path/'games.pgn')
    finally:s.close()


def test_forced_exit_after_deletion_intent_and_old_backup_restore(tmp_path):
    s=Store(tmp_path);tid=tournament(s,'Delete me');keep=tournament(s,'Keep me');finish(s,tid);finish(s,keep)
    s.export_pending();s.backup();s.close()
    # Simulate the exact crash boundary between durable intent and main purge.
    script="""import os,sys
from pathlib import Path
from arena.deletion import ledger
db=ledger(Path(sys.argv[1]))
with db:db.execute('INSERT INTO deleted VALUES(?)',(sys.argv[2],))
os._exit(73)
"""
    result=subprocess.run([sys.executable,'-c',script,str(tmp_path),tid],creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0),timeout=20)
    assert result.returncode==73
    # Force startup to use the pre-deletion recovery snapshot.
    (tmp_path/'arena.sqlite3').write_bytes(b'forced corruption')
    s=Store(tmp_path)
    try:
        assert 'Restored verified backup' in s.warning;assert not s.failure;assert_absent(s.db,tid)
        assert s.snapshot(keep)['official_games']==1
        assert [t for t,_ in pgn_ids(tmp_path/'games.pgn')]==[keep]
    finally:s.close()


def test_active_tournament_guard_and_confirmation_api(tmp_path):
    async def run():
        app=await create_app(tmp_path,'delete-test');runner=app['runner'];db=app['db']
        runner.scheduler.cancel();await asyncio.gather(runner.scheduler,return_exceptions=True)
        tid=await db.call('create_tournament','Delete me',[{'name':'A','path':'a.exe'},{'name':'B','path':'b.exe'}],{'cycles':1})
        tid=tid['id']
        async with TestClient(TestServer(app),headers={'X-Arena-Token':'delete-test'}) as client:
            url=f'/api/tournaments/{tid}/delete'
            r=await client.get(url);assert r.status==200 and (await r.json())['scheduled']==2
            r=await client.post(url,json={'name':'Delete me'});assert r.status==400
            r=await client.post(url,json={'confirmed':True,'name':'Wrong name'});assert r.status==400
            await db.call('set_state',tid,'running')
            r=await client.post(url,json={'confirmed':True,'name':'Delete me'});assert r.status==400
            assert 'drain' in (await r.json())['error']
            await db.call('set_state',tid,'paused')
            r=await client.post(url,json={'confirmed':True,'name':'Delete me'});assert r.status==200
            assert await (await client.get('/api/tournaments')).json()==[]
    asyncio.run(run())


def test_failed_backup_replacement_and_abandoned_scratch_sidecars(tmp_path):
    s=Store(tmp_path);tid=tournament(s,'Delete me');keep=tournament(s,'Keep me')
    finish(s,tid);finish(s,keep);s.export_pending();s.backup()
    backup=next((tmp_path/'backups').glob('recovery-*.sqlite3'));temporary=backup.with_suffix('.delete.tmp')
    for suffix in ('','-wal','-shm','-journal'):
        temporary.with_name(temporary.name+suffix).write_bytes(b'Abandoned incomplete scratch image')
    try:
        with patch('os.replace',side_effect=OSError('Injected snapshot replacement failure')):
            with pytest.raises(SavingError):s.delete_tournament(tid,'Delete me')
        # Original backup is still valid until replacement completes.
        with closing(sqlite3.connect(backup)) as db:
            assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
            assert db.execute('SELECT count(*) FROM tournaments').fetchone()[0]==2
        s.retry_saving();assert not s.failure;assert_absent(s.db,tid)
        with closing(sqlite3.connect(backup)) as db:assert_absent(db,tid)
        assert [t for t,_ in pgn_ids(tmp_path/'games.pgn')]==[keep]
    finally:s.close()
