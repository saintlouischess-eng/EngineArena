"""Deletion durability and reusable pages without mandatory whole-DB compaction."""
from contextlib import closing
import sqlite3
from unittest.mock import patch

import pytest

from arena.store import Store, SavingError


def played(s,name):
    tid=s.create_tournament(name,[{'name':'A','sha256':'a','threads':1},{'name':'B','sha256':'b','threads':1}],
        {'cycles':5,'time_control':{'kind':'fischer','seconds':180,'increment':2}},backup=False)['id']
    s.set_state(tid,'running');s.fill_queue(tid,10)
    for i in range(10):
        g=s.claim(tid);s.finish(g['aid'],'1-0' if i%2 else '0-1','fixture')
    s.set_state(tid,'paused');return tid


def verify(db,removed,kept):
    assert db.execute('SELECT count(*) FROM rc_games WHERE tid=?',(removed,)).fetchone()[0]==0
    assert db.execute('SELECT count(*) FROM rc_games WHERE tid=?',(kept,)).fetchone()[0]==10
    assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'


def test_deletion_with_report_reader_preserves_reader_snapshot_and_new_results(tmp_path):
    s=Store(tmp_path)
    try:
        removed=played(s,'Test');kept=played(s,'Keep')
        s.export_pending();s.backup()
        # A report owns a WAL read snapshot while deletion commits. It must
        # neither block on compaction nor discard the reader's existing view.
        with closing(sqlite3.connect(s.path.as_uri()+'?mode=ro',uri=True)) as reader:
            reader.execute('BEGIN')
            assert reader.execute('SELECT count(*) FROM tournaments').fetchone()[0]==2
            s.db.execute('PRAGMA busy_timeout=50')
            s.delete_tournament(removed,'Test',keep_ratings=False)
            assert not s.failure and not s.one('SELECT 1 FROM storage_jobs')
            assert reader.execute('SELECT count(*) FROM tournaments').fetchone()[0]==2
            verify(s.db,removed,kept)
        assert s.snapshot(kept)['official_games']==10
    finally:s.close()
    s=Store(tmp_path)
    try:verify(s.db,removed,kept)
    finally:s.close()


@pytest.mark.parametrize('point',['copy_flush','main_finish'])
def test_rating_removal_retries_after_failure_without_losing_other_sources(tmp_path,point):
    s=Store(tmp_path);removed=played(s,'Test');kept=played(s,'Keep')
    s.export_pending();s.backup();backup=s.backup_file;stamp=backup.stat().st_mtime_ns
    try:
        target='os.fsync' if point=='copy_flush' else 'arena.storage.finish_record_cleanup'
        with patch(target,side_effect=OSError('Injected cleanup failure')):
            with pytest.raises(SavingError):
                s.rating_center_call('command',{'action':'remove_source','pool':'main','tid':removed,'confirmed':True})
        verify(s.db,removed,kept)
        if point=='copy_flush':
            with closing(sqlite3.connect(backup)) as db:
                assert db.execute('SELECT count(*) FROM rc_games').fetchone()[0]==20
                assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
    finally:s.close()
    s=Store(tmp_path)
    try:
        verify(s.db,removed,kept)
        assert s.snapshot(removed)['official_games']==10
        assert not s.one('SELECT 1 FROM storage_jobs') and not s.failure
        assert backup.stat().st_mtime_ns==stamp
        with closing(sqlite3.connect(backup)) as db:verify(db,removed,kept)
    finally:s.close()
