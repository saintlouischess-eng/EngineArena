"""Reproducible opening assignment, independent of dispatch concurrency."""
import hashlib
import random
from .models import scheduled_pairs, static_pair

POLICIES={'legacy','pair','round','cycle','fixed'}


def prepare(settings,items):
    from .openings import unique_openings
    policy=settings.get('opening_policy','legacy')
    if policy not in POLICIES:raise ValueError('Unknown opening preset')
    if settings['opening_order'] not in ('sequential','random','shuffle'):raise ValueError('Unknown opening order')
    if policy!='legacy':items=unique_openings(items,settings['chess960'])
    if not isinstance(settings['seed'],int) or isinstance(settings['seed'],bool):raise ValueError('Opening seed must be a whole number')
    # Persist the permutation; recovery never depends on RNG state.
    if settings['opening_order']=='shuffle':
        items=list(items);random.Random(settings['seed']).shuffle(items)
    return items


def round_pair(index,n,fmt,cycles,candidates=1):
    """Constant-space rounds: each engine plays at most one matchup per round."""
    if fmt=='round_robin':
        size=n+(n%2);per_round=n//2;round_no,slot=divmod(index,per_round)
        r=round_no%(size-1);i=slot+int(n%2)
        def at(j):return size-1 if j==0 else (r+j-1)%(size-1)
        return at(i),at(size-1-i),round_no
    if fmt=='gauntlet':
        other=n-candidates;per_round=min(candidates,other);round_no,i=divmod(index,per_round)
        r=round_no%max(candidates,other)
        return (i,candidates+(i+r)%other,round_no) if candidates<=other else ((i+r)%candidates,candidates+i,round_no)
    if fmt=='self_play':
        round_no,i=divmod(index,n);return i,i,round_no
    return static_pair(index,n,fmt,cycles,candidates)


def select(settings,pair_no,round_no,cycle=0):
    policy=settings.get('opening_policy','legacy');items=settings['openings']
    if policy=='fixed':index=0
    elif policy=='round':index=round_no
    elif policy=='cycle':index=round_no*settings['cycles']+cycle if settings['format'] in ('swiss','ladder','knockout','double_elimination') else round_no
    else:index=pair_no
    k=index
    if settings['opening_order']=='random':k=int.from_bytes(hashlib.sha256(f"{settings['seed']}:{index}".encode()).digest()[:8],'big')
    return items[k%len(items)]|{'seed':settings['seed'],'selection':k%len(items),'assignment':index,'opening_policy':policy,'pool_pass':index//len(items)}


def capacity(unique,n,s):
    legs=2 if s['paired'] else 1;policy=s.get('opening_policy','pair');fmt=s['format'];cycles=s['cycles']
    pairs=scheduled_pairs(n,fmt,cycles,s['candidates'],s['rounds'],s.get('ladder_distance',1))
    required=pairs;games=unique*legs;unit='opening pairs' if s['paired'] else 'games';conditional=False
    note='A fresh position for each color-reversed pair.' if s['paired'] else 'A fresh position for each game.'
    if policy=='fixed':
        required=1;games=legs;unit='fixed position';note='The first selected position is deliberately reused for the whole tournament.'
    elif policy in ('round','cycle'):
        unit='rounds' if policy=='round' else 'shared cycles'
        if fmt in ('match','sprt'):required=cycles;games=unique*legs
        elif fmt=='self_play':required=cycles;games=unique*n*legs
        elif fmt in ('round_robin','gauntlet'):
            if policy=='cycle':per=pairs//cycles;required=cycles
            else:
                per=n//2 if fmt=='round_robin' else min(s['candidates'],n-s['candidates']);required=pairs//per
            games=unique*per*legs
        elif fmt=='swiss':
            per=(n//2)*(cycles if policy=='round' else 1);required=s['rounds']*(cycles if policy=='cycle' else 1);games=unique*per*legs
        elif fmt=='ladder':
            from .rounds import ladder_positions
            units=cycles if policy=='cycle' else 1;required=s['rounds']*units
            complete,rest=divmod(unique,units);period=s.get('ladder_distance',1)+1
            counts=[len(ladder_positions(n,r,s.get('ladder_distance',1))[0]) for r in range(min(complete+1,period))]
            full,tail=divmod(complete,period)
            games=(full*sum(counts)+sum(counts[:tail]))*cycles*legs
            if rest:games+=counts[complete%period]*rest*legs
        else:
            required=(n-1).bit_length() if fmt=='knockout' else 2*n-1
            if policy=='cycle':required*=cycles
            games=None;conditional=True
        note='All matchups in a round share one position.' if policy=='round' else 'All matchups share the same ordered opening suite, one position per cycle.'
    if fmt in ('knockout','double_elimination'):
        conditional=True
        if policy in ('pair','legacy'):
            required+=(cycles if fmt=='double_elimination' else 0)
            if s.get('knockout_tiebreak')=='playoff':required+=(n-1 if fmt=='knockout' else 2*n-1)*s['playoff_limit']*s['playoff_cycles']
        note+=' Finals, byes and playoffs depend on results; the requirement is an upper bound. Shared presets retain the round opening suite during playoffs.'
    random_repeats=s['opening_order']=='random'
    return {'unique_positions':unique,'paired_game_capacity':str(unique*2),'single_game_capacity':str(unique),
            'games_before_reuse':None if random_repeats else str(games) if games is not None else None,
            'required_positions':str(required),'pool_units':unit,'reuse_expected':required>unique or policy=='fixed' and pairs>1,
            'conditional':conditional,'random_repeats':random_repeats,'note':note,
            'exhaustion':'After all positions have been assigned, the recorded order repeats. Retries reuse their recorded opening and do not consume another position.'}
