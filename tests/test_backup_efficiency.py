import sqlite3
import threading
from unittest.mock import patch

from arena.store import Store


def test_unchanged_backup_is_reused_but_changed_or_missing_backup_is_not(tmp_path):
    store=Store(tmp_path)
    try:
        assert store.backup(force=False)
        original=store.backup_file
        stamp=original.stat().st_mtime_ns
        with store.tx():store.db.execute('SELECT 1')
        assert store.backup(force=False) is False
        assert original.stat().st_mtime_ns==stamp
        store.execute("INSERT INTO preferences VALUES('test','{}')")
        assert store.backup(force=False)
        assert len(list((tmp_path/'backups').glob('recovery-*.sqlite3')))==2
        store.backup_file.unlink()
        assert store.backup(force=False)
        with sqlite3.connect(store.backup_file) as check:
            assert check.execute("SELECT body FROM preferences WHERE name='test'").fetchone()[0]=='{}'
        assert store.backup_state['phase']=='ready'
    finally:store.close()


def test_commit_during_snapshot_requires_another_backup(tmp_path):
    store=Store(tmp_path);entered=threading.Event();release=threading.Event();errors=[]
    try:
        original=store._backup_progress
        def pause(**values):
            original(**values)
            if values.get('phase')=='verifying':
                entered.set()
                assert release.wait(5)
        def backup():
            try:store.backup(force=False)
            except Exception as error:errors.append(error)
        with patch.object(store,'_backup_progress',pause):
            thread=threading.Thread(target=backup);thread.start()
            assert entered.wait(5)
            store.execute("INSERT INTO preferences VALUES('newer','{}')")
            release.set();thread.join(5)
            assert not thread.is_alive() and not errors
        assert store.backup_revision<store.revision
        assert store.backup(force=False)
        assert not store.backup(force=False)
        with sqlite3.connect(store.backup_file) as check:
            assert check.execute("SELECT body FROM preferences WHERE name='newer'").fetchone()[0]=='{}'
    finally:release.set();store.close()
