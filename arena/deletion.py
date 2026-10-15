"""Durable tournament deletion, including shared PGNs and recovery snapshots.

The independent ledger contains only opaque IDs. It survives restoring an older
arena database, and makes an interrupted deletion safe to repeat at startup.
"""
from contextlib import closing
import os
from pathlib import Path
import sqlite3


def ledger(folder):
    db=sqlite3.connect(folder/'deletions.sqlite3')
    db.execute('PRAGMA synchronous=FULL')
    db.execute('CREATE TABLE IF NOT EXISTS deleted(id TEXT PRIMARY KEY)')
    db.execute('CREATE TABLE IF NOT EXISTS deleted_events(id TEXT PRIMARY KEY)')
    db.execute('CREATE TABLE IF NOT EXISTS kept_ratings(id TEXT PRIMARY KEY)')
    db.execute('CREATE TABLE IF NOT EXISTS rating_actions(seq INTEGER PRIMARY KEY,body TEXT)')
    db.commit()
    return db


def preview(store,tid):
    t=store.tournament(tid)
    counts=store.one('''SELECT count(*) games,coalesce(sum(official IS NOT NULL),0) official
        FROM games WHERE tid=?''',(tid,))
    attempts=store.one('SELECT count(*) n FROM attempts WHERE gid IN (SELECT id FROM games WHERE tid=?)',(tid,))['n']
    return {'id':tid,'name':t['name'],'scheduled':t['total'],'attempts':attempts,**counts}


def prepare_ids(db,ids):
    db.execute('CREATE TEMP TABLE IF NOT EXISTS deleted_tournaments(id TEXT PRIMARY KEY)')
    db.execute('DELETE FROM deleted_tournaments')
    db.executemany('INSERT INTO deleted_tournaments VALUES(?)',((tid,) for tid in ids))


def contains_deleted(db,ids,event_ids=()):
    prepare_ids(db,ids)
    found=db.execute('SELECT 1 FROM tournaments WHERE id IN (SELECT id FROM deleted_tournaments) LIMIT 1').fetchone() is not None
    if event_ids and db.execute("SELECT 1 FROM sqlite_master WHERE name='events'").fetchone():
        import json
        found=found or bool(db.execute('SELECT 1 FROM events WHERE id IN (SELECT value FROM json_each(?)) LIMIT 1',(json.dumps(event_ids),)).fetchone())
    return found


def discard_temporary(path):
    # Only known scratch images, never a verified recovery snapshot. A process
    # kill can leave SQLite sidecars, which must not attach to a fresh image.
    for suffix in ('','-wal','-shm','-journal'):Path(str(path)+suffix).unlink(missing_ok=True)


def purge(db,ids,event_ids=(),keep_ratings=()):
    """Caller owns the transaction. Bounded Python memory even for huge histories."""
    if not contains_deleted(db,ids,event_ids):return False
    if event_ids and db.execute("SELECT 1 FROM sqlite_master WHERE name='event_children'").fetchone():
        import json
        # Discover children independently in every recovery snapshot, including
        # stages no longer present in the current workspace.
        raw=json.dumps(event_ids)
        db.execute('INSERT OR IGNORE INTO deleted_tournaments SELECT tid FROM event_children WHERE eid IN (SELECT value FROM json_each(?))',(raw,))
        if db.execute("SELECT 1 FROM sqlite_master WHERE name='rc_games'").fetchone():
            db.execute('DELETE FROM rc_games WHERE tid IN (SELECT tid FROM event_children WHERE valid=0 AND eid IN (SELECT value FROM json_each(?)))',(raw,))
        db.execute('DELETE FROM event_children WHERE eid IN (SELECT value FROM json_each(?))',(raw,))
        db.execute('DELETE FROM event_decisions WHERE eid IN (SELECT value FROM json_each(?))',(raw,))
        db.execute('DELETE FROM events WHERE id IN (SELECT value FROM json_each(?))',(raw,))
        if db.execute("SELECT 1 FROM sqlite_master WHERE name='audit'").fetchone():
            db.execute("DELETE FROM audit WHERE tid IS NULL AND json_valid(body) AND json_extract(body,'$.event') IN (SELECT value FROM json_each(?))",(raw,))
    db.execute('CREATE TEMP TABLE IF NOT EXISTS deleted_games(id TEXT PRIMARY KEY)')
    db.execute('CREATE TEMP TABLE IF NOT EXISTS deleted_attempts(id TEXT PRIMARY KEY)')
    db.execute('DELETE FROM deleted_games');db.execute('DELETE FROM deleted_attempts')
    db.execute('INSERT INTO deleted_games SELECT id FROM games WHERE tid IN (SELECT id FROM deleted_tournaments)')
    db.execute('INSERT INTO deleted_attempts SELECT id FROM attempts WHERE gid IN (SELECT id FROM deleted_games)')
    tables={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if 'rc_games' in tables:
        import json
        db.execute('DELETE FROM rc_games WHERE tid IN (SELECT tid FROM event_children WHERE valid=0) AND tid IN (SELECT id FROM deleted_tournaments)')
        db.execute('UPDATE rc_sources SET retained=1 WHERE tid IN (SELECT id FROM deleted_tournaments) AND tid IN (SELECT value FROM json_each(?))',(json.dumps(list(keep_ratings)),))
        db.execute('UPDATE rc_pools SET revision=revision+1 WHERE id IN (SELECT pool FROM rc_sources WHERE tid IN (SELECT id FROM deleted_tournaments))')
        db.execute('DELETE FROM rc_games WHERE tid IN (SELECT id FROM deleted_tournaments) AND tid NOT IN (SELECT value FROM json_each(?))',(json.dumps(list(keep_ratings)),))
        db.execute('DELETE FROM rc_sources WHERE tid IN (SELECT id FROM deleted_tournaments) AND retained=0')
        db.execute('DELETE FROM rc_imports WHERE tid IN (SELECT id FROM deleted_tournaments)')
        for table in ('rc_anchors','rc_refs'):
            db.execute(f'DELETE FROM {table} WHERE NOT EXISTS(SELECT 1 FROM rc_games g WHERE g.pool={table}.pool AND g.category={table}.category AND (g.white={table}.entry OR g.black={table}.entry))')
        from .rating_cleanup import gc
        gc(db)
    for table in ('run_attempts','attempt_engines'):
        if table in tables:db.execute(f'DELETE FROM {table} WHERE aid IN (SELECT id FROM deleted_attempts)')
    if 'engine_evidence' in tables:
        db.execute('DELETE FROM engine_evidence WHERE id NOT IN (SELECT evidence FROM attempt_engines)')
    for table in ('moves','logs','outbox'):
        db.execute(f'DELETE FROM {table} WHERE aid IN (SELECT id FROM deleted_attempts)')
    if 'log_blocks' in tables:db.execute('DELETE FROM log_blocks WHERE aid IN (SELECT id FROM deleted_attempts)')
    if 'log_packing' in tables:db.execute('DELETE FROM log_packing WHERE aid IN (SELECT id FROM deleted_attempts)')
    db.execute('DELETE FROM attempts WHERE id IN (SELECT id FROM deleted_attempts)')
    db.execute('DELETE FROM games WHERE id IN (SELECT id FROM deleted_games)')
    tables={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    for table in ('participants','aggregates','engine_failures','audit','round_state','game_counts','rankings','ranking_meta',
                  'sequential_state','sequential_samples','rating_anchors','report_revisions','run_sessions','opening_suites','tournament_queue','pgn_links','pgn_changes'):
        if table in tables:db.execute(f'DELETE FROM {table} WHERE tid IN (SELECT id FROM deleted_tournaments)')
    if 'event_children' in tables:
        db.execute('DELETE FROM event_children WHERE tid IN (SELECT id FROM deleted_tournaments)')
        db.execute("DELETE FROM event_decisions WHERE eid IN (SELECT id FROM events WHERE state='retired' AND id NOT IN (SELECT eid FROM event_children))")
        db.execute("DELETE FROM events WHERE state='retired' AND id NOT IN (SELECT eid FROM event_children)")
    if 'queue_control' in tables:
        db.execute("""UPDATE queue_control SET active_tid=NULL,mode='paused',revision=revision+1,
          note='The current queue tournament was deleted. Review the queue before resuming.'
          WHERE active_tid IN (SELECT id FROM deleted_tournaments)""")
    db.execute('DELETE FROM tournaments WHERE id IN (SELECT id FROM deleted_tournaments)')
    db.execute('CREATE TABLE IF NOT EXISTS pgn_rebuild(stream TEXT PRIMARY KEY)')
    db.executemany('INSERT OR IGNORE INTO pgn_rebuild VALUES(?)',[('games',),('interrupted',)])
    db.execute('CREATE TABLE IF NOT EXISTS storage_jobs(name TEXT PRIMARY KEY)')
    db.execute("INSERT OR IGNORE INTO storage_jobs VALUES('delete')")
    return True


def rebuild_pgn(store):
    """Replace whole streams atomically; a durable marker survives rename/commit gaps."""
    for row in store.rows('SELECT stream FROM pgn_rebuild'):
        stream=row['stream']
        if stream not in ('games','interrupted'):raise ValueError('Unknown PGN stream')
        path=store.folder/(stream+'.pgn');temporary=store.folder/(stream+'.pgn.rebuild')
        last=0
        with temporary.open('wb') as f:
            cursor=store.db.execute('SELECT id,pgn FROM outbox WHERE stream=? ORDER BY id',(stream,))
            while rows:=cursor.fetchmany(64):
                for entry in rows:f.write(entry['pgn'].encode('utf-8'));last=entry['id']
            offset=f.tell();f.flush();os.fsync(f.fileno())
        os.replace(temporary,path)
        with store.tx():
            store.db.execute('INSERT OR REPLACE INTO exports VALUES(?,?,?)',(stream,last,offset))
            store.db.execute('DELETE FROM pgn_rebuild WHERE stream=?',(stream,))


def apply_pending(store):
    from .store import SavingError
    from .storage import compact,progress,scratch_files
    from .rating_cleanup import pending as rating_pending
    rating_pending(store)
    try:
        with closing(ledger(store.folder)) as log:
            keep_ratings=[r[0] for r in log.execute('SELECT id FROM kept_ratings')]
            ids=[r[0] for r in log.execute('SELECT id FROM deleted')]
            event_ids=[r[0] for r in log.execute('SELECT id FROM deleted_events')]
        if not ids and not event_ids:return
        with store.backup_lock:
            progress(store,busy=True,phase='Removing deleted tournament records',error='')
            # Preparing TEMP lookup rows increments SQLite total_changes too.
            # Check outside the durable transaction so old deletion receipts do
            # not make an unchanged workspace dirty at every launch.
            if contains_deleted(store.db,ids,event_ids):
                from .report_cache import clear
                clear(store.folder)
                with store.tx():purge(store.db,ids,event_ids,keep_ratings)
            # Each original snapshot stays recoverable until its scrubbed copy is
            # complete. Keep timestamps so recovery still chooses the newest one.
            recovery_files=list((store.folder/'backups').glob('recovery-*.sqlite3'))
            for index,path in enumerate(recovery_files,1):
                with closing(sqlite3.connect(path,isolation_level=None)) as source:
                    if not contains_deleted(source,ids,event_ids):continue
                    progress(store,phase=f'Cleaning recovery backup {index} of {len(recovery_files)}')
                    stamp=path.stat();temporary=path.with_suffix('.delete.tmp')
                    discard_temporary(temporary)
                    with closing(sqlite3.connect(temporary)) as dest:
                        source.backup(dest)
                        dest.execute('PRAGMA journal_mode=DELETE')
                        with dest:purge(dest,ids,event_ids,keep_ratings)
                        with dest:dest.execute("DELETE FROM storage_jobs WHERE name='delete'")
                        progress(store,phase=f'Compacting backup {index} of {len(recovery_files)}')
                        compact(dest)
                with temporary.open('r+b') as f:f.flush();os.fsync(f.fileno())
                os.utime(temporary,ns=(stamp.st_atime_ns,stamp.st_mtime_ns));os.replace(temporary,path)
            discard_temporary(store.folder/'backups'/'backup.tmp')
            rebuild_pgn(store)
            if store.one("SELECT 1 FROM storage_jobs WHERE name='delete'"):
                progress(store,phase='Returning deleted database space to Windows')
                compact(store.db)
                store.execute("DELETE FROM storage_jobs WHERE name='delete'")
                store.db.execute('PRAGMA wal_checkpoint(TRUNCATE)')
                store.backup_revision=-1
            # Clear abandoned cleanup images and sidecars of retired snapshots
            # only after verified replacements and main compaction succeed.
            for path in scratch_files(store.folder):path.unlink(missing_ok=True)
            files=list((store.folder/'backups').glob('recovery-*.sqlite3'))
            store._backup_progress(backup_count=len(files),total_bytes=sum(p.stat().st_size for p in files))
            progress(store,busy=False,phase='Complete')
    except (OSError,sqlite3.Error,SavingError) as exc:
        progress(store,busy=False,phase='Failed',error=str(exc))
        store.failure=f'Tournament deletion cleanup failed: {exc}. Scheduling stopped. Retry saving or reopen to finish cleanup.'
        raise SavingError(store.failure) from exc


def delete(store,tid,name,keep_ratings=True):
    from .events import membership
    member=membership(store,tid)
    if member and member['valid']:raise ValueError('Retire the event before deleting its current stages. This preserves qualification dependencies.')
    details=preview(store,tid)
    if details['name']!=name:raise ValueError('Tournament changed; review the deletion again')
    if store.one("SELECT 1 FROM tournaments WHERE state IN ('running','draining') LIMIT 1") or store.one('SELECT 1 FROM attempts WHERE ended IS NULL LIMIT 1') or store.one("SELECT 1 FROM experiments WHERE state='running' LIMIT 1"):
        raise ValueError('Stop or pause and drain all tournaments and experiments before deleting a tournament')
    try:
        with closing(ledger(store.folder)) as log:
            with log:
                log.execute('INSERT OR IGNORE INTO deleted VALUES(?)',(tid,))
                if keep_ratings:log.execute('INSERT OR IGNORE INTO kept_ratings VALUES(?)',(tid,))
    except (OSError,sqlite3.Error) as exc:
        from .store import SavingError
        store.failure=f'Tournament deletion could not be saved: {exc}. Scheduling stopped.'
        raise SavingError(store.failure) from exc
    apply_pending(store)
    return details
