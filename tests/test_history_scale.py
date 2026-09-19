import asyncio
import contextlib
import io
import sqlite3
import threading
from unittest.mock import patch
import chess
import chess.pgn
import pytest
from aiohttp.test_utils import TestClient,TestServer
from arena.pgn_export import OfficialPgnReader
from arena.runner import Database,Runner
from arena.server import create_app
from arena.store import Store,SavingError


def tournament(s):
    t=s.create_tournament('History',[{'name':'A'},{'name':'B'}],{'cycles':1})
    s.set_state(t['id'],'running');s.fill_queue(t['id'],2)
    return t['id']


def check_counts(s,tid):
    expected=s.rows('SELECT state,count(*) n FROM games WHERE tid=? AND invalid=0 GROUP BY state',(tid,))
    snap=s.snapshot(tid)
    assert snap['counts']=={r['state']:r['n'] for r in expected}
    assert snap['official_games']==s.one('SELECT count(*) n FROM games WHERE tid=? AND invalid=0 AND official IS NOT NULL',(tid,))['n']
    assert s.games(tid)['total']==s.one('SELECT count(*) n FROM games WHERE tid=?',(tid,))['n']


def test_counter_migration_and_transaction_rollback(tmp_path):
    s=Store(tmp_path);tid=tournament(s);g=s.claim(tid);s.finish(g['aid'],'0-1','timeout');check_counts(s,tid)
    s.set_state(tid,'paused');s.requeue(tid,[g['id']],mode='replacement');check_counts(s,tid)
    s.set_state(tid,'running');retry=s.claim(tid);s.finish(retry['aid'],'1-0','checkmate');check_counts(s,tid)
    with pytest.raises(ValueError):
        with s.tx():
            s.db.execute("UPDATE games SET state='invalidated',invalid=1 WHERE tid=?",(tid,))
            raise ValueError('Injected rollback')
    check_counts(s,tid)
    # Simulate an existing release database without the new migration.
    for name in ('insert','delete','update'):s.db.execute('DROP TRIGGER game_counts_'+name)
    s.db.execute('DROP TABLE game_counts');s.close()
    s=Store(tmp_path)
    try:
        check_counts(s,tid)
        with s.tx():s.db.execute('DELETE FROM games WHERE official IS NULL AND tid=?',(tid,))
        check_counts(s,tid)
    finally:s.close()


def test_backup_does_not_hold_move_writer_or_scheduler(tmp_path):
    async def run():
        db=await Database().open(tmp_path);entered=threading.Event();release=threading.Event();runner=Runner(db)
        try:
            t=await db.call('create_tournament','Backup',[{'name':'A'},{'name':'B'}],{'cycles':1});tid=t['id']
            await db.call('set_state',tid,'running');await db.call('fill_queue',tid,2);g=await db.call('claim',tid)
            # Pause admission so the scheduler can be tested without engines.
            await db.call('set_state',tid,'paused')
            actual_backup=db.store._backup_snapshot
            def slow_backup():entered.set();assert release.wait(5);actual_backup()
            with patch.object(db.store,'_backup_snapshot',slow_backup):
                runner.last_backup-=61;await runner.start()
                assert await asyncio.to_thread(entered.wait,2)
                board=chess.Board();board.push_uci('e2e4')
                await asyncio.wait_for(db.save_move(g['aid'],1,'e2e4','e4',board.fen(),.1,
                    {'white':{'remaining':None},'black':{'remaining':None}},{'nodes':100},[]),1)
                # A blocked backup must not prevent the scheduler's next PGN flush.
                await db.call('finish',g['aid'],'1-0','checkmate')
                for _ in range(30):
                    if (tmp_path/'games.pgn').stat().st_size:break
                    await asyncio.sleep(.01)
                assert (tmp_path/'games.pgn').stat().st_size>0
                release.set();await runner.backup_task
            backup=max((tmp_path/'backups').glob('recovery-*.sqlite3'),key=lambda p:p.stat().st_mtime_ns)
            with sqlite3.connect(backup) as verify:
                assert verify.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
                assert verify.execute('SELECT count(*) FROM moves').fetchone()[0]==1
        finally:
            release.set();await runner.close()
    asyncio.run(run())


def test_background_backup_failure_is_reported_and_retryable(tmp_path):
    async def run():
        db=await Database().open(tmp_path)
        try:
            with patch('arena.store.os.replace',side_effect=OSError('Injected backup replacement failure')):
                with pytest.raises(SavingError):await db.call('backup')
            assert 'Backup saving failed' in db.store.failure
            await db.call('retry_saving');assert not db.store.failure
        finally:await db.close()
    asyncio.run(run())


def test_partial_backup_image_is_replaced_without_losing_verified_backups(tmp_path):
    s=Store(tmp_path);tid=tournament(s)
    before={p.name:p.read_bytes() for p in (tmp_path/'backups').glob('recovery-*.sqlite3')}
    (tmp_path/'backups/backup.tmp').write_bytes(b'Interrupted SQLite backup image')
    s.backup()
    for name,data in before.items():assert (tmp_path/'backups'/name).read_bytes()==data
    assert not (tmp_path/'backups/backup.tmp').exists()
    latest=max((tmp_path/'backups').glob('recovery-*.sqlite3'),key=lambda p:p.stat().st_mtime_ns)
    with sqlite3.connect(latest) as db:
        assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        assert db.execute('SELECT id FROM tournaments').fetchone()[0]==tid
    s.close()


def test_pgn_snapshot_preserves_old_results_during_replacement(tmp_path):
    s=Store(tmp_path);tid=tournament(s);games=[]
    for _ in range(2):
        g=s.claim(tid);s.finish(g['aid'],'0-1','timeout');games.append(g)
    reader=OfficialPgnReader(s.path,tid)
    s.set_state(tid,'paused');s.requeue(tid,[games[0]['id']],mode='replacement');s.set_state(tid,'running')
    replacement=s.claim(tid);s.finish(replacement['aid'],'1/2-1/2','replacement')
    before=reader.chunk().decode();assert reader.chunk()==b'';reader.close()
    assert replacement['aid'] not in before and games[0]['aid'] in before
    after=s.export_official(tid);assert replacement['aid'] in after and games[0]['aid'] not in after
    f=io.StringIO(after);ids=[]
    while game:=chess.pgn.read_game(f):
        assert not game.errors;ids.append(game.headers['AttemptId'])
    assert ids==[replacement['aid'],games[1]['aid']];s.close()


def test_http_pgn_download_renders_snapshot_off_writer(tmp_path):
    async def run():
        app=await create_app(tmp_path,'export');db=app['db'];app['runner'].scheduler.cancel()
        with contextlib.suppress(asyncio.CancelledError):await app['runner'].scheduler
        async with TestClient(TestServer(app),headers={'X-Arena-Token':'export'}) as client:
            tid=await db.call('create_tournament','HTTP PGN',[{'name':'A'},{'name':'B'}],{'cycles':1});tid=tid['id']
            await db.call('set_state',tid,'running');await db.call('fill_queue',tid,2)
            g=await db.call('claim',tid);await db.call('finish',g['aid'],'1-0','checkmate')
            response=await client.get(f'/api/tournaments/{tid}/game-number/1')
            assert response.status==200 and (await response.json())['id']==g['id']
            for number in ('0','-1','3','invalid'):
                response=await client.get(f'/api/tournaments/{tid}/game-number/{number}')
                assert response.status==400
            with patch.object(db.store,'pgn',side_effect=AssertionError('Export must not render on the writer connection')):
                response=await client.get(f'/api/export/{tid}/pgn')
                assert response.status==200 and response.headers['Transfer-Encoding']=='chunked'
                game=chess.pgn.read_game(io.StringIO(await response.text()))
                assert game.headers['AttemptId']==g['aid'] and not game.errors
            response=await client.get('/api/export/missing/pgn');assert response.status==400
    asyncio.run(run())


def test_slow_history_filter_does_not_block_game_commits(tmp_path):
    async def run():
        app=await create_app(tmp_path,'history');db=app['db'];app['runner'].scheduler.cancel()
        with contextlib.suppress(asyncio.CancelledError):await app['runner'].scheduler
        entered=threading.Event();release=threading.Event()
        from arena.history import read_game_page
        def slow_page(*args):
            entered.set();assert release.wait(5)
            return read_game_page(*args)
        async with TestClient(TestServer(app),headers={'X-Arena-Token':'history'}) as client:
            t=await db.call('create_tournament','History isolation',[{'name':'A'},{'name':'B'}],{'cycles':1});tid=t['id']
            await db.call('set_state',tid,'running');await db.call('fill_queue',tid,2);g=await db.call('claim',tid)
            with patch('arena.history.read_game_page',side_effect=slow_page):
                pending=asyncio.create_task(client.get(f'/api/tournaments/{tid}/games?reason=failed'))
                try:
                    assert await asyncio.to_thread(entered.wait,2)
                    await asyncio.wait_for(db.call('finish',g['aid'],'0-1','timeout'),1)
                finally:release.set()
                response=await pending;page=await response.json()
                assert response.status==200 and page['total']==1 and page['items'][0]['id']==g['id']
    asyncio.run(run())
