import asyncio
from contextlib import closing
import hashlib
import os
import sqlite3
import subprocess
import sys
import threading
from unittest.mock import patch

import pytest
from aiohttp.test_utils import TestClient,TestServer
from arena.store import Store,SavingError
from arena.log_storage import read,migrate
from arena.storage import inventory,settings
from arena.server import create_app


def test_sqlite_full_rolls_back_preserves_results_and_recovers(tmp_path):
    # SQLite's page limit produces SQLITE_FULL without exhausting the real disk.
    s=Store(tmp_path)
    try:
        tid,g=game(s)
        before=s.snapshot(tid)['standings'];pgn=(tmp_path/'games.pgn').read_bytes()
        s.execute('CREATE TABLE limited_space(data BLOB)')
        pages=s.db.execute('PRAGMA page_count').fetchone()[0]
        s.db.execute(f'PRAGMA max_page_count={pages}')
        with pytest.raises(SavingError,match='full'):
            s.execute('INSERT INTO limited_space VALUES(zeroblob(2097152))')
        assert s.failure and s.one('SELECT count(*) n FROM limited_space')['n']==0
        assert s.snapshot(tid)['standings']==before
        assert (tmp_path/'games.pgn').read_bytes()==pgn
        s.db.execute('PRAGMA max_page_count=1073741823');s.retry_saving()
        assert not s.failure and s.db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
    finally:s.close()


def game(s,name='Preserved'):
    tid=s.create_tournament(name,[{'name':'A'},{'name':'B'}],{'cycles':2},backup=False)['id']
    s.set_state(tid,'running');s.fill_queue(tid,4);g=s.claim(tid)
    s.finish(g['aid'],'1/2-1/2','fixture');s.set_state(tid,'paused');s.export_pending()
    return tid,g


def legacy(s,aid,n=5000):
    with s.tx():s.db.executemany('INSERT INTO logs(aid,line,created) VALUES(?,?,?)',
        ((aid,f'info depth {i%80} nodes {i*1000} pv '+('e2e4 e7e5 g1f3 b8c6 '*60)+f' ♞ {i}',i*.001) for i in range(n)))


def test_lossless_order_timestamps_and_restartable_migration(tmp_path):
    s=Store(tmp_path)
    try:
        tid,g=game(s);legacy(s,g['aid']);before=read(s.db,g['aid'],10000,False)
        s.log(g['aid'],['stderr failure preserved','bestmove e2e4'])
        before+=read(s.db,g['aid'],2)[::-1]
        # The transaction must retain the old rows if deletion fails after packing.
        s.db.execute("CREATE TRIGGER reject_log_delete BEFORE DELETE ON logs BEGIN SELECT RAISE(ABORT,'injected'); END")
        with pytest.raises(SavingError):migrate(s.db,transaction=s.tx)
        assert len(read(s.db,g['aid'],10000,False))==len(before)
        s.db.execute('DROP TRIGGER reject_log_delete');s.failure=''
        migrate(s.db,transaction=s.tx)
        assert read(s.db,g['aid'],10000,False)==before
        assert read(s.db,g['aid'],300)==before[-300:][::-1]
        assert not s.db.execute('SELECT 1 FROM logs').fetchone()
        assert s.db.execute('SELECT sum(length(body))*1.0/sum(raw_bytes) FROM log_blocks').fetchone()[0]<.1
    finally:s.close()


def test_optimize_and_delete_reclaim_real_files_preserving_results_and_pgn(tmp_path):
    s=Store(tmp_path)
    try:
        tid,g=game(s);keep,k=game(s,'Other tournament');legacy(s,g['aid']);legacy(s,k['aid'],1000)
        # Initial logs were inserted through the old format. New logs use blocks.
        s.log(g['aid'],['final diagnostic']);before_logs=read(s.db,g['aid'],10000,False)
        before_results=s.snapshot(tid);pgn=(tmp_path/'games.pgn').read_bytes()
        s.save_storage_settings({'backup_copies':5,'backup_minutes':10})
        for _ in range(5):s.backup()
        s.db.execute('PRAGMA wal_checkpoint(TRUNCATE)');before=inventory(s)['total_bytes']
        s.save_storage_settings({'backup_copies':2,'backup_minutes':10})
        result=s.optimize_storage()
        assert result['total_bytes']<before*.25 and result['backup_count']==2
        assert result['reclaimable_bytes']==0
        assert read(s.db,g['aid'],10000,False)==before_logs
        assert s.snapshot(tid)['standings']==before_results['standings']
        assert (tmp_path/'games.pgn').read_bytes()==pgn
        for path in (tmp_path/'backups').glob('recovery-*.sqlite3'):
            with closing(sqlite3.connect(path)) as db:
                assert read(db,g['aid'],10000,False)==before_logs
                assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
                assert db.execute('PRAGMA freelist_count').fetchone()[0]==0
        # Deletion must also shrink files even if they were written by an older build.
        legacy(s,g['aid'],7000)
        s.backup();s.db.execute('PRAGMA wal_checkpoint(TRUNCATE)');before=inventory(s)['total_bytes']
        s.delete_tournament(tid,'Preserved')
        assert inventory(s)['total_bytes']<before*.3
        assert s.snapshot(keep)['official_games']==1
        assert not s.db.execute('SELECT 1 FROM log_blocks WHERE aid=?',(g['aid'],)).fetchone()
        for path in (tmp_path/'backups').glob('recovery-*.sqlite3'):
            with closing(sqlite3.connect(path)) as db:
                assert not db.execute('SELECT 1 FROM tournaments WHERE id=?',(tid,)).fetchone()
                assert db.execute('PRAGMA freelist_count').fetchone()[0]==0
    finally:s.close()


def test_killed_cleanup_resumes_with_all_diagnostics_and_results(tmp_path):
    s=Store(tmp_path);tid,g=game(s);legacy(s,g['aid'],1000)
    expected=read(s.db,g['aid'],2000,False);s.backup();s.close()
    code='''import os,sys
from arena.store import Store
import arena.storage as maintenance
s=Store(sys.argv[1])
maintenance.compact=lambda db:os._exit(79)
s.optimize_storage()
'''
    p=subprocess.run([sys.executable,'-c',code,str(tmp_path)],timeout=30,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    assert p.returncode==79
    s=Store(tmp_path)
    try:
        assert not s.failure and s.snapshot(tid)['official_games']==1
        assert read(s.db,g['aid'],2000,False)==expected
        assert not s.db.execute('SELECT 1 FROM storage_jobs').fetchone()
        assert s.db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
    finally:s.close()


def test_failed_cleanup_leaves_verified_copy_and_can_retry(tmp_path):
    s=Store(tmp_path)
    try:
        tid,g=game(s);legacy(s,g['aid'],1000);s.backup()
        backup=s.backup_file;original=hashlib.sha256(backup.read_bytes()).digest()
        with patch('os.replace',side_effect=OSError('Injected disk failure')):
            with pytest.raises(SavingError):s.optimize_storage()
        assert s.maintenance_state['phase']=='Failed' and s.failure
        assert hashlib.sha256(backup.read_bytes()).digest()==original
        s.retry_saving();assert not s.failure
        assert not s.db.execute('SELECT 1 FROM storage_jobs').fetchone()
        assert s.snapshot(tid)['official_games']==1
    finally:s.close()


def test_settings_validation_and_resume_message(tmp_path):
    for value in [1,11,2.5,True,'3']:
        with pytest.raises(ValueError):settings({'backup_copies':value})
    s=Store(tmp_path)
    try:
        tid,g=game(s)
        s.execute("UPDATE tournaments SET note='Recovered after restart. Completed results retained; unfinished attempts archived. Resume when ready.' WHERE id=?",(tid,))
        s.set_state(tid,'running')
        assert 'Resume when ready' not in s.tournament(tid)['note']
        with pytest.raises(ValueError):s.optimize_storage()
        assert s.h2h_page(tid,0)['selected']['name']=='A'
    finally:s.close()


def test_reclaim_also_finishes_a_failed_deletion(tmp_path):
    s=Store(tmp_path)
    try:
        tid,g=game(s);keep,k=game(s,'Kept');legacy(s,g['aid'],500);s.backup()
        with patch('os.replace',side_effect=OSError('Interrupted deletion')):
            with pytest.raises(SavingError):s.delete_tournament(tid,'Preserved')
        assert not s.maintenance_state['busy']
        s.optimize_storage()
        assert not s.failure
        assert tid not in (tmp_path/'games.pgn').read_text()
        assert s.snapshot(keep)['official_games']==1
        for path in (tmp_path/'backups').glob('recovery-*.sqlite3'):
            with closing(sqlite3.connect(path)) as db:
                assert not db.execute('SELECT 1 FROM tournaments WHERE id=?',(tid,)).fetchone()
    finally:s.close()


def test_maintenance_progress_is_readable_and_blocks_start(tmp_path):
    async def run():
        app=await create_app(tmp_path,'test');runner=app['runner'];db=app['db']
        runner.scheduler.cancel();await asyncio.gather(runner.scheduler,return_exceptions=True)
        tid=(await db.call('create_tournament','Preserved',[{'name':'A'},{'name':'B'}],{'cycles':1}))['id']
        entered=threading.Event();release=threading.Event()
        original=db.store.optimize_storage
        def held():entered.set();assert release.wait(10);return original()
        async with TestClient(TestServer(app),headers={'X-Arena-Token':'test'}) as client:
            with patch.object(db.store,'optimize_storage',held):
                try:
                    assert (await client.post('/api/storage',json={'action':'optimize'})).status==200
                    await asyncio.to_thread(entered.wait,3);assert entered.is_set()
                    response=await asyncio.wait_for(client.get('/api/storage'),1)
                    assert (await response.json())['maintenance']['busy']
                    response=await asyncio.wait_for(client.post(f'/api/tournaments/{tid}/action',json={'action':'start'}),1)
                    assert response.status==400
                finally:release.set()
                await runner.storage_task
                assert (await (await client.get('/api/storage')).json())['maintenance']['phase']=='Complete'
    asyncio.run(run())


def test_startup_serves_progress_while_resuming_interrupted_cleanup(tmp_path):
    s=Store(tmp_path);tid,g=game(s);legacy(s,g['aid'],500)
    s.execute("INSERT INTO storage_jobs VALUES('optimize')");s.close()
    entered=threading.Event();release=threading.Event()
    original=Store.finish_startup
    def held(store):
        entered.set();assert release.wait(15)
        return original(store)
    async def run():
        with patch.object(Store,'finish_startup',held):
            app=await asyncio.wait_for(create_app(tmp_path,'test'),3)
            runner=app['runner']
            async with TestClient(TestServer(app),headers={'X-Arena-Token':'test'}) as client:
                try:
                    assert await asyncio.to_thread(entered.wait,3)
                    assert (await asyncio.wait_for(client.get('/'),1)).status==200
                    response=await asyncio.wait_for(client.get('/api/storage'),1)
                    assert (await response.json())['maintenance']['busy']
                    response=await asyncio.wait_for(client.get('/api/status'),1)
                    assert (await response.json())['maintenance']
                    response=await client.post(f'/api/tournaments/{tid}/action',json={'action':'start'})
                    assert response.status==400 and not runner.tasks
                finally:release.set()
                await runner.storage_task
                assert not app['db'].store.startup_pending
                assert not app['db'].store.failure
                assert (await app['db'].call('snapshot',tid))['official_games']==1
    asyncio.run(run())
