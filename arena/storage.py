"""Storage maintenance with durable intent, lossless logs and verified replacement."""
from contextlib import closing
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import time

DEFAULTS={'backup_copies':3,'backup_minutes':5}


def backup_interval(config,state):
    return max(config['backup_minutes']*60,min(3600,10*(state.get('duration_seconds') or 0)))


def settings(value=None):
    value=DEFAULTS| (value or {})
    for key,low,high in [('backup_copies',2,10),('backup_minutes',1,60)]:
        n=value[key]
        if isinstance(n,bool) or not isinstance(n,(int,float)) or int(n)!=n or not low<=n<=high:
            raise ValueError(f'{key.replace("_"," ")} must be a whole number from {low} to {high}')
        value[key]=int(n)
    return {key:value[key] for key in DEFAULTS}


def initialize(store):
    from .log_storage import initialize as logs
    logs(store.db)
    store.db.execute('CREATE TABLE IF NOT EXISTS storage_jobs(name TEXT PRIMARY KEY)')
    row=store.db.execute("SELECT body FROM preferences WHERE name='storage'").fetchone()
    store.storage_settings=settings(json.loads(row[0]) if row else None)
    store.maintenance_state={'phase':'idle','busy':False}


def progress(store,**values):
    store.maintenance_state=store.maintenance_state|values


def ensure_idle(store):
    if (store.one("SELECT 1 FROM tournaments WHERE state IN ('running','draining') LIMIT 1") or
        store.one('SELECT 1 FROM attempts WHERE ended IS NULL LIMIT 1') or
        store.one("SELECT 1 FROM experiments WHERE state='running' LIMIT 1") or
        store.one("SELECT 1 FROM player_games WHERE state IN ('starting','playing') LIMIT 1")):
        raise ValueError('Stop or pause and drain all tournaments and experiments before storage maintenance')


def save_settings(store,value):
    config=settings(value)
    store.execute("INSERT OR REPLACE INTO preferences VALUES('storage',?)",(json.dumps(config),))
    store.storage_settings=config
    return config


def snapshots(folder):
    found=[]
    for path in (folder/'backups').glob('recovery-*.sqlite3'):
        try:found.append((path.stat().st_mtime_ns,path))
        except FileNotFoundError:pass
    return [p for _,p in sorted(found,reverse=True)]


def scratch_files(folder):
    directory=folder/'backups'
    if not directory.exists():return []
    result=[]
    for p in directory.iterdir():
        if not p.is_file() or p.is_symlink():continue
        if re.fullmatch(r'(?:backup\.tmp|recovery-\d+\.(?:compact|delete|ratings)\.tmp)(?:-wal|-shm|-journal)?',p.name):
            result.append(p);continue
        # A retired snapshot may leave a WAL/shared-memory file behind after
        # an interrupted reader. Never remove sidecars of an existing snapshot.
        orphan=re.fullmatch(r'(recovery-\d+\.sqlite3)-(?:wal|shm|journal)',p.name)
        if orphan and not (directory/orphan[1]).exists():result.append(p)
    return result


def prune(store):
    # Only called after a new, fully verified snapshot has been published.
    for path in snapshots(store.folder)[store.storage_settings['backup_copies']:]:path.unlink()


def inventory(store):
    def size(path):
        try:return path.stat().st_size
        except FileNotFoundError:return 0
    files=snapshots(store.folder)
    result={'settings':dict(store.storage_settings),'maintenance':dict(store.maintenance_state),
            'effective_backup_seconds':backup_interval(store.storage_settings,store.backup_state),
            'last_backup_seconds':store.backup_state.get('duration_seconds'),
            'database_bytes':size(store.path),'wal_bytes':size(Path(str(store.path)+'-wal')),
            'backup_bytes':sum(size(p) for p in files),'backup_count':len(files),
            'pgn_bytes':sum(size(store.folder/name) for name in ('games.pgn','interrupted.pgn')),
            'temporary_bytes':sum(size(p) for p in scratch_files(store.folder)),
            'free_disk_bytes':shutil.disk_usage(store.folder).free,'reclaimable_bytes':None}
    result['total_bytes']=sum(result[k] for k in ('database_bytes','wal_bytes','backup_bytes','pgn_bytes','temporary_bytes'))
    result['forecast']=None
    # Skip SQL while maintenance is working; its state stays available immediately.
    if not result['maintenance'].get('busy'):
        with closing(sqlite3.connect(store.path.as_uri()+'?mode=ro',uri=True,timeout=1)) as db:
            db.execute('BEGIN')
            result['reclaimable_bytes']=db.execute('PRAGMA freelist_count').fetchone()[0]*db.execute('PRAGMA page_size').fetchone()[0]
            result['legacy_logs']=bool(db.execute('SELECT 1 FROM logs LIMIT 1').fetchone())
            if not result['legacy_logs']:
                result['legacy_logs']=bool(db.execute('''SELECT 1 FROM attempts a WHERE a.ended IS NOT NULL
                    AND NOT EXISTS(SELECT 1 FROM log_packing p WHERE p.aid=a.id)
                    AND EXISTS(SELECT 1 FROM log_blocks b WHERE b.aid=a.id) LIMIT 1''').fetchone())
            from .storage_forecast import collect
            result['forecast']=collect(db,result)
    return result


def compact(db):
    # SQLite VACUUM is transactional. Never rename the open production database.
    db.commit()
    db.execute('VACUUM')
    checkpoint=db.execute('PRAGMA wal_checkpoint(TRUNCATE)').fetchone()
    if checkpoint and checkpoint[0]:raise OSError('Database readers prevented space reclamation; close report windows and retry storage cleanup')
    if db.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise OSError('Compacted database integrity check failed')


def compact_snapshot(store,path,index,total):
    from .deletion import discard_temporary
    from .log_storage import migrate,pack_completed
    temporary=path.with_suffix('.compact.tmp');discard_temporary(temporary)
    stamp=path.stat();progress(store,phase=f'Compressing backup {index} of {total}',lines_processed=0)
    with closing(sqlite3.connect(path.as_uri()+'?mode=ro',uri=True)) as source:
        with closing(sqlite3.connect(temporary)) as dest:
            source.backup(dest);dest.execute('PRAGMA journal_mode=DELETE')
            migrate(dest,lambda **kw:progress(store,**kw))
            pack_completed(dest,lambda **kw:progress(store,**kw))
            if dest.execute("SELECT 1 FROM sqlite_master WHERE name='storage_jobs'").fetchone():
                with dest:dest.execute('DELETE FROM storage_jobs')
            progress(store,phase=f'Compacting backup {index} of {total}')
            compact(dest)
    with temporary.open('r+b') as f:f.flush();os.fsync(f.fileno())
    os.utime(temporary,ns=(stamp.st_atime_ns,stamp.st_mtime_ns));os.replace(temporary,path)


def optimize(store):
    from .store import SavingError
    from .log_storage import migrate,pack_completed
    ensure_idle(store)
    before=inventory(store);started=time.monotonic()
    progress(store,busy=True,phase='Compressing engine logs',error='',lines_processed=0,before_bytes=before['total_bytes'])
    try:
        # A failed deletion can leave PGN/snapshot cleanup pending. Honor its
        # durable ledger before producing any new compact recovery image.
        from .deletion import apply_pending
        apply_pending(store)
        progress(store,busy=True,phase='Compressing engine logs',error='',lines_processed=0)
        store.execute("INSERT OR IGNORE INTO storage_jobs VALUES('optimize')")
        with store.backup_lock:
            migrate(store.db,lambda **kw:progress(store,**kw),store.tx)
            progress(store,phase='Packing completed-game diagnostics',attempts_packed=0)
            pack_completed(store.db,lambda **kw:progress(store,**kw),store.tx)
            progress(store,phase='Compacting main database')
            compact(store.db)
            progress(store,phase='Creating verified recovery snapshot')
            store._backup_snapshot()
            files=snapshots(store.folder)
            for i,path in enumerate(files,1):compact_snapshot(store,path,i,len(files))
            store.execute("DELETE FROM storage_jobs WHERE name='optimize'")
            compact(store.db)
            for path in scratch_files(store.folder):path.unlink(missing_ok=True)
            store.backup_revision=-1
            files=snapshots(store.folder)
            store._backup_progress(backup_count=len(files),total_bytes=sum(p.stat().st_size for p in files))
        progress(store,busy=False,phase='Complete',duration_seconds=round(time.monotonic()-started,2))
        after=inventory(store)
        progress(store,after_bytes=after['total_bytes'],reclaimed_bytes=max(0,before['total_bytes']-after['total_bytes']))
        if store.failure.startswith(('Storage cleanup did not finish:','Tournament deletion cleanup failed:','Backup saving failed:')):store.failure=''
        return inventory(store)
    except (OSError,sqlite3.Error,SavingError) as exc:
        message=f'Storage cleanup did not finish: {exc}. Saved results are retained. Retry cleanup to continue.'
        progress(store,busy=False,phase='Failed',error=message)
        store.failure=message;raise SavingError(message) from exc


def resume(store):
    if store.one("SELECT 1 FROM storage_jobs WHERE name='optimize'"):optimize(store)
