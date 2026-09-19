"""Freeze the first sequential stopping observation in the result transaction.

Paired tests admit a sample only after both final attempts have completed,
including prescribed automatic retries. Post-stop completions remain official
but cannot move the recorded stopping boundary. Manual replacement invalidates
inference; descriptive standings continue to follow current official results.
"""
import json
import time
from .stats import sprt_llr

def initialize(store):
    store.db.executescript('''
    CREATE TABLE IF NOT EXISTS sequential_state(tid TEXT PRIMARY KEY,body TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS sequential_samples(tid TEXT,sample INTEGER,body TEXT NOT NULL,PRIMARY KEY(tid,sample));
    ''')

def get(store,tid):
    row=store.one('SELECT body FROM sequential_state WHERE tid=?',(tid,))
    return json.loads(row['body']) if row else None

def invalidate(store,tid):
    previous=get(store,tid)
    value={'decision':'invalidated','reason':'Official results were selected for manual replacement. Descriptive ratings update; start a new test for a valid sequential decision.','previous':previous}
    store.db.execute('INSERT OR REPLACE INTO sequential_state VALUES(?,?)',(tid,json.dumps(value)))
    store.audit(tid,'sprt_inference_invalidated',value)

def observe(store,t,g):
    if t['settings']['format']!='sprt':return
    state=get(store,t['id'])
    if state and state['decision']!='continue':return
    paired=t['settings']['paired'];sample=g['pair_no'] if paired else g['number']
    if store.one('SELECT sample FROM sequential_samples WHERE tid=? AND sample=?',(t['id'],sample)):return
    rows=store.rows('SELECT g.*,a.result FROM games g JOIN attempts a ON a.id=g.official WHERE g.tid=? AND '+('g.pair_no=?' if paired else 'g.number=?')+' AND invalid=0 ORDER BY leg',(t['id'],sample))
    if len(rows)!=(2 if paired else 1) or any(r['state']!='completed' or r['result'] not in ('1-0','0-1','1/2-1/2') for r in rows):return
    score=sum(({'1-0':1,'0-1':0,'1/2-1/2':.5}[r['result']] if r['white']==0 else 1-{'1-0':1,'0-1':0,'1/2-1/2':.5}[r['result']]) for r in rows)
    bins=list(state['bins']) if state else [0]*(5 if paired else 3);bins[round(2*score)]+=1
    evidence={'sample':sample,'attempts':[r['official'] for r in rows],'score':score,'completed':time.time()}
    store.db.execute('INSERT INTO sequential_samples VALUES(?,?,?)',(t['id'],sample,json.dumps(evidence)))
    value=sprt_llr(bins,**t['settings']['sprt'])|{'bins':bins,'samples':sum(bins),'paired':paired,'observation':evidence,'frozen':False}
    if value['decision'] in ('H0','H1'):
        value['frozen']=True;store.audit(t['id'],'sprt_stopped',value)
        store.db.execute("UPDATE tournaments SET state='draining',note=? WHERE id=?",(f"SPRT stopped at {value['samples']} {'pairs' if paired else 'games'}: {value['decision']}. Running games drain; the stopping evidence is frozen.",t['id']))
    store.db.execute('INSERT OR REPLACE INTO sequential_state VALUES(?,?)',(t['id'],json.dumps(value)))
