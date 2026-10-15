"""Whole-event removal uses the durable deletion ledger, including empty drafts."""
import json
from contextlib import closing
from . import deletion


def selection(store,ids):
    if not isinstance(ids,list) or not ids or any(not isinstance(v,str) for v in ids):
        raise ValueError('Select events to delete.')
    ids=list(dict.fromkeys(ids))
    rows=store.rows('SELECT id,name,revision,state FROM events WHERE id IN (SELECT value FROM json_each(?)) ORDER BY id',(json.dumps(ids),))
    if len(rows)!=len(ids):raise ValueError('An event changed. Refresh the event list.')
    return rows


def preview(store,ids):
    rows=selection(store,ids);raw=json.dumps(ids)
    stages=store.rows('SELECT c.tid,t.name FROM event_children c JOIN tournaments t ON t.id=c.tid WHERE c.eid IN (SELECT value FROM json_each(?)) ORDER BY c.eid,c.stage,c.bucket',(raw,))
    tids=json.dumps([r['tid'] for r in stages])
    counts=store.one('SELECT count(*) games,coalesce(sum(official IS NOT NULL AND invalid=0),0) official FROM games WHERE tid IN (SELECT value FROM json_each(?))',(tids,))
    attempts=store.one('SELECT count(*) n FROM attempts WHERE gid IN (SELECT id FROM games WHERE tid IN (SELECT value FROM json_each(?)))',(tids,))['n']
    return dict(events=rows,stages=stages,attempts=attempts,**counts)


def delete(store,ids,expected,keep_ratings=True):
    from .storage import ensure_idle,inventory
    from .store import SavingError
    result=preview(store,ids)
    if result['events']!=expected:raise ValueError('An event changed. Preview deletion again.')
    ensure_idle(store)
    if store.one("SELECT 1 FROM events WHERE state='running' LIMIT 1"):
        raise ValueError('Pause and drain events before deleting records.')
    before=inventory(store)['total_bytes']
    try:
        with closing(deletion.ledger(store.folder)) as log:
            with log:
                if keep_ratings:log.executemany('INSERT OR IGNORE INTO kept_ratings VALUES(?)',((r['tid'],) for r in result['stages']))
                log.executemany('INSERT OR IGNORE INTO deleted_events VALUES(?)',((v,) for v in ids))
                log.executemany('INSERT OR IGNORE INTO deleted VALUES(?)',((r['tid'],) for r in result['stages']))
    except (OSError,__import__('sqlite3').Error) as exc:
        store.failure='Event deletion could not be saved: '+str(exc)
        raise SavingError(store.failure) from exc
    deletion.apply_pending(store)
    after=inventory(store)['total_bytes']
    return result|{'before_bytes':before,'after_bytes':after,'recovered_bytes':max(0,before-after)}
