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
    if d.get('execution_mode','sequential') not in ('sequential','parallel'):raise ValueError('Choose one at a time or run together.')
    if d.get('season_openings','reuse') not in ('reuse','advance'):raise ValueError('Choose how openings advance between seasons.')
    final=d.get('championship',{})
    if not isinstance(final,dict) or type(final.get('enabled',False)) is not bool:raise ValueError('Choose whether to play a championship final.')
    if final.get('enabled'):
        for key,default in (('games',8),('tiebreak_games',2)):
            value=integer(final.get(key,default),'Championship games')
            if value%2:raise ValueError('Championship and tiebreak game counts must be even for color-reversed opening pairs.')
            final[key]=value
        controls=final.get('controls',[])
        if not isinstance(controls,list):raise ValueError('Playoff controls must be a list')
        from .models import TimeControl
        for control in controls:
            if not isinstance(control,dict) or not control:raise ValueError('Each playoff stage needs a time control')
            TimeControl.parse(control)
        final['controls']=controls
    d['championship']=final
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
            'regular_winner':tables[0][0]['name'],'regular_winner_slot':tables[0][0]['slot'],
            'champion':None if d.get('championship',{}).get('enabled') else tables[0][0]['name'],
            'policy':'Game points, configured standings tiebreaks, then recorded initial seed. Movements apply after every division finishes. Championship games do not change division standings or movement.'}


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
    if e['body'].get('opening_plan'):
        plan=e['body']['opening_plan'];plan['required_minimum']=plan['positions_per_season']*d['seasons']
        plan['reuse_expected']=plan['required_minimum']>plan['available']
    if e['body']['regular_games']>9223372036854775807:raise ValueError('Event exceeds 64-bit game numbering capacity.')
    with store.tx():
        for i,g in enumerate(decision['next_groups']):child(store,e,g,e['stage']+1,i)
        change(store,e['id'],stage=e['stage']+1,body=encode(e['body']),state='paused',note='Another season is prepared from the saved promotion and relegation places. Run event when ready.')
        store.audit(None,'league_extended',{'event':e['id'],'season':d['seasons']})
