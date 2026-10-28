"""Small indexed reads for broadcast panels, no Store or game-history scans."""
from contextlib import closing
import json
from pathlib import Path
import sqlite3

def read(path, tid):
    with closing(sqlite3.connect(Path(path).as_uri()+'?mode=ro',uri=True,timeout=5)) as db:
        db.row_factory=sqlite3.Row;db.execute('PRAGMA query_only=ON');db.execute('BEGIN')
        t=db.execute('SELECT settings FROM tournaments WHERE id=?',(tid,)).fetchone()
        if not t:raise ValueError('Tournament not found')
        cfg=json.loads(t[0]);excluded=set(cfg.get('rr_withdrawn_excluded',[]))
        people={}
        for row in db.execute('SELECT slot,profile FROM participants WHERE tid=?',(tid,)):
            if row['slot'] in excluded:continue
            p=json.loads(row['profile']);people[row['slot']]={k:p.get(k) for k in ('id','name','threads')}
        upcoming=[]
        for row in db.execute("SELECT number,white,black FROM games WHERE tid=? AND state='pending' AND invalid=0 ORDER BY number LIMIT 20",(tid,)):
            if row['white'] in people and row['black'] in people:
                upcoming.append(dict(number=row['number']+1,white=people[row['white']]['name'],black=people[row['black']]['name']))
        return dict(people=[dict(slot=k,**v) for k,v in people.items()],upcoming=upcoming,
            conditions={k:cfg.get(k) for k in ('time_control','concurrency','cpu_budget','hash_mb','threads','paired','format','cycles')})
