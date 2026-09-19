"""Identify and explicitly invalidate result-dependent rounds and playoffs."""
import json
from .rounds import match_key

def effects(store,tid,games):
    t=store.tournament(tid);first=min(g['round'] for g in games);states={r['round']:json.loads(r['body']) for r in store.rows('SELECT round,body FROM round_state WHERE tid=?',(tid,))};source={}
    for g in games:
        key=match_key(g['a'],g['b']);state=states.get(g['round'],{});stage=0
        for i,span in enumerate(state.get('playoffs',{}).get(key,[])):
            if span['start']<=g['pair_no']<span['end']:stage=i+1;break
        source[(g['round'],key)]=min(source.get((g['round'],key),stage),stage)
    playoffs=[]
    for (round_no,key),stage in source.items():
        spans=states.get(round_no,{}).get('playoffs',{}).get(key,[])
        if len(spans)>stage:playoffs.append({'round':round_no,'match':key,'keep':stage,'spans':spans[stage:]})
    return {'first_round':first,'later_rounds':sorted(r for r in states if r>first),'playoffs':playoffs,'source_matches':[(r,k) for r,k in source]}

def invalidate_playoffs(store,tid,effect):
    first=effect['first_round'];selected={(r,key) for r,key in effect['source_matches']};changes={e['round']:[] for e in effect['playoffs'] if e['round']<=first}
    for e in effect['playoffs']:
        if e['round']<=first:changes[e['round']].append(e)
    for r,key in selected:
        if r<=first:changes.setdefault(r,[])
    for round_no,items in changes.items():
        row=store.one('SELECT body FROM round_state WHERE tid=? AND round=?',(tid,round_no))
        if not row:continue
        state=json.loads(row['body']);original=json.loads(row['body']);changed=False
        if 'final_ladder_order' in state:state.pop('final_ladder_order');changed=True
        for item in items:
            spans=item['spans'];key=item['match']
            for span in spans:
                for g in store.rows('SELECT * FROM games WHERE tid=? AND invalid=0 AND pair_no>=? AND pair_no<?',(tid,span['start'],span['end'])):
                    if g['official']:store._set_official(g,None)
                    store.db.execute("UPDATE games SET invalid=1,state='invalidated' WHERE id=?",(g['id'],))
            state['chunks']=[c for c in state.get('chunks',[]) if not any(span['start']<=c['start']<span['end'] for span in spans)]
            state['playoffs'][key]=state['playoffs'][key][:item['keep']];changed=True
        for r,key in selected:
            if r==round_no and key in state.get('manual_winners',{}):state['manual_winners'].pop(key);changed=True
        if changed:
            store.db.execute('UPDATE round_state SET body=? WHERE tid=? AND round=?',(json.dumps(state,separators=(',',':')),tid,round_no));store.audit(tid,'playoff_dependencies_invalidated',{'round':round_no,'previous':original,'current':state})

def update_total(store,tid):
    from .models import scheduled_pairs
    t=store.tournament(tid);s=t['settings'];legs=2 if s['paired'] else 1
    base=scheduled_pairs(t['participants'],s['format'],s['cycles'],s['candidates'],s['rounds'],s.get('ladder_distance',1));regular=playoffs=0
    for row in store.rows('SELECT body FROM round_state WHERE tid=?',(tid,)):
        state=json.loads(row['body'])
        if 'chunks' not in state:regular+=len(state.get('matches',[]))*s['cycles']
        for c in state.get('chunks',[]):
            if c['phase']=='playoff':playoffs+=c['count']
            else:regular+=c['count']
    store.db.execute('UPDATE tournaments SET total=? WHERE id=?',((max(base,regular)+playoffs)*legs,tid))
