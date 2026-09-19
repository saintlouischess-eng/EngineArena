"""Incremental tournament points and configurable tiebreaks.

Byes contribute tournament points but never rated games. Buchholz is the sum
of opponent tournament points per played game; Sonneborn-Berger weights those
points by the score earned in that game. Both are updated algebraically when
an official result changes, including reversals and dependent-round removal.
"""
import json
import random

TIEBREAKS={'wins':'wins','black_wins':'black_wins','buchholz':'buchholz','sonneborn_berger':'sb','seed':'seed'}

def initialize(store):
    store.db.executescript('''
    CREATE TABLE IF NOT EXISTS rankings(tid TEXT,slot INTEGER,seed INTEGER,score REAL DEFAULT 0,
      bye_points REAL DEFAULT 0,wins INTEGER DEFAULT 0,black_wins INTEGER DEFAULT 0,
      buchholz REAL DEFAULT 0,sb REAL DEFAULT 0,PRIMARY KEY(tid,slot));
    CREATE INDEX IF NOT EXISTS ranking_points ON rankings(tid,(score+bye_points) DESC,seed);
    CREATE TABLE IF NOT EXISTS ranking_meta(tid TEXT PRIMARY KEY,extended INTEGER NOT NULL);
    CREATE INDEX IF NOT EXISTS aggregates_opponent ON aggregates(tid,b,a);
    ''')
    for t in store.rows('SELECT id,settings FROM tournaments WHERE id NOT IN (SELECT tid FROM ranking_meta)'):
        with store.tx():
            settings=json.loads(t['settings']);create(store,t['id'],settings)
            if settings['format']=='self_play':
                store.db.execute('UPDATE aggregates SET w=0,d=0,l=0,p0=0,p1=0,p2=0,p3=0,p4=0 WHERE tid=?',(t['id'],))
                for g in store.rows('SELECT g.*,a.result FROM games g JOIN attempts a ON a.id=g.official WHERE g.tid=? AND g.invalid=0',(t['id'],)):store._result_delta(g,g['result'],1)
                for g in store.rows('SELECT DISTINCT pair_no FROM games WHERE tid=? AND invalid=0',(t['id'],)):store._pair_delta(t['id'],g['pair_no'],1)
                continue
            store.db.execute('''UPDATE rankings SET score=coalesce((SELECT w+d*.5 FROM aggregates WHERE tid=rankings.tid AND a=rankings.slot AND b=-1),0),
              wins=coalesce((SELECT w FROM aggregates WHERE tid=rankings.tid AND a=rankings.slot AND b=-1),0),
              black_wins=(SELECT count(*) FROM games g JOIN attempts a ON g.official=a.id WHERE g.tid=rankings.tid AND g.black=rankings.slot AND g.invalid=0 AND a.result='0-1') WHERE tid=?''',(t['id'],))
            if settings['format']=='swiss':
                for row in store.rows('SELECT body FROM round_state WHERE tid=?',(t['id'],)):
                    state=json.loads(row['body'])
                    for slot,points in bye_awards(state,settings):store.db.execute('UPDATE rankings SET bye_points=bye_points+? WHERE tid=? AND slot=?',(points,t['id'],slot))
            rebuild_extended(store,t['id'])

def create(store,tid,settings):
    slots=[r['slot'] for r in store.rows('SELECT slot FROM participants WHERE tid=? ORDER BY slot',(tid,))]
    if settings.get('seeding')=='random':random.Random(settings['seed']).shuffle(slots)
    store.db.executemany('INSERT INTO rankings(tid,slot,seed) VALUES(?,?,?)',((tid,slot,i) for i,slot in enumerate(slots)))
    extended=any(v in ('buchholz','sonneborn_berger') for v in [*settings.get('tiebreaks',[]),settings.get('knockout_tiebreak')])
    store.db.execute('INSERT INTO ranking_meta VALUES(?,?)',(tid,int(extended)))

def rebuild_extended(store,tid):
    store.db.execute('''UPDATE rankings SET
      buchholz=coalesce((SELECT sum((a.w+a.d+a.l)*(o.score+o.bye_points)) FROM aggregates a JOIN rankings o ON o.tid=a.tid AND o.slot=a.b WHERE a.tid=rankings.tid AND a.a=rankings.slot AND a.b>=0 AND a.a<>a.b),0),
      sb=coalesce((SELECT sum((a.w+a.d*.5)*(o.score+o.bye_points)) FROM aggregates a JOIN rankings o ON o.tid=a.tid AND o.slot=a.b WHERE a.tid=rankings.tid AND a.a=rankings.slot AND a.b>=0 AND a.a<>a.b),0) WHERE tid=?''',(tid,))

def point_delta(store,tid,slot,delta,column='score'):
    assert column in ('score','bye_points')
    extended=store.one('SELECT extended FROM ranking_meta WHERE tid=?',(tid,))
    if extended and extended['extended'] and delta:
        store.db.execute('''UPDATE rankings SET
          buchholz=buchholz+?*coalesce((SELECT w+d+l FROM aggregates WHERE tid=? AND a=rankings.slot AND b=?),0),
          sb=sb+?*coalesce((SELECT w+d*.5 FROM aggregates WHERE tid=? AND a=rankings.slot AND b=?),0)
          WHERE tid=? AND slot<>? AND slot IN (SELECT a FROM aggregates WHERE tid=? AND b=?)''',(delta,tid,slot,delta,tid,slot,tid,slot,tid,slot))
    store.db.execute(f'UPDATE rankings SET {column}={column}+? WHERE tid=? AND slot=?',(delta,tid,slot))

def result_delta(store,g,result,delta):
    tid=g['tid'];a=g['white'];b=g['black'];white={'1-0':1,'0-1':0,'1/2-1/2':.5}[result]
    # Called before the old aggregates are changed; apply point changes first,
    # then the edge contribution using the new opponent points.
    point_delta(store,tid,a,delta*white)
    if a!=b:point_delta(store,tid,b,delta*(1-white))
    store.db.execute('UPDATE rankings SET wins=wins+?,black_wins=black_wins+? WHERE tid=? AND slot=?',(delta*int(white==1),delta*int(a==b and white==0),tid,a))
    if a!=b:store.db.execute('UPDATE rankings SET wins=wins+?,black_wins=black_wins+? WHERE tid=? AND slot=?',(delta*int(white==0),delta*int(white==0),tid,b))
    meta=store.one('SELECT extended FROM ranking_meta WHERE tid=?',(tid,))
    if meta and meta['extended'] and a!=b:
        for x,y,score in ((a,b,white),(b,a,1-white)):
            points=store.one('SELECT score+bye_points p FROM rankings WHERE tid=? AND slot=?',(tid,y))['p']
            store.db.execute('UPDATE rankings SET buchholz=buchholz+?,sb=sb+? WHERE tid=? AND slot=?',(delta*points,delta*score*points,tid,x))

def bye_awards(state,settings):
    if settings['format']!='swiss':return []
    return state.get('bye_awards',[(slot,settings['cycles']*(2 if settings['paired'] else 1)*settings.get('bye_score',1)) for slot in state.get('byes',[])])

def reverse_round_byes(store,tid,first_round,settings):
    for row in store.rows('SELECT body FROM round_state WHERE tid=? AND round>?',(tid,first_round)):
        for slot,points in bye_awards(json.loads(row['body']),settings):point_delta(store,tid,slot,-points,'bye_points')

def order_sql(settings,alias='r'):
    terms=[f'({alias}.score+{alias}.bye_points) DESC']
    for key in settings.get('tiebreaks',['wins','seed']):
        column=TIEBREAKS[key];terms.append(f'{alias}.{column} '+('ASC' if key=='seed' else 'DESC'))
    terms.append(f'{alias}.seed ASC');return ','.join(terms)

def rows(store,tid,settings,offset=0,limit=-1):
    if settings['format']=='ladder':
        saved=store.one('SELECT body FROM round_state WHERE tid=? ORDER BY round DESC LIMIT 1',(tid,))
        if saved:
            state=json.loads(saved['body']);order=state.get('final_ladder_order',state.get('ladder_order',[]))
            if order:
                selected=order[offset:] if limit<0 else order[offset:offset+limit]
                return [store.one('SELECT r.*,r.score+r.bye_points points,? ladder_position FROM rankings r WHERE tid=? AND slot=?',(i+offset+1,tid,a)) for i,a in enumerate(selected)]
    return store.rows('SELECT r.*,r.score+r.bye_points points FROM rankings r WHERE tid=? ORDER BY '+order_sql(settings)+' LIMIT ? OFFSET ?',(tid,limit,offset))
