"""Match outcomes from a committed snapshot; diagnostics never enter the bracket."""
import json
from collections import defaultdict
from .knockout import format_name,round_cycles

NOTE=('KO order puts surviving engines first, then the latest round of elimination; '
      'engines eliminated in the same round are listed by initial seed, not awarded different places. '
      'W-D-L, game points, Elo, CI and LOS describe official games, including tiebreaks; they do not decide bracket advancement. '
      'Results at different time controls and against different opponents are pooled, not a single uniform strength test.')
from .knockout import SAMPLE_NOTE
NOTE+=' '+SAMPLE_NOTE


def read(store,tid,s):
    from .rounds import match_key,resolve_match
    ranks={r['slot']:r for r in store.rows('SELECT *,score+bye_points points FROM rankings WHERE tid=?',(tid,))}
    names={r['slot']:r['name'] for r in store.rows("SELECT slot,json_extract(profile,'$.name') name FROM participants WHERE tid=?",(tid,))}
    people={a:{'slot':a,'name':names[a],'match_wins':0,'match_losses':0,'byes':0,'eliminated_round':None} for a in ranks}
    threshold=1 if s['format']=='knockout' else 2;legs=2 if s['paired'] else 1;rounds=[]
    for row in store.rows('SELECT round,body FROM round_state WHERE tid=? ORDER BY round',(tid,)):
        saved=json.loads(row['body']);chunks=saved.get('chunks',[]);stats={};by_match=defaultdict(list)
        for i,c in enumerate(chunks):by_match[match_key(c['a'],c['b'])].append((i,c))
        # Indexed pair ranges keep moves/telemetry out of result rendering.
        if chunks:
            for r in store.rows('''SELECT c.key chunk,count(a.id) completed,
              coalesce(sum(CASE a.result WHEN '1/2-1/2' THEN .5 WHEN '1-0' THEN (g.white=json_extract(c.value,'$.a')) WHEN '0-1' THEN (g.black=json_extract(c.value,'$.a')) ELSE 0 END),0) score,
              coalesce(sum(g.state IN ('pending','running') AND (g.official IS NULL OR g.mode='replacement')),0) unfinished
              FROM json_each(?) c LEFT JOIN games g ON g.tid=? AND g.invalid=0
              AND g.pair_no>=json_extract(c.value,'$.start') AND g.pair_no<json_extract(c.value,'$.start')+json_extract(c.value,'$.count')
              LEFT JOIN attempts a ON a.id=g.official GROUP BY c.key''',(json.dumps(chunks),tid)):
                stats[r['chunk']]=r
        byes=saved.get('byes',[])
        for a in byes:people[a]['byes']+=1
        matches=[]
        for a,b in saved.get('matches',[]):
            key=match_key(a,b);stages=[]
            for i,c in by_match[key]:
                v=stats[i];score=v['score'] if c['a']==a else v['completed']-v['score']
                stages.append({'stage':len(stages),'games':c['count']*legs,'completed':v['completed'],'a_score':score,'b_score':v['completed']-score,
                    'finished':v['completed']==c['count']*legs and not v['unfinished'],'time_control':c.get('time_control')})
            last=stages[-1] if stages else None;winner=None;method=None
            if last and last['finished']:
                if last['a_score']!=last['b_score']:winner=a if last['a_score']>last['b_score'] else b;method='playoff' if last['stage'] else 'score'
                else:
                    # Reuse recorded legacy/manual policies without reinterpreting old tournaments.
                    decision=resolve_match(saved,[],a,b,s,ranks);winner=decision.get('winner');method=decision.get('method')
            if winner is not None:
                loser=b if winner==a else a;people[winner]['match_wins']+=1;people[loser]['match_losses']+=1
                if people[loser]['match_losses']>=threshold:people[loser]['eliminated_round']=row['round']+1
            status=('Winner: '+names[winner]) if winner is not None else ('Tied — more games required' if last and last['finished'] and s.get('knockout_tiebreak')=='continuous' else 'Tied — awaiting tiebreak decision' if last and last['finished'] else 'Tiebreak in progress' if last and last['stage'] else 'Match in progress')
            matches.append({'a':a,'b':b,'a_name':names[a],'b_name':names[b],'a_score':sum(v['a_score'] for v in stages),'b_score':sum(v['b_score'] for v in stages),
                'winner':winner,'method':method,'decision_basis':{'score':'Game score','playoff':'Tiebreak game score','manual':'Manual decision','seed':'Initial seed','wins':'Wins','black_wins':'Wins with Black','buchholz':'Buchholz','sonneborn_berger':'Sonneborn–Berger'}.get(method,''),
                'status':status,'stages':stages,'regular_games':round_cycles(s,row['round'])*legs})
        rounds.append({'round':row['round']+1,'matches':matches,'byes':[{'slot':a,'name':names[a]} for a in byes]})
    remaining=[a for a,p in people.items() if p['eliminated_round'] is None]
    champion=remaining[0] if len(remaining)==1 and any(p['match_wins'] for p in people.values()) else None
    current=rounds[-1]['round'] if rounds else 0
    for a,p in people.items():
        p['ko_status']='Champion' if a==champion else 'Eliminated in round '+str(p['eliminated_round']) if p['eliminated_round'] else ('Still in KO · '+str(p['match_losses'])+' match loss' if p['match_losses'] else 'Still in KO')
        p['ko_finish']=p['ko_status']
        if s['format']=='knockout' and p['eliminated_round']:
            from .knockout import round_matches
            remaining_rounds=len(round_matches(len(people)))-p['eliminated_round']
            p['ko_finish']={0:'Runner-up',1:'Semifinalist',2:'Quarterfinalist'}.get(remaining_rounds,p['ko_status'])
    order=sorted(people,key=lambda a:(people[a]['eliminated_round'] is not None, -(people[a]['eliminated_round'] or current+1),people[a]['match_losses'] if people[a]['eliminated_round'] is None else 0,ranks[a]['seed']))
    return {'format':format_name(s['format']),'round':current,'champion':names[champion] if champion is not None else None,'champion_slot':champion,
        'remaining':len(remaining),'rounds':rounds,'people':people,'order':order,'note':NOTE,'unbounded':s.get('knockout_tiebreak')=='continuous'}


def public(value,full=False):
    rounds=value['rounds']
    selected=[dict(r,matches=r['matches'] if full else r['matches'][:50],match_count=len(r['matches']),byes=r['byes'] if full else r['byes'][:50],bye_count=len(r['byes'])) for r in (rounds if full else rounds[-1:])]
    return {k:v for k,v in value.items() if k not in ('people','order','rounds')}|{'rounds':selected,'full':full}
