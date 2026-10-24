"""Small persistent observation ledger. Unobserved time is never uptime."""
import time
import uuid


def initialize(store):
    store.db.executescript('''
      CREATE TABLE IF NOT EXISTS activity_sessions(id TEXT PRIMARY KEY,started REAL,last_seen REAL,ended REAL,outcome TEXT);
      CREATE TABLE IF NOT EXISTS activity_spans(session TEXT,tid TEXT,state TEXT,started REAL,last_seen REAL,
        PRIMARY KEY(session,tid,started));
      CREATE INDEX IF NOT EXISTS activity_tournament ON activity_spans(tid,started);
    ''')
    store.activity_id=uuid.uuid4().hex
    store.activity_due=0


def observe(store,active=(),stamp=None):
    stamp=time.time() if stamp is None else float(stamp)
    if time.monotonic()<store.activity_due:return
    store.activity_due=time.monotonic()+10
    active=set(active);sid=store.activity_id
    with store.tx():
        store.db.execute("UPDATE activity_sessions SET ended=last_seen,outcome='interrupted or unobserved shutdown' WHERE ended IS NULL AND id<>?",(sid,))
        row=store.one('SELECT * FROM activity_sessions WHERE id=?',(sid,))
        if not row:store.db.execute("INSERT INTO activity_sessions VALUES(?,?,?,NULL,'open')",(sid,stamp,stamp))
        elif stamp-row['last_seen']>60 or stamp<row['last_seen']:
            store.db.execute("UPDATE activity_sessions SET ended=last_seen,outcome='observation gap' WHERE id=?",(sid,))
            store.activity_id=sid=uuid.uuid4().hex
            store.db.execute("INSERT INTO activity_sessions VALUES(?,?,?,NULL,'open')",(sid,stamp,stamp))
        else:store.db.execute('UPDATE activity_sessions SET last_seen=? WHERE id=?',(stamp,sid))
        for t in store.rows('SELECT id,state FROM tournaments'):
            state=t['state']
            if state=='running':state='active' if t['id'] in active else 'waiting'
            elif t['id'] in active and state!='draining':state='finishing active games'
            last=store.one('SELECT * FROM activity_spans WHERE session=? AND tid=? ORDER BY started DESC LIMIT 1',(sid,t['id']))
            if last and stamp>=last['last_seen']:
                store.db.execute('UPDATE activity_spans SET last_seen=? WHERE session=? AND tid=? AND started=?',(stamp,sid,t['id'],last['started']))
            if not last or last['state']!=state:
                store.db.execute('INSERT OR REPLACE INTO activity_spans VALUES(?,?,?,?,?)',(sid,t['id'],state,stamp,stamp))


def close(store):
    # Final observed instant; never bridge an unobserved long gap at shutdown.
    row=store.one('SELECT last_seen FROM activity_sessions WHERE id=?',(store.activity_id,))
    if not row:return
    stamp=time.time()
    with store.tx():
        end=stamp if 0<=stamp-row['last_seen']<=60 else row['last_seen']
        store.db.execute('UPDATE activity_spans SET last_seen=? WHERE session=? AND last_seen=?',(end,store.activity_id,row['last_seen']))
        store.db.execute("UPDATE activity_sessions SET last_seen=?,ended=?,outcome='closed normally' WHERE id=?",(end,end,store.activity_id))


def report(store,tid='',offset=0):
    offset=int(offset)
    if offset<0:raise ValueError('Invalid activity page')
    if tid:store.tournament(tid)
    if tid:
        rows=store.rows('SELECT a.*,s.outcome FROM activity_spans a JOIN activity_sessions s ON s.id=a.session WHERE tid=? ORDER BY a.started DESC LIMIT 50 OFFSET ?',(tid,offset))
        totals=store.rows('SELECT state,sum(max(0,last_seen-started)) seconds FROM activity_spans WHERE tid=? GROUP BY state',(tid,))
        count=store.one('SELECT count(*) n FROM activity_spans WHERE tid=?',(tid,))['n']
    else:
        rows=store.rows("SELECT id session,started,last_seen,ended,outcome,'worker online' state FROM activity_sessions ORDER BY started DESC LIMIT 50 OFFSET ?",(offset,))
        totals=store.rows("SELECT 'worker online' state,coalesce(sum(max(0,last_seen-started)),0) seconds FROM activity_sessions")
        count=store.one('SELECT count(*) n FROM activity_sessions')['n']
    bounds=store.one('SELECT min(started) first,max(last_seen) last,sum(max(0,last_seen-started)) online,count(*) sessions FROM activity_sessions')
    unknown=max(0,(bounds['last'] or 0)-(bounds['first'] or 0)-(bounds['online'] or 0))
    return {'items':rows,'totals':totals,'total':count,'offset':offset,'sessions':bounds['sessions'],
      'unobserved_seconds':unknown,'since':bounds['first'],
      'note':'Observed time since activity tracking began. State changes are sampled every 10 seconds. Offline time, sleep, clock changes and observation gaps are unobserved, not uninterrupted uptime. Older run sessions remain in tournament reports.'}
