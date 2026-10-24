"""Bounded newcomer admission, using the ordinary resource checks and claims."""
import json


def choose(store,t,eligible,claim,limit,dry_run=False):
    rule=t['settings'].get('rr_admission')
    if not rule or rule['mode']=='after_existing':return None
    tid=t['id'];s=t['settings'];legs=2 if s['paired'] else 1
    turns=getattr(store,'rr_turns',{})
    if rule['mode']=='balanced' and turns.get(tid):
        if not dry_run:turns[tid]=False
        return None
    if rule['mode']=='catch_up':
        def load(slots):
            if not slots:return 0
            completed=store.one('SELECT coalesce(sum(w+d+l),0) n FROM aggregates WHERE tid=? AND b=-1 AND a IN (SELECT value FROM json_each(?))',(tid,json.dumps(slots)))['n']
            underway=store.one("SELECT coalesce(sum((white IN (SELECT value FROM json_each(?)))+(black IN (SELECT value FROM json_each(?)))),0) n FROM games WHERE tid=? AND invalid=0 AND state='running'",(json.dumps(slots),json.dumps(slots),tid))['n']
            return (completed+underway)/len(slots)
        if load(rule['new_slots'])>=load(rule['old_slots']):return None
    def picked(gid):
        result=claim(gid,True)
        if result.get('game') and not dry_run:
            turns[tid]=True;store.rr_turns=turns
        return result
    pending=store.rows("SELECT id,white,black FROM games WHERE tid=? AND invalid=0 AND state='pending' AND pair_no>=? AND pair_no<? ORDER BY number LIMIT ?",(tid,rule['start'],rule['end'],limit))
    for g in pending:
        if eligible(g['white'],g['black']):return picked(g['id'])
    from .tournament_extend import pair,canonical
    cursors=getattr(store,'rr_priority_cursors',{});key=(tid,rule['start'])
    position=max(rule['start'],cursors.get(key,rule['start']))
    stop=min(rule['end'],position+limit)
    # Priority admissions always spread the newcomer matchups by pairing round.
    ordered=s|{'schedule_order':'balanced'}
    for pos in range(position,stop):
        if not dry_run:cursors[key]=pos+1;store.rr_priority_cursors=cursors
        k=canonical(pos,t['slot_count'],ordered);a,b,r=pair(k,t['slot_count'],s)
        if store.one('SELECT 1 FROM games WHERE tid=? AND pair_no=? LIMIT 1',(tid,k)):continue
        if not eligible(a,b):continue
        if dry_run:return {'game':{'planned_pair':k},'white':store.participant(tid,a),'black':store.participant(tid,b),'scan':None,'exhausted':False,'reason':''}
        with store.tx():store._insert_pair(tid,k,a,b,r,s,fixed_colors=True,schedule_index=pos)
        g=store.one('SELECT id FROM games WHERE tid=? AND pair_no=? ORDER BY leg LIMIT 1',(tid,k))
        return picked(g['id'])
    if not dry_run and stop>=rule['end']:cursors[key]=rule['start'];store.rr_priority_cursors=cursors
    return None
