"""Promotion/relegation between adjacent divisions, with fixed division sizes."""
from .events import integer


def validate(d):
    groups=d['groups'];n=len(groups)
    if n<2:raise ValueError('A promotion/relegation league needs at least two divisions.')
    d['seasons']=integer(d.get('seasons',1),'Seasons')
    moves=d.get('movement',[1]*(n-1))
    if not isinstance(moves,list) or len(moves)!=n-1 or any(type(v) is not int or v<1 for v in moves):
        raise ValueError('Enter a positive promotion/relegation count for each adjacent division boundary.')
    for i,g in enumerate(groups):
        up=moves[i-1] if i else 0;down=moves[i] if i<n-1 else 0
        if up+down>len(g):raise ValueError('Promotion and relegation places overlap in a division. Reduce the movement counts.')
    names=d.get('division_names') or [f'Division {i+1}' for i in range(n)]
    if not isinstance(names,list) or len(names)!=n or any(not isinstance(v,str) or not v.strip() for v in names):
        raise ValueError('Enter one non-empty name per division, highest division first.')
    names=[v.strip() for v in names]
    if len(set(names))!=n:raise ValueError('Division names must be different.')
    d.update(division_names=names,movement=moves,initial_format='round_robin',final_format='round_robin',advance=1)
    d.pop('final_time_control',None)


def movement(d,tables,stage):
    n=len(tables);next_groups=[[] for _ in tables];changes=[]
    for i,table in enumerate(tables):
        up=d['movement'][i-1] if i else 0;down=d['movement'][i] if i<n-1 else 0
        for rank,r in enumerate(table):
            destination=i-1 if rank<up else i+1 if down and rank>=len(table)-down else i
            next_groups[destination].append(r['slot'])
            if destination!=i:changes.append({'slot':r['slot'],'name':r['name'],'from':i,'to':destination,'outcome':'Promoted' if destination<i else 'Relegated'})
    assert [len(g) for g in next_groups]==[len(g) for g in d['groups']]
    return {'stage':stage+1,'standings':tables,'qualified':[],'movement':changes,'next_groups':next_groups,
            'champion':tables[0][0]['name'],'policy':'Game points, configured standings tiebreaks, then recorded initial seed. Movements apply after every division finishes.'}


def extend(store,e):
    from .store import encode
    from .events import child,change
    d=e['body']['definition']
    if d['kind']!='league' or e['state']!='completed':raise ValueError('Finish the current league season before adding another.')
    decision=store.one('SELECT body FROM event_decisions WHERE eid=? AND stage=?',(e['id'],e['stage']))
    if not decision:raise ValueError('The completed season has no saved movement decision.')
    import json
    decision=json.loads(decision['body']);one_season=e['body']['regular_games']//d['seasons']
    d['seasons']+=1;e['body']['regular_games']+=one_season
    if e['body']['regular_games']>9223372036854775807:raise ValueError('Event exceeds 64-bit game numbering capacity.')
    with store.tx():
        for i,g in enumerate(decision['next_groups']):child(store,e,g,e['stage']+1,i)
        change(store,e['id'],stage=e['stage']+1,body=encode(e['body']),state='paused',note='Another season is prepared from the saved promotion and relegation places. Run event when ready.')
        store.audit(None,'league_extended',{'event':e['id'],'season':d['seasons']})
