"""Small transactional counters; polling never scans completed game history."""


def initialize(store):
    if store.one("SELECT name FROM sqlite_master WHERE type='table' AND name='game_counts'"):
        return
    # Table, backfill and triggers commit together, including on older databases.
    with store.tx():
        store.db.execute('''CREATE TABLE game_counts(tid TEXT,state TEXT,invalid INTEGER,
            has_official INTEGER,n INTEGER NOT NULL CHECK(n>=0),
            PRIMARY KEY(tid,state,invalid,has_official))''')
        store.db.execute('''INSERT INTO game_counts SELECT tid,state,invalid,official IS NOT NULL,count(*)
            FROM games GROUP BY tid,state,invalid,official IS NOT NULL''')
        store.db.execute('''CREATE TRIGGER game_counts_insert AFTER INSERT ON games BEGIN
            INSERT INTO game_counts VALUES(new.tid,new.state,new.invalid,new.official IS NOT NULL,1)
            ON CONFLICT(tid,state,invalid,has_official) DO UPDATE SET n=n+1;
            END''')
        store.db.execute('''CREATE TRIGGER game_counts_delete AFTER DELETE ON games BEGIN
            UPDATE game_counts SET n=n-1 WHERE tid=old.tid AND state=old.state AND invalid=old.invalid
                AND has_official=(old.official IS NOT NULL);
            END''')
        store.db.execute('''CREATE TRIGGER game_counts_update AFTER UPDATE OF tid,state,invalid,official ON games BEGIN
            UPDATE game_counts SET n=n-1 WHERE tid=old.tid AND state=old.state AND invalid=old.invalid
                AND has_official=(old.official IS NOT NULL);
            INSERT INTO game_counts VALUES(new.tid,new.state,new.invalid,new.official IS NOT NULL,1)
            ON CONFLICT(tid,state,invalid,has_official) DO UPDATE SET n=n+1;
            END''')


import json
from pathlib import Path
import sqlite3
from .models import FAILURES


def game_page(db,tid,reason='',offset=0,limit=100):
    if offset<0 or limit<1:raise ValueError('Invalid game-history page')
    def rows(sql,args):return [dict(r) for r in db.execute(sql,args)]
    def participant(tid,slot):return json.loads(db.execute('SELECT profile FROM participants WHERE tid=? AND slot=?',(tid,slot)).fetchone()[0])
    clause='g.tid=?';args=[tid]
    if reason=='interrupted':clause+=" AND EXISTS(SELECT 1 FROM attempts x WHERE x.gid=g.id AND x.reason='interrupted')"
    elif reason=='failed':clause+=' AND (a.reason IN ('+','.join('?' for _ in FAILURES)+") OR EXISTS(SELECT 1 FROM attempts x WHERE x.gid=g.id AND x.reason='interrupted'))";args.extend(FAILURES)
    elif reason:clause+=' AND (a.reason=? OR g.state=?)';args.extend([reason,reason])
    source='FROM games g LEFT JOIN attempts a ON g.official=a.id WHERE '+clause
    if reason:
        total=db.execute('SELECT count(*) '+source,args).fetchone()[0]
        items=rows('SELECT g.*,a.result,a.reason,(SELECT count(*) FROM attempts x WHERE x.gid=g.id) attempts '+source+' ORDER BY g.number LIMIT ? OFFSET ?',[*args,limit,offset])
    else:
        total=db.execute('SELECT coalesce(sum(n),0) FROM game_counts WHERE tid=?',(tid,)).fetchone()[0]
        items=rows('SELECT g.*,a.result,a.reason,(SELECT count(*) FROM attempts x WHERE x.gid=g.id) attempts FROM '
            '(SELECT * FROM games WHERE tid=? ORDER BY number LIMIT ? OFFSET ?) g LEFT JOIN attempts a ON a.id=g.official ORDER BY g.number',(tid,limit,offset))
    from .models import Clock,TimeControl
    tournament=db.execute('SELECT settings FROM tournaments WHERE id=?',(tid,)).fetchone()
    if not tournament:raise ValueError('Tournament no longer exists')
    settings=json.loads(tournament[0])
    for g in items:
        profiles={side:participant(tid,g[side]) for side in ('white','black')}
        g['white_name']=profiles['white']['name'];g['black_name']=profiles['black']['name']
        attempt=db.execute('SELECT clocks FROM attempts WHERE gid=? ORDER BY seq DESC LIMIT 1',(g['id'],)).fetchone()
        g['clocks']=json.loads(attempt[0]) if attempt and attempt[0] else {side:Clock(TimeControl.parse(p.get('time_control') or settings['time_control'])).snapshot() for side,p in profiles.items()}

    return {'total':total,'items':items}


def read_game_page(path,tid,reason='',offset=0,limit=100):
    db=sqlite3.connect(Path(path).as_uri()+'?mode=ro',uri=True,timeout=30);db.row_factory=sqlite3.Row
    try:
        db.execute('BEGIN')
        return game_page(db,tid,reason,offset,limit)
    finally:db.close()
