"""Resource admission with bounded lookahead over the implicit static schedule.

Skipped pairs remain implicit; only a chosen pair is materialized, with both
colors and its original number/opening. The ordinary cursor later catches up.
Scan cursors are disposable: recovery needs only existing games and settings.
"""
from functools import lru_cache

from .models import static_pair,scheduled_pairs
from .opening_policy import round_pair
from .resources import fits,game_cost
from .schedule_order import canonical

DYNAMIC={'swiss','knockout','double_elimination','ladder'}


def no_more_capacity(new,old):
    """Previously rejected costs remain rejected if available resources shrink."""
    return (new['threads']>=old['threads'] and new['memory_mb']>=old['memory_mb']
            and all(new['gpu'].get(group,0)>=count for group,count in old['gpu'].items()))


def dispatch(store,tid,used,admission,scan=None,limit=256,dry_run=False):
    t=store.tournament(tid);s=t['settings'];legs=2 if s['paired'] else 1
    empty={'game':None,'scan':None,'exhausted':True,'reason':''}
    if t['state']!='running' or t['dependency']:return empty
    from .sequential import frozen
    diagnostic_only=s['format']=='sprt' and frozen(store,tid)
    previous=scan
    signature=(used,admission,t['round'],t.get('setup_revision',0))
    compatible=scan and scan['signature'][1:]==signature[1:]
    if not compatible or not no_more_capacity(used,scan['signature'][0]):
        scan={'signature':signature,'pending_after':(-2,-1),'phase':'pending','future':t['cursor'],'reason':''}
    else:
        scan=dict(scan)
        if scan['signature']!=signature:scan.update(pending_after=(-2,-1),phase='pending',signature=signature)
        scan['future']=max(scan['future'],t['cursor'])

    @lru_cache(maxsize=256)
    def profile(slot):return store.participant(tid,slot)

    def eligible(a,b):
        if active_slots is not None and (a not in active_slots or b not in active_slots):return False
        cost=game_cost(profile(a),profile(b),s['ponder'])
        allowed,why=fits(cost,used,admission)
        if allowed and '_local_used' in admission:
            allowed,why=fits(cost,admission['_local_used'],admission['_local_limits'])
        if not allowed and not scan['reason']:scan['reason']=why
        return allowed

    active_slots=set(s['rr_active_slots']) if 'rr_active_slots' in s else None

    def rewind_pending(state):return dict(state,phase='pending',pending_after=(-2,-1))

    def claim(gid,from_pending=False):
        if dry_run:
            g=store.one('SELECT * FROM games WHERE id=?',(gid,))
            return empty|{'game':g,'white':profile(g['white']),'black':profile(g['black'])}
        g=store.claim(tid,gid)
        # A GPU finishing and immediately being replaced should not discard an
        # in-progress lookahead under the occupied-GPU budget. The next dispatch
        # revalidates its budget before reusing it. Always recheck pending games.
        resume=previous if from_pending and compatible else scan
        return empty|{'game':g,'scan':rewind_pending(resume),'white':profile(g['white']),'black':profile(g['black'])} if g else empty

    from .rr_priority import choose
    priority=choose(store,t,eligible,claim,limit,dry_run)
    if priority:return priority

    # Prefer the earliest eligible recorded game, including retries and replays.
    if scan['phase']=='pending':
        rows=store.rows("SELECT id,number,schedule_index,white,black FROM games WHERE tid=? AND state='pending' AND invalid=0 AND (schedule_index,number)>(?,?)"+(" AND mode='diagnostic'" if diagnostic_only else '')+" ORDER BY schedule_index,number LIMIT ?",(tid,*scan['pending_after'],limit))
        for g in rows:
            scan['pending_after']=(g['schedule_index'],g['number'])
            if eligible(g['white'],g['black']):return claim(g['id'],True)
        if len(rows)==limit:return empty|{'scan':scan,'exhausted':False}
        scan['phase']='future'

    # Dependent formats may only dispatch games from their committed round plan.
    if s['format'] in DYNAMIC or diagnostic_only:return empty|{'reason':scan['reason']}
    total=t['schedule_total']//legs;decoder=round_pair if s.get('opening_policy')=='round' else static_pair
    # With shared-round openings, matchups repeat every single schedule cycle.
    # If every pairing fails admission for a full cycle, later cycles cannot fit.
    period=scheduled_pairs(t['slot_count'],s['format'],1,s['candidates']) if s['format']!='custom' else None if s['format']!='custom' else None
    checked=0
    while scan['future']<total and checked<limit:
        from .custom_matchups import pair,decode
        position=scan['future'];k=canonical(position,t['slot_count'],s);a,b,rep=pair(k,t['slot_count'],s);checked+=1
        if not eligible(a,b):
            if s.get('rr_extensions'):
                scan['future']=position+1
                continue  # Segment permutations have different skip boundaries.
            legacy=s.get('schedule_order','legacy')=='legacy'
            scan['future']=position+1
            if s.get('schedule_order')=='matchup':
                scan['future']=decode(position,s)[3] if s['format']=='custom' else min(total,(position//s['cycles']+1)*s['cycles'])
            if s['format'] in ('match','sprt'):scan['future']=total
            if legacy and decoder is not round_pair:scan['future']=min(total,(k//s['cycles']+1)*s['cycles'])
            if legacy and s['format']=='custom':scan['future']=decode(k,s)[3]
            elif (legacy and decoder is round_pair) or (s.get('schedule_order')=='balanced' and s['format']!='custom'):
                scan['blocked_run']=scan.get('blocked_run',0)+1
                if scan['blocked_run']>=period:scan['future']=total
            continue
        scan['blocked_run']=0;scan['future']=position+1
        if store.one('SELECT id FROM games WHERE tid=? AND pair_no=? LIMIT 1',(tid,k)):continue
        if dry_run:return empty|{'game':{'planned_pair':k},'white':profile(a),'black':profile(b)}
        with store.tx():store._insert_pair(tid,k,a,b,rep,s,fixed_colors=s['format']=='custom' or bool(s.get('rr_extensions')),schedule_index=position)
        g=store.one('SELECT id FROM games WHERE tid=? AND pair_no=? ORDER BY leg LIMIT 1',(tid,k))
        return claim(g['id'])
    exhausted=scan['future']>=total
    return empty|{'scan':rewind_pending(scan) if exhausted else scan,'exhausted':exhausted,'reason':scan['reason']}
