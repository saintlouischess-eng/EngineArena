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


def contains_deleted(db,ids):
    prepare_ids(db,ids)
    return db.execute('SELECT 1 FROM tournaments WHERE id IN (SELECT id FROM deleted_tournaments) LIMIT 1').fetchone() is not None


def discard_temporary(path):
    # Only known scratch images, never a verified recovery snapshot. A process
    # kill can leave SQLite sidecars, which must not attach to a fresh image.
    for suffix in ('','-wal','-shm','-journal'):Path(str(path)+suffix).unlink(missing_ok=True)


def purge(db,ids):
    """Caller owns the transaction. Bounded Python memory even for huge histories."""
    if not contains_deleted(db,ids):return False
    db.execute('CREATE TEMP TABLE IF NOT EXISTS deleted_games(id TEXT PRIMARY KEY)')
    db.execute('CREATE TEMP TABLE IF NOT EXISTS deleted_attempts(id TEXT PRIMARY KEY)')
    db.execute('DELETE FROM deleted_games');db.execute('DELETE FROM deleted_attempts')
    db.execute('INSERT INTO deleted_games SELECT id FROM games WHERE tid IN (SELECT id FROM deleted_tournaments)')
    db.execute('INSERT INTO deleted_attempts SELECT id FROM attempts WHERE gid IN (SELECT id FROM deleted_games)')
    for table in ('moves','logs','outbox'):
        db.execute(f'DELETE FROM {table} WHERE aid IN (SELECT id FROM deleted_attempts)')
    db.execute('DELETE FROM attempts WHERE id IN (SELECT id FROM deleted_attempts)')
    db.execute('DELETE FROM games WHERE id IN (SELECT id FROM deleted_games)')
    tables={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    for table in ('participants','aggregates','audit','round_state','game_counts','rankings','ranking_meta',
                  'sequential_state','sequential_samples','rating_anchors','report_revisions'):
        if table in tables:db.execute(f'DELETE FROM {table} WHERE tid IN (SELECT id FROM deleted_tournaments)')
    db.execute('DELETE FROM tournaments WHERE id IN (SELECT id FROM deleted_tournaments)')
    db.execute('CREATE TABLE IF NOT EXISTS pgn_rebuild(stream TEXT PRIMARY KEY)')
    db.executemany('INSERT OR IGNORE INTO pgn_rebuild VALUES(?)',[('games',),('interrupted',)])
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
    try:
        with closing(ledger(store.folder)) as log:ids=[r[0] for r in log.execute('SELECT id FROM deleted')]
        if not ids:return
        with store.backup_lock:
            with store.tx():purge(store.db,ids)
            # Each original snapshot stays recoverable until its scrubbed copy is
            # complete. Keep timestamps so recovery still chooses the newest one.
            for path in (store.folder/'backups').glob('recovery-*.sqlite3'):
                with closing(sqlite3.connect(path,isolation_level=None)) as source:
                    if not contains_deleted(source,ids):continue
                    stamp=path.stat();temporary=path.with_suffix('.delete.tmp')
                    discard_temporary(temporary)
                    with closing(sqlite3.connect(temporary)) as dest:
                        source.backup(dest)
                        dest.execute('PRAGMA journal_mode=DELETE')
                        with dest:purge(dest,ids)
                        if dest.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise OSError('Deletion backup integrity check failed')
                with temporary.open('r+b') as f:f.flush();os.fsync(f.fileno())
                os.utime(temporary,ns=(stamp.st_atime_ns,stamp.st_mtime_ns));os.replace(temporary,path)
            discard_temporary(store.folder/'backups'/'backup.tmp')
            rebuild_pgn(store)
    except (OSError,sqlite3.Error) as exc:
        store.failure=f'Tournament deletion cleanup failed: {exc}. Scheduling stopped. Retry saving or reopen to finish cleanup.'
        raise SavingError(store.failure) from exc


def delete(store,tid,name):
    details=preview(store,tid)
    if details['name']!=name:raise ValueError('Tournament changed; review the deletion again')
    if store.one("SELECT 1 FROM tournaments WHERE state IN ('running','draining') LIMIT 1") or store.one('SELECT 1 FROM attempts WHERE ended IS NULL LIMIT 1') or store.one("SELECT 1 FROM experiments WHERE state='running' LIMIT 1"):
        raise ValueError('Stop or pause and drain all tournaments and experiments before deleting a tournament')
    try:
        with closing(ledger(store.folder)) as log:
            with log:log.execute('INSERT OR IGNORE INTO deleted VALUES(?)',(tid,))
    except (OSError,sqlite3.Error) as exc:
        from .store import SavingError
        store.failure=f'Tournament deletion could not be saved: {exc}. Scheduling stopped.'
        raise SavingError(store.failure) from exc
    apply_pending(store)
    return details
