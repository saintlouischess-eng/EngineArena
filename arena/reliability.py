"""Incremental engine failure counts, independent of official scoring."""
from .models import FAILURES
REASONS=tuple(r for r in FAILURES if r!='interrupted')
LABELS=','.join("'"+r+"'" for r in REASONS)

def initialize(store):
    if store.one("SELECT 1 FROM sqlite_master WHERE name='engine_failures'"):return
    with store.tx():
        store.db.execute('CREATE TABLE engine_failures(tid TEXT,slot INTEGER,reason TEXT,attempts INTEGER NOT NULL DEFAULT 0,official INTEGER NOT NULL DEFAULT 0,PRIMARY KEY(tid,slot,reason))')
        store.db.execute(f'CREATE INDEX IF NOT EXISTS attempts_failures ON attempts(reason,ended,gid) WHERE reason IN ({LABELS})')
        store.db.execute(f'''INSERT INTO engine_failures
            SELECT g.tid,CASE a.result WHEN '0-1' THEN g.white ELSE g.black END,a.reason,count(*),
                sum(CASE WHEN g.official=a.id AND g.invalid=0 THEN 1 ELSE 0 END)
            FROM attempts a JOIN games g ON g.id=a.gid
            WHERE a.reason IN ({LABELS}) AND a.result IN ('1-0','0-1') AND a.mode!='diagnostic'
            GROUP BY g.tid,2,a.reason''')

def delta(store,g,attempt,*,attempts=0,official=0):
    if attempt['reason'] not in REASONS or attempt['mode']=='diagnostic' or attempt['result'] not in ('1-0','0-1'):return
    slot=g['white'] if attempt['result']=='0-1' else g['black']
    store.db.execute('''INSERT INTO engine_failures VALUES(?,?,?,?,?)
        ON CONFLICT(tid,slot,reason) DO UPDATE SET attempts=attempts+excluded.attempts,official=official+excluded.official''',
        (g['tid'],slot,attempt['reason'],attempts,official))

def tf_source(db):
    if db.execute("SELECT 1 FROM sqlite_master WHERE name='engine_failures'").fetchone():
        return "(SELECT tid,slot,attempts,official FROM engine_failures WHERE reason='timeout')"
    return """(SELECT g.tid,CASE a.result WHEN '0-1' THEN g.white ELSE g.black END slot,
        count(*) attempts,sum(CASE WHEN g.official=a.id AND g.invalid=0 THEN 1 ELSE 0 END) official
        FROM attempts a JOIN games g ON g.id=a.gid WHERE a.reason='timeout'
        AND a.result IN ('1-0','0-1') AND a.mode!='diagnostic' GROUP BY g.tid,slot)"""

def page(store,tid,slot,reason='timeout',offset=0,limit=50):
    if reason not in REASONS or offset<0:raise ValueError('Invalid engine failure filter')
    profile=store.participant(tid,slot)
    rows=store.rows('SELECT reason,attempts,official FROM engine_failures WHERE tid=? AND slot=?',(tid,slot))
    items=store.rows('''SELECT g.id game,g.number,a.id attempt,a.seq,a.mode,a.result,a.reason,a.detail,a.ended,
        (g.official=a.id AND g.invalid=0) official,g.invalid,
        json_extract(w.profile,'$.name') white,json_extract(b.profile,'$.name') black
        FROM attempts a JOIN games g ON g.id=a.gid
        JOIN participants w ON w.tid=g.tid AND w.slot=g.white JOIN participants b ON b.tid=g.tid AND b.slot=g.black
        WHERE g.tid=? AND a.reason=? AND a.mode!='diagnostic' AND a.result IN ('1-0','0-1')
        AND CASE a.result WHEN '0-1' THEN g.white ELSE g.black END=?
        ORDER BY a.ended DESC,a.id LIMIT ? OFFSET ?''',(tid,reason,slot,min(100,max(1,limit)),offset))
    return {'name':profile['name'],'slot':slot,'reason':reason,'counts':rows,'items':items,
        'total':next((r['attempts'] for r in rows if r['reason']==reason),0),'offset':offset}
