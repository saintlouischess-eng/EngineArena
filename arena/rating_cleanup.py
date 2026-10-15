"""Replayable rating erasures, including rotating recovery backups."""
from contextlib import closing
import json
import os
import sqlite3
import time


def gc(db):
    db.execute('DELETE FROM rc_conditions WHERE id NOT IN (SELECT conditions FROM rc_games)')
    db.execute('DELETE FROM rc_entries WHERE id NOT IN (SELECT white FROM rc_games UNION SELECT black FROM rc_games UNION SELECT entry FROM rc_anchors UNION SELECT predecessor FROM rc_links UNION SELECT entry FROM rc_links UNION SELECT entry FROM rc_blocks)')
    if db.execute("SELECT 1 FROM sqlite_master WHERE name='rc_families'").fetchone():db.execute('DELETE FROM rc_families WHERE entry NOT IN (SELECT id FROM rc_entries) OR pool NOT IN (SELECT id FROM rc_pools)')


def apply(db,receipts):
    if not db.execute("SELECT 1 FROM sqlite_master WHERE name='rc_receipts'").fetchone():return False
    changed=False
    for seq,raw in receipts:
        if db.execute('SELECT 1 FROM rc_receipts WHERE seq=?',(seq,)).fetchone():continue
        b=json.loads(raw);pid=b['pool'];action=b['action'];cat=b.get('category','all')
        if db.execute("SELECT 1 FROM sqlite_master WHERE name='rc_families'").fetchone():
            if action=='delete_pool' or action=='reset' and cat=='all':db.execute('DELETE FROM rc_families WHERE pool=?',(pid,))
            elif action=='remove_entry':db.execute('DELETE FROM rc_families WHERE pool=? AND entry=?',(pid,b['entry']))
        if action=='reset':
            if cat=='all':
                for table in ('rc_games','rc_sources','rc_anchors','rc_refs','rc_gates','rc_imports','rc_links','rc_lineage','rc_blocks'):
                    db.execute(f'DELETE FROM {table} WHERE pool=?',(pid,))
                db.execute('UPDATE rc_pools SET epoch=? WHERE id=?',(b['at'],pid))
            else:
                db.execute('DELETE FROM rc_games WHERE pool=? AND category=?',(pid,cat))
                for table in ('rc_anchors','rc_refs'):db.execute(f'DELETE FROM {table} WHERE pool=? AND category=?',(pid,cat))
                db.execute('INSERT OR REPLACE INTO rc_gates VALUES(?,?,?)',(pid,cat,b['at']))
                # Explicit import permission cannot override a subsequent reset.
                db.execute('DELETE FROM rc_imports WHERE pool=? AND category=?',(pid,cat))
        elif action=='remove_source':
            db.execute('DELETE FROM rc_games WHERE pool=? AND tid=?',(pid,b['tid']))
            db.execute('DELETE FROM rc_imports WHERE pool=? AND tid=?',(pid,b['tid']))
            db.execute('UPDATE rc_sources SET enabled=0,explicit=0,cursor=-1 WHERE pool=? AND tid=?',(pid,b['tid']))
        elif action=='remove_entry':
            key=b['entry']
            # An exclusion made before GPU identities were introduced must not
            # resurrect those games when their history is explicitly reimported.
            affected="SELECT id FROM rc_entries WHERE id=? OR json_extract(body,'$.legacy_identity')=?"
            db.execute(f'DELETE FROM rc_games WHERE pool=? AND (white IN ({affected}) OR black IN ({affected}))',(pid,key,key,key,key))
            db.execute('INSERT OR IGNORE INTO rc_blocks VALUES(?,?)',(pid,key))
            for table in ('rc_anchors','rc_refs','rc_lineage'):db.execute(f'DELETE FROM {table} WHERE pool=? AND entry IN ({affected})',(pid,key,key))
            db.execute(f'DELETE FROM rc_links WHERE pool=? AND (entry IN ({affected}) OR predecessor IN ({affected}))',(pid,key,key,key,key))
        elif action=='delete_pool':
            for table in ('rc_games','rc_sources','rc_anchors','rc_refs','rc_gates','rc_imports','rc_blocks','rc_links','rc_lineage'):db.execute(f'DELETE FROM {table} WHERE pool=?',(pid,))
            db.execute('DELETE FROM rc_pools WHERE id=?',(pid,))
        else:raise ValueError('Invalid rating cleanup receipt')
        # Remove references with no retained data, then choose a stable new
        # internal reference when the next fit has evidence to use.
        for table in ('rc_anchors','rc_refs'):
            db.execute(f'DELETE FROM {table} WHERE pool=? AND NOT EXISTS(SELECT 1 FROM rc_games g WHERE g.pool={table}.pool AND g.category={table}.category AND (g.white={table}.entry OR g.black={table}.entry))',(pid,))
        db.execute('UPDATE rc_pools SET revision=revision+1 WHERE id=?',(pid,))
        db.execute('INSERT INTO rc_receipts VALUES(?)',(seq,));changed=True
    if changed:gc(db)
    return changed


def pending(store):
    from .deletion import ledger,discard_temporary
    from .storage import compact,progress
    from .store import SavingError
    try:
        with closing(ledger(store.folder)) as log:receipts=list(log.execute('SELECT seq,body FROM rating_actions ORDER BY seq'))
        if not receipts:return
        with store.backup_lock:
            missing=any(not store.one('SELECT 1 FROM rc_receipts WHERE seq=?',(seq,)) for seq,_ in receipts)
            if missing:
                progress(store,busy=True,phase='Removing rating records from recovery storage',error='')
                with store.tx():apply(store.db,receipts);store.db.execute("INSERT OR IGNORE INTO storage_jobs VALUES('ratings')")
            for path in (store.folder/'backups').glob('recovery-*.sqlite3'):
                with closing(sqlite3.connect(path)) as source:
                    if not source.execute("SELECT 1 FROM sqlite_master WHERE name='rc_receipts'").fetchone():continue
                    if all(source.execute('SELECT 1 FROM rc_receipts WHERE seq=?',(seq,)).fetchone() for seq,_ in receipts):continue
                    progress(store,busy=True,phase='Cleaning rating records in recovery backups',error='')
                    stamp=path.stat();temporary=path.with_suffix('.ratings.tmp');discard_temporary(temporary)
                    with closing(sqlite3.connect(temporary)) as dest:
                        source.backup(dest);dest.execute('PRAGMA journal_mode=DELETE')
                        with dest:apply(dest,receipts);dest.execute("DELETE FROM storage_jobs WHERE name='ratings'")
                        compact(dest)
                with temporary.open('r+b') as f:f.flush();os.fsync(f.fileno())
                os.utime(temporary,ns=(stamp.st_atime_ns,stamp.st_mtime_ns));os.replace(temporary,path)
            if store.one("SELECT 1 FROM storage_jobs WHERE name='ratings'"):
                compact(store.db);store.execute("DELETE FROM storage_jobs WHERE name='ratings'")
                store.db.execute('PRAGMA wal_checkpoint(TRUNCATE)');store.backup_revision=-1
            progress(store,busy=False,phase='Complete')
    except (sqlite3.Error,OSError) as exc:
        store.failure=f'Rating cleanup failed: {exc}. Scheduling stopped; retry saving to finish cleanup.'
        progress(store,busy=False,phase='Failed',error=store.failure)
        raise SavingError(store.failure) from exc


def request(store,body):
    from .storage import ensure_idle,inventory
    from .rating_center import CATEGORIES
    from .deletion import ledger
    if body.get('confirmed') is not True:raise ValueError('Confirm the rating-record deletion')
    if body['action']=='delete_pool' and body['pool']=='main':raise ValueError('Reset the main rating list instead of deleting it')
    if body.get('category','all') not in (*CATEGORIES,'all'):raise ValueError('Unknown rating category')
    if body['action']=='remove_source' and not store.one('SELECT 1 FROM rc_sources WHERE pool=? AND tid=?',(body['pool'],body.get('tid'))):raise ValueError('Rating source not found')
    if body['action']=='remove_entry' and not store.one('SELECT 1 FROM rc_entries WHERE id=?',(body.get('entry'),)):raise ValueError('Rating entry not found')
    ensure_idle(store);before=inventory(store)['total_bytes']
    try:
        with closing(ledger(store.folder)) as log:
            with log:log.execute('INSERT INTO rating_actions(body) VALUES(?)',(json.dumps(body|{'at':time.time()}),))
    except (sqlite3.Error,OSError) as exc:
        from .store import SavingError
        store.failure=f'Rating cleanup could not be saved: {exc}'
        raise SavingError(store.failure) from exc
    pending(store)
    return {'ok':True,'recovered_bytes':max(0,before-inventory(store)['total_bytes'])}
