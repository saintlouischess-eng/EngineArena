"""Lossless, bounded UCI log blocks. Legacy text rows remain readable until migrated."""
import collections
import json
import time
import zlib


def initialize(db):
    db.executescript('''CREATE TABLE IF NOT EXISTS log_blocks(
        id INTEGER PRIMARY KEY, last_id INTEGER NOT NULL, aid TEXT NOT NULL,
        lines INTEGER NOT NULL, raw_bytes INTEGER NOT NULL, body BLOB NOT NULL);
        CREATE INDEX IF NOT EXISTS log_blocks_attempt ON log_blocks(aid,id);
        CREATE INDEX IF NOT EXISTS log_blocks_last ON log_blocks(last_id);''')
    db.execute('CREATE TABLE IF NOT EXISTS log_packing(aid TEXT PRIMARY KEY,last_id INTEGER NOT NULL)')


def insert(db,aid,rows):
    raw=json.dumps(rows,ensure_ascii=False,separators=(',',':')).encode('utf-8')
    db.execute('INSERT INTO log_blocks VALUES(?,?,?,?,?,?)',
               (rows[0][0],rows[-1][0],aid,len(rows),len(raw),zlib.compress(raw,6)))


def append(store,aid,lines):
    # Called inside the move/result transaction: diagnostics commit with the move.
    if not lines:return
    if not hasattr(store,'log_sequence'):
        store.log_sequence=max(store.db.execute('SELECT coalesce(max(id),0) FROM logs').fetchone()[0],
                               store.db.execute('SELECT coalesce(max(last_id),0) FROM log_blocks').fetchone()[0])
    stamp=time.time()
    for start in range(0,len(lines),512):
        rows=[]
        for line in lines[start:start+512]:
            store.log_sequence+=1;rows.append([store.log_sequence,line[:4096],stamp])
        insert(store.db,aid,rows)


def read(db,aid,limit=300,descending=True):
    order='DESC' if descending else 'ASC'
    rows=[list(r) for r in db.execute(f'SELECT id,line,created FROM logs WHERE aid=? ORDER BY id {order} LIMIT ?',(aid,limit))]
    exists=db.execute("SELECT 1 FROM sqlite_master WHERE name='log_blocks'").fetchone()
    if exists:
        count=0
        for block in db.execute(f'SELECT body FROM log_blocks WHERE aid=? ORDER BY id {order}',(aid,)):
            values=json.loads(zlib.decompress(block[0]));rows.extend(values);count+=len(values)
            if count>=limit:break
    rows.sort(key=lambda r:r[0],reverse=descending)
    return [{'line':r[1],'created':r[2]} for r in rows[:limit]]


def pack_attempt(db,aid):
    """Pack completed searches together, preserving every line/id/timestamp.

    Caller owns the transaction. Existing zlib readers remain compatible.
    Running games retain per-move durable blocks until they finish.
    """
    last=db.execute('SELECT max(last_id) FROM log_blocks WHERE aid=?',(aid,)).fetchone()[0]
    if last is None:return
    saved=db.execute('SELECT last_id FROM log_packing WHERE aid=?',(aid,)).fetchone()
    if saved and saved[0]>=last:return
    blocks=db.execute('SELECT id,body FROM log_blocks WHERE aid=? ORDER BY id',(aid,)).fetchall()
    # Keep only compressed blocks plus one bounded decoded output block.
    db.execute('DELETE FROM log_blocks WHERE aid=?',(aid,))
    pending=[];size=0
    for _,body in blocks:
        for row in json.loads(zlib.decompress(body)):
            pending.append(row);size+=len(row[1].encode('utf-8'))+40
            if len(pending)>=1024 or size>=262144:
                insert(db,aid,pending);pending=[];size=0
    if pending:insert(db,aid,pending)
    db.execute('INSERT OR REPLACE INTO log_packing VALUES(?,?)',(aid,last))


def pack_completed(db,progress=lambda **kw:None,transaction=None):
    initialize(db);after='';processed=0
    while True:
        attempts=db.execute('''SELECT a.id FROM attempts a WHERE a.ended IS NOT NULL AND a.id>?
            AND coalesce((SELECT max(last_id) FROM log_blocks WHERE aid=a.id),0)>
                coalesce((SELECT last_id FROM log_packing WHERE aid=a.id),0)
            ORDER BY a.id LIMIT 128''',(after,)).fetchall()
        if not attempts:return
        # Maintenance runs only when idle. Amortize FULL fsync over a bounded
        # batch; a crash rolls back just this batch and earlier cursors survive.
        with transaction() if transaction else db:
            for (aid,) in attempts:
                pack_attempt(db,aid);after=aid;processed+=1
        progress(attempts_packed=processed)


def migrate(db,progress=lambda **kw:None,transaction=None):
    """Each batch is atomic and restartable; retain original order and timestamps."""
    initialize(db);processed=0
    while True:
        rows=db.execute('SELECT id,aid,line,created FROM logs ORDER BY id LIMIT 4096').fetchall()
        if not rows:break
        grouped=collections.defaultdict(list)
        for ident,aid,line,created in rows:grouped[aid].append([ident,line,created])
        # A supplied Store transaction also invalidates its backup revision.
        with transaction() if transaction else db:
            for aid,values in grouped.items():insert(db,aid,values)
            db.execute('DELETE FROM logs WHERE id<=?',(rows[-1][0],))
        processed+=len(rows);progress(lines_processed=processed)
    return processed
