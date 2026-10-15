"""Append-only round-robin expansions. Matchups remain implicit, even for large fields."""
import hashlib
import json


def reason(t):
    if t.get('event'):return 'Event stages cannot be extended. Change the next season roster instead.'
    if t['settings']['format']!='round_robin':return 'Only standalone round-robin tournaments can be extended.'
    if t['state']!='completed' or t['dependency']:return 'Finish the tournament and all replays before extending it.'
    return ''


def info(store,tid):
    t=store.tournament(tid)
    return {'reason':reason(t),'participants':t['participants'],'total':t['total'],
            'existing_ids':[json.loads(r['profile']).get('id') for r in store.rows('SELECT profile FROM participants WHERE tid=?',(tid,))]}


def checked(store,tid,profiles):
    from .store import encode
    t=store.tournament(tid);error=reason(t)
    if error:raise ValueError(error)
    if not profiles:raise ValueError('Select at least one new engine profile.')
    ids=[p.get('id') for p in profiles]
    if any(not v for v in ids) or len(set(ids))!=len(ids):raise ValueError('Select different registered engine profiles.')
    existing=info(store,tid)['existing_ids']
    if set(ids).intersection(existing):raise ValueError('An engine profile is already in this tournament.')
    counts=store.one('SELECT count(*) n,sum(official IS NOT NULL) official FROM games WHERE tid=?',(tid,))
    # Diagnostic replays are fine once finished; only their official result counts.
    unfinished=store.one("SELECT 1 FROM games WHERE tid=? AND (state<>'completed' OR invalid<>0 OR official IS NULL) LIMIT 1",(tid,))
    if unfinished or counts['n']!=t['total'] or counts['official']!=t['total']:
        raise ValueError('Every scheduled game needs a completed official result before extension.')
    from .move_books import validate
    from .models import TimeControl
    profiles=[dict(p,move_book=validate(store,p.get('move_book'))) for p in profiles]
    for p in profiles:
        if p.get('time_control'):TimeControl.parse(p['time_control'])
    n=t['participants'];m=len(profiles);s=t['settings'];legs=2 if s['paired'] else 1
    extra=(n*m+m*(m-1)//2)*s['cycles']*legs
    if t['total']+extra>9223372036854775807:raise ValueError('Schedule exceeds SQLite 64-bit game numbering capacity')
    rev=store.one('SELECT revision FROM report_revisions WHERE tid=?',(tid,))
    token=hashlib.sha256(encode([tid,t['setup_revision'],rev,t['total'],profiles]).encode()).hexdigest()
    return t,profiles,{'expected':token,'old_participants':n,'new_participants':n+m,
        'retained_games':t['total'],'additional_games':extra,'total_games':t['total']+extra,
        'cycles':s['cycles'],'paired':s['paired'],'opening_policy':s.get('opening_policy','legacy'),
        'opening_order':s['opening_order'],'names':[p['name'] for p in profiles]}


def preview(store,tid,profiles):return checked(store,tid,profiles)[2]


def extend(store,tid,profiles,expected):
    from .store import encode,now
    with store.tx():
        t,profiles,p=checked(store,tid,profiles)
        if not expected or expected!=p['expected']:raise ValueError('The tournament or engine selection changed. Preview the extension again.')
        s=t['settings'];n=t['participants'];legs=2 if s['paired'] else 1
        rounds=store.one('SELECT coalesce(max(round),-1)+1 n FROM games WHERE tid=?',(tid,))['n']
        segment={'start':t['total']//legs,'end':p['total_games']//legs,'old':n,'added':len(profiles),'round_start':rounds,'created':now()}
        s['rr_extensions']=[*s.get('rr_extensions',[]),segment]
        for i,profile in enumerate(profiles,n):
            store.db.execute('INSERT INTO participants VALUES(?,?,?)',(tid,i,encode(profile)))
            store.db.execute('INSERT INTO rankings(tid,slot,seed) VALUES(?,?,?)',(tid,i,i))
            store.db.execute('INSERT INTO aggregates(tid,a,b) VALUES(?,?,-1)',(tid,i))
        store.db.execute("UPDATE tournaments SET settings=?,total=?,cursor=?,state='paused',note='',setup_revision=setup_revision+1 WHERE id=?",
                         (encode(s),p['total_games'],segment['start'],tid))
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
    old,added=v['old'],v['added'];cross=old*added;per=cross+added*(added-1)//2
    cycle,within=divmod(index-v['start'],per)
    cross_rounds=max(old,added);new_rounds=added+(added%2)-1 if added>1 else 0
    if within<cross:
        # Circle-style bipartite rounds give new and incumbent engines turns.
        a,b,r=round_pair(within,old+added,'gauntlet',1,old)
    else:
        a,b,r=round_pair(within-cross,added,'round_robin',1);a+=old;b+=old;r+=cross_rounds
    round_no=v['round_start']+cycle*(cross_rounds+new_rounds)+r if s.get('opening_policy')=='round' else cycle
    if not s['paired'] and (within+cycle)%2:a,b=b,a
    return a,b,round_no
