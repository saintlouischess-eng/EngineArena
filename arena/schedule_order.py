"""Reproducible launch order, separate from game identities and opening choice.

The cursor indexes launch positions; game numbers/pairs retain their canonical
identities. No quadratic schedule or per-game shuffle list is allocated.
"""
from bisect import bisect_right
from functools import lru_cache
import hashlib

ORDERS=('legacy','balanced','matchup','shuffle')
LABELS={'legacy':'Recorded schedule order','balanced':'Balanced round order',
        'matchup':'Matchup order','shuffle':'Seeded shuffle'}


def initialize(store):
    if not any(r['name']=='schedule_index' for r in store.db.execute('PRAGMA table_info(games)')):
        with store.tx():
            store.db.execute('ALTER TABLE games ADD COLUMN schedule_index INTEGER NOT NULL DEFAULT -1')
    store.db.execute('CREATE INDEX IF NOT EXISTS games_schedule_queue ON games(tid,state,invalid,schedule_index,number)')


def validate(settings):
    if settings.get('schedule_order','legacy') not in ORDERS:raise ValueError('Unknown game scheduling order')
    seed=settings.get('schedule_seed',7970)
    if type(seed) is not int or not 0<=seed<=2147483647:raise ValueError('Scheduling seed must be a whole number from 0 to 2147483647')


@lru_cache(maxsize=64)
def keys(seed,scope):
    return tuple(hashlib.sha256(f'arena-schedule-v1:{seed}:{scope}:{r}'.encode()).digest() for r in range(6))


def shuffled(index,count,seed,scope='static'):
    """Cycle-walk a six-round Feistel permutation to an arbitrary finite range."""
    if count<=1:return index
    bits=((count-1).bit_length()+1)//2;mask=(1<<bits)-1
    value=index
    while True:
        left,right=value>>bits,value&mask
        for key in keys(seed,scope):
            mix=int.from_bytes(hashlib.blake2s(right.to_bytes(8,'little'),key=key,digest_size=8).digest(),'little')&mask
            left,right=right,left^mix
        value=(left<<bits)|right
        if value<count:return value


def rr_index(a,b,n):
    """Inverse of opening_policy.round_pair within one round-robin cycle."""
    size=n+n%2;m=size-1
    if m in (a,b):r=((b if a==m else a)+1)%m;slot=0
    else:
        r=((a+b+2)*((m+1)//2))%m
        j=(a-r)%m+1;slot=min(j,m-j)-n%2
    return r*(n//2)+slot


def round_index(a,b,n,fmt,candidates):
    if fmt=='round_robin':return rr_index(a,b,n)
    if fmt=='self_play':return a
    other=n-candidates;i=b-candidates
    return ((i-a)%other)*candidates+a if candidates<=other else ((a-i)%candidates)*other+i


@lru_cache(maxsize=8)
def layers(counts):
    """Compressed transpose of ragged matchup repetitions, O(matchups) space."""
    levels=sorted(set(counts));starts=[];total=0;previous=0;active=len(counts)
    from collections import Counter
    frequencies=Counter(counts)
    for level in levels:
        starts.append((total,previous,active));total+=(level-previous)*active
        active-=frequencies[level];previous=level
    ends=[];total=0
    for count in counts:total+=count;ends.append(total)
    return starts,[v[0] for v in starts],ends


def interleaved(index,counts):
    starts,offsets,ends=layers(tuple(counts));base,rep,width=starts[bisect_right(offsets,index)-1]
    layer,slot=divmod(index-base,width);rep+=layer
    for i,count in enumerate(counts):
        if count>rep:
            if slot==0:return (ends[i-1] if i else 0)+rep
            slot-=1
    raise ValueError('Schedule position outside matchup list')


def canonical(index,n,s):
    """Map a launch-pair position to the unchanged canonical opening/game pair."""
    if s.get('rr_extensions'):
        from .tournament_extend import canonical as expanded
        return expanded(index,n,s)
    from .models import scheduled_pairs,static_pair
    from .opening_policy import round_pair
    order=s.get('schedule_order','legacy');fmt=s['format'];cycles=s['cycles'];c=s['candidates']
    if order=='legacy':return index
    count=sum(v['count'] for v in s['custom_matchups']) if fmt=='custom' else scheduled_pairs(n,fmt,cycles,c)
    if order=='shuffle':return shuffled(index,count,s.get('schedule_seed',7970))
    if fmt=='custom':return interleaved(index,tuple(v['count'] for v in s['custom_matchups'])) if order=='balanced' else index
    if fmt in ('match','sprt'):return index
    per=scheduled_pairs(n,fmt,1,c)
    if order=='balanced':
        if s.get('opening_policy')=='round':return index
        cycle,within=divmod(index,per);a,b,_=round_pair(within,n,fmt,1,c)
        if fmt=='round_robin':
            a,b=sorted((a,b));match=a*(2*n-a-1)//2+b-a-1
        elif fmt=='gauntlet':match=a*(n-c)+b-c
        else:match=a
        return match*cycles+cycle
    if s.get('opening_policy')!='round':return index
    a,b,cycle=static_pair(index,n,fmt,cycles,c)
    return cycle*per+round_index(a,b,n,fmt,c)


def materialize_round(store,t,row,state,remaining):
    """Apply the chosen order within committed dynamic batches, never across rounds."""
    from .store import encode
    from .knockout import round_cycles
    s=t['settings'];legs=2 if s['paired'] else 1;changed=False
    available={c['start']:c for c in state['chunks']};work=0
    for batch in state['schedule_batches']:
        if batch['done']>=batch['count']:continue
        chunks=batch['chunks']
        counts=tuple(c['count'] for c in chunks);ends=layers(counts)[2]
        while batch['done']<batch['count'] and remaining>0 and work<256:
            index=batch['done'];order=s.get('schedule_order','legacy')
            local=interleaved(index,counts) if order=='balanced' else shuffled(index,batch['count'],s.get('schedule_seed',7970),str(batch['start'])) if order=='shuffle' else index
            ci=bisect_right(ends,local);c=available.get(chunks[ci]['start']);rep=local-(ends[ci-1] if ci else 0)
            batch['done']+=1;work+=1;changed=True
            # A result replacement may archive one matchup's later tiebreaks.
            # Keep this immutable permutation and skip the invalidated chunks.
            if c is None:continue
            a,b=c['a'],c['b']
            if legs==1 and (s.get('ko_round_games') or s.get('knockout_tiebreak')=='continuous') and (c.get('color_offset',0)+rep)%2:a,b=b,a
            store._insert_pair(t['id'],c['start']+rep,a,b,row['round'],s,fixed_colors=True,stage=c['phase'],
                cycle=rep%round_cycles(s,row['round']),playoff_stage=c.get('playoff_stage'),playoff_time_control=c.get('time_control'),
                opening_assignment=c['opening_start']+rep if c.get('opening_start') is not None else None,
                schedule_index=batch['start']+index)
            c['materialized']+=1;remaining-=legs
        if remaining<=0 or work>=256:break
    if changed:store.db.execute('UPDATE round_state SET body=? WHERE tid=? AND round=?',(encode(state),t['id'],row['round']))
    return remaining
