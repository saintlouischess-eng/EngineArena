import asyncio
import json
from unittest.mock import patch

from arena.store import Store
from arena.tournament_report import render
from arena.report_jobs import ReportJobs


def completed(store):
    tid=store.create_tournament('Completed stress fixture',[{'name':'A'},{'name':'B'}],{'cycles':1},backup=False)['id']
    store.set_state(tid,'running');store.fill_queue(tid,2)
    while g:=store.claim(tid):store.finish(g['aid'],'1/2-1/2','fixture')
    store.execute("UPDATE tournaments SET state='completed' WHERE id=?",(tid,))
    store.export_pending()
    return tid


def test_clean_reopen_reuses_verified_backup_without_new_copy(tmp_path):
    store=Store(tmp_path);tid=completed(store);store.backup()
    path=store.backup_file;stamp=path.stat().st_mtime_ns
    revision=store.one('SELECT revision FROM workspace_version')['revision']
    checked=store.checked_at;store.close()
    assert (tmp_path/'clean-shutdown.json').exists()
    store=Store(tmp_path)
    try:
        assert not (tmp_path/'clean-shutdown.json').exists()
        assert store.checked_at==checked
        assert store.one('SELECT revision FROM workspace_version')['revision']==revision
        assert not store.backup(force=False)
        assert path.stat().st_mtime_ns==stamp
        assert store.snapshot(tid)['official_games']==2
        store.execute("UPDATE tournaments SET note='New report note' WHERE id=?",(tid,))
        assert store.backup(force=False)
    finally:store.close()


def test_stale_or_missing_backup_is_not_reused(tmp_path):
    store=Store(tmp_path);completed(store);store.backup();backup=store.backup_file;store.close()
    backup.unlink()
    store=Store(tmp_path)
    try:assert store.backup(force=False)
    finally:store.close()


def test_finished_deletion_ledger_does_not_dirty_every_reopen(tmp_path):
    from arena.deletion import ledger
    store=Store(tmp_path);tid=completed(store);store.backup()
    html=render(store.path,tid)
    with ledger(tmp_path) as log:log.execute("INSERT INTO deleted VALUES('already-removed')")
    store.close();store=Store(tmp_path)
    try:
        assert not store.backup(force=False)
        with patch('arena.engine_readout.collect',side_effect=AssertionError('Unexpected move rescan')):
            assert render(store.path,tid)==html
    finally:store.close()


def test_receipt_does_not_hide_changed_database_or_expired_check(tmp_path):
    store=Store(tmp_path);completed(store);store.close()
    receipt=tmp_path/'clean-shutdown.json'
    value=json.loads(receipt.read_text());value['checked_at']=1;receipt.write_text(json.dumps(value))
    store=Store(tmp_path)
    assert store.checked_at>1
    checked=store.checked_at;store.close()
    value=json.loads(receipt.read_text());value['database'][0][1]-=1;receipt.write_text(json.dumps(value))
    store=Store(tmp_path)
    assert store.checked_at>checked
    store.close()


def test_report_cache_survives_reopen_and_invalidates_on_edit(tmp_path):
    store=Store(tmp_path);tid=completed(store)
    first=render(store.path,tid)
    store.close();store=Store(tmp_path)
    try:
        with patch('arena.engine_readout.collect',side_effect=AssertionError('Unexpected move rescan')):
            assert render(store.path,tid)==first
            store.execute("INSERT INTO preferences VALUES('ui','{}')",report_change=False)
            assert render(store.path,tid)==first
            assert 'Normal 90% CI' in render(store.path,tid,confidence=90)
            assert 'All 2 participants' in render(store.path,tid,all_engines=True)
        store.execute("UPDATE tournaments SET note='Updated saved note' WHERE id=?",(tid,))
        updated=render(store.path,tid)
        assert 'Updated saved note' in updated and updated!=first
        # Cache scopes include confidence, language and whether technical data is requested.
        assert render(store.path,tid,confidence=90,technical=False)!=updated
        assert render(store.path,tid,confidence=90,technical=False)==render(store.path,tid,confidence=90,technical=False)
    finally:store.close()


def test_report_cancellation_and_shutdown_leave_results_untouched(tmp_path):
    store=Store(tmp_path);tid=completed(store);store.close()
    async def run():
        reports=ReportJobs()
        job=await reports.start(str(tmp_path/'arena.sqlite3'),tid,95,False,True,'en')
        process=reports.jobs[job['id']]['process']
        await asyncio.wait_for(reports.cancel(job['id']),5)
        assert reports.status(job['id'])['state']=='cancelled'
        assert not process.is_alive()
        html=await reports.render(str(tmp_path/'arena.sqlite3'),tid,95,False,False,'en')
        assert '2 scheduled' in html
        job=await reports.start(str(tmp_path/'arena.sqlite3'),tid,95,False,True,'en')
        process=reports.jobs[job['id']]['process']
        await asyncio.wait_for(reports.close(),5)
        assert not process.is_alive()
    asyncio.run(run())
    store=Store(tmp_path)
    try:assert store.snapshot(tid)['official_games']==2
    finally:store.close()
