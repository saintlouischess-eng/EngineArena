"""Bounded season fields with an independently sized, durable candidate pool.

These policies are opt-in. Older events retain their original season rules.
Only compact roster/decision data is stored here; normal child tournaments own
all games, attempts, ratings and opening cursors.
"""
import copy


def enabled(d):
    return d.get('admission', {}).get('policy', 'off') != 'off'


def validate(d, count):
    a = d.setdefault('admission', {'policy': 'off'})
    if not isinstance(a, dict) or a.get('policy') not in ('off', 'full', 'challenge'):
        raise ValueError('Choose a season admission policy.')
    if not enabled(d):
        return
    field = sum(d['sizes'])
    if count < field:
        raise ValueError('The candidate pool must contain at least the season field size.')
    a.setdefault('places', min(8, field))
    if type(a['places']) is not int or not 1 <= a['places'] <= field:
        raise ValueError('Places at risk must be between one and the season field size.')
    # Admission is an actual played qualifier, including initial placement.
    d.setdefault('qualifier', {})['enabled'] = True


def pool(body):
    return body['season_state'].get('candidates', [s for g in body['season_state']['groups'] for s in g])


def plan(body, *, season=None):
    d = body['definition']; r = body['season_state']; candidates = pool(body)
    season = r['season'] if season is None else season
    full = season == 1 or d['admission']['policy'] == 'full'
    protected = [[] for _ in d['sizes']]
    if not full:
        # Groups are in earned seed order, highest division first. Withdrawals
        # create vacancies too; they never protect an extra incumbent.
        keep = sum(d['sizes']) - d['admission']['places']
        available = set(candidates)
        for i, group in enumerate(r['groups']):
            earned = group[:keep]
            protected[i] = [s for s in earned if s in available]
            keep -= len(earned)
    retained = {s for g in protected for s in g}
    vacancies = [size-len(g) for size,g in zip(d['sizes'], protected)]
    contestants = [s for s in candidates if s not in retained]
    return dict(policy='full' if full else 'challenge', field_size=sum(d['sizes']),
                candidates=len(candidates), protected=protected, vacancies=vacancies,
                places=sum(vacancies), contestants=contestants)


def begin(body):
    """Recompute only at a season boundary, before any qualification results."""
    r = body['season_state']
    r['admission_plan'] = plan(body)
    r['phase'] = 'qualification'
    r['bucket'] = len(r['groups'])-1 if body['definition']['mode']=='progressive' else 0


def cuts(body):
    p = body['season_state']['admission_plan']; total = 0; cuts = []
    for count in p['vacancies']:
        total += count
        if 0 < total < len(p['contestants']):
            cuts.append(total)
    return sorted(set(cuts))


def place(body, order, decision):
    r = body['season_state']; p = r['admission_plan']
    if len(order) != len(set(order)) or set(order) != set(p['contestants']):
        raise ValueError('Qualification results do not match the candidate pool.')
    groups = copy.deepcopy(p['protected']); offset = 0
    for i, count in enumerate(p['vacancies']):
        groups[i].extend(order[offset:offset+count]); offset += count
    if list(map(len, groups)) != body['definition']['sizes']:
        raise ValueError('Qualification did not fill the configured season field.')
    admitted = order[:offset]; missed = order[offset:]
    decision['admission'] = dict(policy=p['policy'], field_size=p['field_size'],
        protected=[s for g in p['protected'] for s in g], qualified=admitted,
        not_qualified=missed, candidates=p['candidates'],
        names={str(s):body['profiles'][s]['name'] for s in pool(body)})
    r['last_admission'] = dict(season=r['season'], **decision['admission'])
    r['groups'] = groups; r['next_groups'] = [[] for _ in groups]
    r['phase'] = 'division'; r['season_start'] = False
    decision['qualified'] = admitted; decision['placements'] = copy.deepcopy(groups)


def validate_pool(body, candidates):
    if (not isinstance(candidates, list) or
        any(type(s) is not int or not 0 <= s < len(body['profiles']) for s in candidates) or
        len(candidates) != len(set(candidates))):
        raise ValueError('Choose each candidate once using its participant number.')
    if len(candidates) < sum(body['definition']['sizes']):
        raise ValueError('The candidate pool must contain at least the season field size.')


def summary(body):
    r = body['season_state']; d = body['definition']; p = r.get('admission_plan', plan(body))
    count = len(p['contestants'])
    result = dict(policy=d['admission']['policy'], field_size=sum(d['sizes']),
        candidate_count=len(pool(body)), qualification_count=count,
        protected_count=sum(map(len,p['protected'])), places=p['places'],
        vacancies=p['vacancies'], places_at_risk=d['admission']['places'],
        progressive_fields=[n+(d['movement'][i] if d['mode']=='progressive' and i<len(d['sizes'])-1 else 0) for i,n in enumerate(d['sizes'])])
    if d['qualifier']['format']=='swiss':result['swiss_rounds']=min(d['qualifier']['rounds'],max(0,count-1))
    return result


def risk_cuts(d, bucket, count):
    """A tied safe/at-risk boundary must use the same recorded tie policy."""
    if not enabled(d) or d['admission']['policy']!='challenge':return []
    sizes=d['sizes'];movement=d['movement'];keep=sum(sizes)-d['admission']['places']
    safe=[max(0,min(size,keep-sum(sizes[:i]))) for i,size in enumerate(sizes)]
    up=movement[bucket-1] if bucket else 0
    down=movement[bucket] if bucket<len(sizes)-1 else 0
    cuts=[]
    if up<safe[bucket]<count-down:cuts.append(safe[bucket])
    if down and 0<safe[bucket+1]<down:cuts.append(count-down+safe[bucket+1])
    if d['mode']=='divisions' and up and sizes[bucket-1]-up<safe[bucket-1]<sizes[bucket-1]:
        cuts.append(safe[bucket-1]-sizes[bucket-1]+up)
    return cuts
