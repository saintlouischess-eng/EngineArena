"""Append-only round-robin expansions. Matchups remain implicit, even for large fields."""
import hashlib
import json
from contextlib import nullcontext


def reason(t):
    if t.get('event'):return 'Event stages cannot be extended. Change the next season roster instead.'
    if t['settings']['format']!='round_robin':return 'Only standalone round-robin tournaments can be extended.'
    if t['state'] not in ('completed','paused') or t['dependency']:return 'Pause and drain the tournament before changing its roster.'
    return ''


def info(store,tid):
    t=store.tournament(tid)
    return {'reason':reason(t),'participants':t['active_participants'],'total':t['total'],'keep_played':t['state']=='paused',
            'retained_withdrawals':len(t['settings'].get('rr_withdrawn_retained',[])),
            'active':[{'slot':r['slot'],'name':json.loads(r['profile'])['name']} for r in store.rows('SELECT slot,profile FROM participants WHERE tid=? ORDER BY slot',(tid,)) if r['slot'] in t['settings'].get('rr_active_slots',range(t['participants']))],
            'can_withdraw':not reason(t),
            'existing_ids':[json.loads(r['profile']).get('id') for r in store.rows('SELECT profile FROM participants WHERE tid=?',(tid,))]}


def checked(store,tid,profiles,scheduling='catch_up'):
    from .store import encode
    t=store.tournament(tid);error=reason(t)
    if error:raise ValueError(error)
    if scheduling not in ('catch_up','balanced','after_existing'):raise ValueError('Unknown newcomer scheduling choice')
    if store.one("SELECT 1 FROM games WHERE tid=? AND state='running' LIMIT 1",(tid,)):raise ValueError('Wait for all active games to finish draining')
    if not profiles:raise ValueError('Select at least one new engine profile.')
    ids=[p.get('id') for p in profiles]
    if any(not v for v in ids) or len(set(ids))!=len(ids):raise ValueError('Select different registered engine profiles.')
    existing=info(store,tid)['existing_ids']
    if set(ids).intersection(existing):raise ValueError('An engine profile is already in this tournament.')
    counts=store.one('SELECT coalesce(sum(official IS NOT NULL),0) official FROM games WHERE tid=? AND invalid=0',(tid,))
    if t['state']=='completed' and counts['official']!=t['total']:
        raise ValueError('Every scheduled game needs a completed official result before extension.')
    from .move_books import validate
    from .models import TimeControl
    profiles=[dict(p,move_book=validate(store,p.get('move_book'))) for p in profiles]
    for p in profiles:
        if p.get('time_control'):TimeControl.parse(p['time_control'])
    n=t['active_participants'];m=len(profiles);s=t['settings'];legs=2 if s['paired'] else 1
    extra=(n*m+m*(m-1)//2)*s['cycles']*legs
    if t['total']+extra>9223372036854775807:raise ValueError('Schedule exceeds SQLite 64-bit game numbering capacity')
    rev=store.one('SELECT revision FROM report_revisions WHERE tid=?',(tid,))
    token=hashlib.sha256(encode([tid,t['setup_revision'],rev,t['total'],t['state'],profiles,scheduling]).encode()).hexdigest()
    return t,profiles,{'expected':token,'old_participants':n,'new_participants':n+m,
        'retained_games':counts['official'],'existing_schedule':t['total'],'scheduling':scheduling,'additional_games':extra,'total_games':t['total']+extra,
        'cycles':s['cycles'],'paired':s['paired'],'opening_policy':s.get('opening_policy','legacy'),
        'opening_order':s['opening_order'],'names':[p['name'] for p in profiles]}


def preview(store,tid,profiles,scheduling='catch_up'):return checked(store,tid,profiles,scheduling)[2]


def extend(store,tid,profiles,expected,scheduling='catch_up',*,in_transaction=False):
    from .store import encode,now
    with nullcontext() if in_transaction else store.tx():
        t,profiles,p=checked(store,tid,profiles,scheduling)
        if not expected or expected!=p['expected']:raise ValueError('The tournament or engine selection changed. Preview the extension again.')
        s=t['settings'];n=t.get('slot_count',t['participants']);legs=2 if s['paired'] else 1
        rounds=store.one('SELECT coalesce(max(round),-1)+1 n FROM games WHERE tid=?',(tid,))['n']
        if s.get('opening_policy')=='round':
            # Reserve the entire implicit schedule, not just materialized games.
            # An early addition must not share opening-round assignments with
            # old rounds that the incremental scheduler has yet to create.
            initial=s['rr_extensions'][0]['old'] if s.get('rr_extensions') else n
            rounds=max(rounds,(initial+initial%2-1)*s['cycles'])
            for prior in s.get('rr_extensions',[]):
                old=len(prior.get('old_slots',range(prior['old'])));added=prior['added']
                span=max(old,added)+(added+added%2-1 if added>1 else 0)
                rounds=max(rounds,prior['round_start']+s['cycles']*span)
        from .rr_roster import archive
        archive(store,tid)
        old_slots=s.get('rr_active_slots',list(range(n)))
        start=s.get('rr_schedule_total',t['total'])//legs
        segment={'start':start,'end':start+p['additional_games']//legs,'old':n,'old_slots':old_slots,'new_start':n,'added':len(profiles),'round_start':rounds,'created':now()}
        s['rr_active_slots']=[*old_slots,*range(n,n+len(profiles))]
        s['rr_schedule_total']=segment['end']*legs
        s['rr_admission']={'start':start,'end':segment['end'],'old_slots':old_slots,'new_slots':list(range(n,n+len(profiles))),'mode':scheduling}

        s['rr_extensions']=[*s.get('rr_extensions',[]),segment]
        for i,profile in enumerate(profiles,n):
            store.db.execute('INSERT INTO participants VALUES(?,?,?)',(tid,i,encode(profile)))
            store.db.execute('INSERT INTO rankings(tid,slot,seed) VALUES(?,?,?)',(tid,i,i))
            store.db.execute('INSERT INTO aggregates(tid,a,b) VALUES(?,?,-1)',(tid,i))
        store.db.execute("UPDATE tournaments SET settings=?,total=?,cursor=?,state='paused',note='',started_once=1,setup_revision=setup_revision+1 WHERE id=?",
                         (encode(s),p['total_games'],t['cursor'],tid))
        # Extension is always a deliberate paused setup, including in an active queue.
        store.db.execute('UPDATE tournament_queue SET finished=0,held=1 WHERE tid=?',(tid,))
        store.db.execute('INSERT INTO report_revisions VALUES(?,1) ON CONFLICT(tid) DO UPDATE SET revision=revision+1',(tid,))
        store.audit(tid,'round_robin_extended',p|{'segment':segment,'profile_ids':[v['id'] for v in profiles]})
    return store.tournament(tid)


def segment(index,s):
    return next((v for v in reversed(s.get('rr_extensions',[])) if v['start']<=index<v['end']),None)


def canonical(index,n,s):
    """Each expansion owns its own permutation; older game identities never change."""
    from .schedule_order import shuffled
    v=segment(index,s)
    if v is None:
        from .schedule_order import canonical as original
        return original(index,s['rr_extensions'][0]['old'],{k:x for k,x in s.items() if k!='rr_extensions'})
    count=v['end']-v['start'];local=index-v['start'];cycles=s['cycles']
    order=s.get('schedule_order','legacy')
    if order=='shuffle':local=shuffled(local,count,s.get('schedule_seed',7970),'extension:'+str(v['start']))
    elif order=='matchup' or order=='legacy' and s.get('opening_policy')!='round':
        match,cycle=divmod(local,cycles);local=cycle*(count//cycles)+match
    return v['start']+local


def pair(index,n,s):
    from .opening_policy import round_pair
    v=segment(index,s)
    if v is None:
        from .custom_matchups import pair as original
        return original(index,s['rr_extensions'][0]['old'],{k:x for k,x in s.items() if k!='rr_extensions'})
    old_slots=v.get('old_slots',list(range(v['old'])));old,added=len(old_slots),v['added'];cross=old*added;per=cross+added*(added-1)//2
    cycle,within=divmod(index-v['start'],per)
    cross_rounds=max(old,added);new_rounds=added+(added%2)-1 if added>1 else 0
    if within<cross:
        # Circle-style bipartite rounds give new and incumbent engines turns.
        a,b,r=round_pair(within,old+added,'gauntlet',1,old)
    else:
        a,b,r=round_pair(within-cross,added,'round_robin',1);a+=old;b+=old;r+=cross_rounds
    slots=[*old_slots,*range(v.get('new_start',v['old']),v.get('new_start',v['old'])+added)]
    a,b=slots[a],slots[b]
    round_no=v['round_start']+cycle*(cross_rounds+new_rounds)+r if s.get('opening_policy')=='round' else cycle
    if not s['paired'] and (within+cycle)%2:a,b=b,a
    return a,b,round_no
