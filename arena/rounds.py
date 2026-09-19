"""Audited round plans, computed outside the writer, with bounded scheduling."""
from collections import Counter,defaultdict
import hashlib
import json
import networkx as nx
from .rankings import rows as ranking_rows,point_delta

DYNAMIC=('swiss','knockout','double_elimination','ladder')
def encode(v):return json.dumps(v,separators=(',',':'),sort_keys=True)
def match_key(a,b):return f'{min(a,b)}:{max(a,b)}'

def ladder_positions(n,round_no,distance=1):
    shift=round_no%(distance+1);order=list(range(n));order=order[shift:]+order[:shift];used=set();pairs=[]
    for a in order:
        b=a+distance
        if b<n and a not in used and b not in used:pairs.append((a,b));used.update((a,b))
    return pairs,[i for i in range(n) if i not in used]

def bracket_seeds(n):
    order=[0];size=1
    while size<n:
        size*=2;order=[x for seed in order for x in (seed,size-1-seed)]
    return order

def color_cost(a,b,colors,recent):
    return abs(colors[a]+1)+abs(colors[b]-1)+10*int(recent[a][-2:]==[1,1])+10*int(recent[b][-2:]==[-1,-1])

def orient(a,b,colors,recent,seeds,round_no):
    x=color_cost(a,b,colors,recent);y=color_cost(b,a,colors,recent)
    return (b,a) if y<x or (y==x and (seeds[a]>seeds[b])!=(round_no%2==1)) else (a,b)

def swiss_matches(pool,points,seeds,colors,recent,opponents,bye_counts,allow_rematches=False):
    """Expand sparse score-neighbor bands until maximum matching covers all.

    Rematches are forbidden unless explicitly enabled. Edge weights prefer
    similar scores, balanced colors and new opponents; bye weights prefer
    players without a previous bye and lower scores. Engine Swiss, not FIDE Dutch.
    """
    n=len(pool);dummy=-1;window=min(8,max(1,n-1));index={a:i for i,a in enumerate(pool)}
    while True:
        graph=nx.Graph();graph.add_nodes_from(pool);scale=(n+1)**3;max_score=max(points.values(),default=0)
        for i,a in enumerate(pool):
            for j in range(i+1,min(n,i+window+1)):
                b=pool[j];repeated=b in opponents[a]
                if repeated and not allow_rematches:continue
                cost=round(abs(points[a]-points[b])*2)*scale+min(color_cost(a,b,colors,recent),color_cost(b,a,colors,recent))*(n+1)+abs(i-j)
                if repeated:cost+=round((max_score*2+1)*scale*(n+1))
                graph.add_edge(a,b,weight=cost)
        if n%2:
            graph.add_node(dummy)
            for a in pool:graph.add_edge(a,dummy,weight=round((bye_counts[a]*(max_score+1)+points[a])*scale*(n+1)**2+(n-1-index[a])))
        found=nx.min_weight_matching(graph)
        if len(found)*2==len(graph):
            byes=[a if b==dummy else b for a,b in found if dummy in (a,b)]
            matches=[tuple(sorted((a,b),key=lambda x:index[x])) for a,b in found if dummy not in (a,b)]
            return sorted(matches,key=lambda pair:index[pair[0]]),byes
        if window>=n-1:return None,None
        window=min(n-1,window*2)

def context(store,t,allow_paused=False):
    if t['settings']['format'] not in DYNAMIC or (not allow_paused and t['state']!='running'):return None
    if store.one("SELECT id FROM games WHERE tid=? AND invalid=0 AND state IN ('pending','running') LIMIT 1",(t['id'],)):return None
    states={r['round']:json.loads(r['body']) for r in store.rows('SELECT round,body FROM round_state WHERE tid=? ORDER BY round',(t['id'],))}
    if any(c.get('materialized',c['count'])<c['count'] for state in states.values() for c in state.get('chunks',[])):return None
    records=store.rows('SELECT g.*,a.result FROM games g JOIN attempts a ON a.id=g.official WHERE g.tid=? AND g.invalid=0 ORDER BY g.number',(t['id'],))
    signature=hashlib.sha256(encode({'round':t['round'],'cursor':t['cursor'],'official':[(g['id'],g['official']) for g in records],'states':states}).encode()).hexdigest()
    return {'tournament':t,'states':states,'records':records,'rankings':ranking_rows(store,t['id'],t['settings']),'signature':signature}

def score_match(records,a,b,start=None,end=None):
    games=[g for g in records if {g['a'],g['b']}=={a,b} and (start is None or start<=g['pair_no']<end)]
    return sum(.5 if g['result']=='1/2-1/2' else int((g['result']=='1-0')==(g['white']==a)) for g in games),len(games)

def resolve_match(previous,records,a,b,s,ranks):
    key=match_key(a,b);manual=previous.get('manual_winners',{}).get(key)
    if manual is not None:return {'winner':manual,'method':'manual'}
    stages=previous.get('playoffs',{}).get(key,[])
    span=[stages[-1]['start'],stages[-1]['end']] if stages else previous.get('regular_pairs',{}).get(key,[None,None])
    score,count=score_match(records,a,b,*span)
    if count and score!=count/2:return {'winner':a if score>count/2 else b,'method':'playoff' if stages else 'score'}
    method=s.get('knockout_tiebreak','seed')
    if method=='playoff' and len(stages)<s.get('playoff_limit',3):return {'playoff':True}
    if method=='playoff':method=s.get('playoff_fallback','seed')
    if method=='manual':return {'manual':True}
    field={'sonneborn_berger':'sb'}.get(method,method);av=ranks[a][field];bv=ranks[b][field]
    if av==bv:method=field='seed';av=ranks[a]['seed'];bv=ranks[b]['seed']
    return {'winner':a if ((av<bv) if field=='seed' else (av>bv)) else b,'method':method}

def build_plan(ctx):
    t=ctx['tournament'];s=t['settings'];fmt=s['format'];states=ctx['states'];previous=states.get(t['round']);round_no=t['round']+int(previous is not None)
    ranks={r['slot']:r for r in ctx['rankings']};seeds={a:r['seed'] for a,r in ranks.items()};points={a:r['points'] for a,r in ranks.items()};ordered=sorted(ranks,key=lambda a:seeds[a]);n=len(ordered)
    records=ctx['records'];colors=Counter();recent=defaultdict(list);opponents=defaultdict(set);byes=Counter()
    for r in records:
        colors[r['white']]+=1;colors[r['black']]-=1;recent[r['white']].append(1);recent[r['black']].append(-1);opponents[r['white']].add(r['black']);opponents[r['black']].add(r['white'])
    for state in states.values():byes.update(state.get('byes',[]))
    plan={'tid':t['id'],'signature':ctx['signature'],'round':round_no,'kind':'round','matches':[],'byes':[],'scores':points,'losses':{},'decisions':{},'order':ordered}
    if fmt=='swiss' and round_no>=s['rounds']:plan.update(kind='completed',note='Scheduled rounds complete');return plan
    if fmt in ('knockout','double_elimination'):
        losses={int(k):v for k,v in (previous.get('losses',{}) if previous else {}).items()};winners={};playoffs=[];manual=[]
        if previous:
            round_records=[g for g in records if g['round']==t['round']]
            for a,b in previous['matches']:
                key=match_key(a,b);decision=resolve_match(previous,round_records,a,b,s,ranks);plan['decisions'][key]=decision
                if decision.get('playoff'):playoffs.append((a,b));continue
                if decision.get('manual'):manual.append((a,b));continue
                winner=decision['winner'];winners[key]=winner;loser=b if winner==a else a;losses[loser]=losses.get(loser,0)+1
            if playoffs or manual:
                plan.update(kind='playoffs' if playoffs else 'blocked',round=t['round'],matches=playoffs,manual=manual,note='Resolve tied matchups in Pairings before the next round.' if manual else 'Playing configured tiebreak games.');return plan
        remaining=[a for a in ordered if losses.get(a,0)<(1 if fmt=='knockout' else 2)];plan['losses']=losses
        if len(remaining)==1:plan.update(kind='completed',winner=remaining[0],note='Elimination complete');return plan
        if not previous:
            bracket=[ordered[i] if i<n else None for i in bracket_seeds(n)];slots=list(zip(bracket[::2],bracket[1::2]));plan['bracket_slots']=slots
            plan['matches']=[(a,b) for a,b in slots if a is not None and b is not None];plan['byes']=[a if b is None else b for a,b in slots if a is None or b is None]
        elif fmt=='knockout':
            prior_slots=previous.get('bracket_slots') or [*previous['matches'],*((a,None) for a in previous.get('byes',[]))]
            next_order=[a if b is None else b if a is None else winners[match_key(a,b)] for a,b in prior_slots]
            if len(next_order)%2:next_order.append(None)
            slots=list(zip(next_order[::2],next_order[1::2]));plan['bracket_slots']=slots
            plan['matches']=[(a,b) for a,b in slots if a is not None and b is not None];plan['byes']=[a if b is None else b for a,b in slots if a is None or b is None]
        else:
            unbeaten=[a for a in remaining if losses.get(a,0)==0];once=[a for a in remaining if losses.get(a,0)==1]
            if len(unbeaten)==len(once)==1:plan['matches']=[(unbeaten[0],once[0])]
            else:
                for group in (unbeaten,once):
                    if len(group)%2:
                        bye=min(group,key=lambda a:(byes[a],seeds[a]));group.remove(bye);plan['byes'].append(bye)
                    while group:
                        a=group.pop(0);j=next((i for i,b in enumerate(group) if b not in opponents[a]),0);plan['matches'].append((a,group.pop(j)))
    elif fmt=='ladder':
        order=list(previous.get('ladder_order',ordered)) if previous else ordered
        if previous:
            for a,b in previous['matches']:
                score,count=score_match([g for g in records if g['round']==t['round']],a,b)
                if not count or score==count/2:continue
                winner=a if score>count/2 else b;loser=b if winner==a else a;wi,li=order.index(winner),order.index(loser)
                if wi>li:
                    if s.get('ladder_swap','adjacent')=='leap':order.pop(wi);order.insert(li,winner)
                    else:order[wi],order[li]=order[li],order[wi]
        if round_no>=s['rounds']:plan.update(kind='completed',note='Scheduled rounds complete',ladder_order=order);return plan
        pairs,rests=ladder_positions(n,round_no,s.get('ladder_distance',1));plan.update(matches=[(order[a],order[b]) for a,b in pairs],byes=[order[a] for a in rests],ladder_order=order)
    else:
        pool=[r['slot'] for r in ctx['rankings']]
        if not previous:
            if n%2:plan['byes']=[pool.pop()]
            half=len(pool)//2;plan['matches']=list(zip(pool[:half],pool[half:]))
        else:
            matches,round_byes=swiss_matches(pool,points,seeds,colors,recent,opponents,byes,s.get('swiss_rematches',False))
            if matches is None:plan.update(kind='blocked',note='No rematch-free Swiss pairing exists for these results. Use Pairings to supply an explicit round and approve any required rematches.');return plan
            plan['matches']=matches;plan['byes']=round_byes
    plan['matches']=[orient(a,b,colors,recent,seeds,round_no) for a,b in plan['matches']]
    return plan

def materialize(store,t,window):
    queued=store.one("SELECT count(*) n FROM games WHERE tid=? AND invalid=0 AND state IN ('pending','running')",(t['id'],))['n'];remaining=max(0,window-queued);s=t['settings'];legs=2 if s['paired'] else 1
    if not remaining:return
    for row in store.rows('SELECT round,body FROM round_state WHERE tid=? ORDER BY round',(t['id'],)):
        state=json.loads(row['body']);changed=False
        if not any(c.get('materialized',c['count'])<c['count'] for c in state.get('chunks',[])):continue
        with store.tx():
            for c in state.get('chunks',[]):
                done=c.get('materialized',c['count']);take=min(c['count']-done,(remaining+legs-1)//legs)
                for j in range(take):store._insert_pair(t['id'],c['start']+done+j,c['a'],c['b'],row['round'],s,fixed_colors=True,stage=c['phase'],cycle=(done+j)%s['cycles'])
                if take:c['materialized']=done+take;remaining-=take*legs;changed=True
                if remaining<=0:break
            if changed:store.db.execute('UPDATE round_state SET body=? WHERE tid=? AND round=?',(encode(state),t['id'],row['round']))
        if remaining<=0:break

def apply_plan(store,plan,allow_paused=False):
    t=store.tournament(plan['tid']);current=context(store,t,allow_paused)
    if not current or current['signature']!=plan['signature']:return False
    tid=t['id'];s=t['settings'];kind=plan['kind'];round_no=plan['round']
    with store.tx():
        if kind=='completed':
            if 'ladder_order' in plan:
                previous=current['states'][t['round']];previous['final_ladder_order']=plan['ladder_order']
                store.db.execute('UPDATE round_state SET body=? WHERE tid=? AND round=?',(encode(previous),tid,t['round']))
            note='Winner: '+store.participant(tid,plan['winner'])['name'] if 'winner' in plan else plan['note'];total=store.one('SELECT count(*) n FROM games WHERE tid=? AND invalid=0',(tid,))['n']
            store.db.execute("UPDATE tournaments SET state='completed',note=?,total=? WHERE id=?",(note,total,tid));store.audit(tid,'competition_completed',plan);return True
        if kind=='blocked':
            store.db.execute("UPDATE tournaments SET state='paused',dependency=?,note=? WHERE id=?",(plan['note'],plan['note'],tid));store.audit(tid,'pairing_attention_required',plan);return True
        start=max(t['cursor'],store.one('SELECT coalesce(max(pair_no),-1)+1 n FROM games WHERE tid=?',(tid,))['n']);cursor=start
        if kind=='playoffs':state=current['states'][round_no];cycles=s.get('playoff_cycles',1)
        else:state={k:v for k,v in plan.items() if k not in ('signature','kind','tid')};state.update(chunks=[],regular_pairs={},playoffs={});cycles=s['cycles']
        for a,b in plan['matches']:
            key=match_key(a,b);state['chunks'].append({'start':cursor,'count':cycles,'materialized':0,'a':a,'b':b,'phase':'playoff' if kind=='playoffs' else 'regular'})
            if kind=='playoffs':state.setdefault('playoffs',{}).setdefault(key,[]).append({'start':cursor,'end':cursor+cycles})
            else:state['regular_pairs'][key]=[cursor,cursor+cycles]
            cursor+=cycles
        if kind!='playoffs':
            state['bye_awards']=[(a,cycles*(2 if s['paired'] else 1)*s.get('bye_score',1)) for a in plan['byes']] if s['format']=='swiss' else []
            for a,points in state['bye_awards']:point_delta(store,tid,a,points,'bye_points')
        store.db.execute('INSERT OR REPLACE INTO round_state VALUES(?,?,?)',(tid,round_no,encode(state)))
        extra=(cursor-start)*(2 if s['paired'] else 1) if kind=='playoffs' else 0
        store.db.execute("UPDATE tournaments SET round=?,cursor=?,total=total+?,dependency='',note=? WHERE id=?",(round_no,cursor,extra,'Tiebreak games scheduled.' if kind=='playoffs' else f'Round {round_no+1} pairings saved.',tid));store.audit(tid,'playoff_scheduled' if kind=='playoffs' else 'round_paired',state)
        from .dependencies import update_total
        update_total(store,tid)
    return True

def advance_round(store,t,window=64,defer=False):
    materialize(store,t,window);ctx=context(store,store.tournament(t['id']))
    if ctx is None:return None
    if defer:return ctx
    apply_plan(store,build_plan(ctx));materialize(store,store.tournament(t['id']),window)

def manual_round(store,tid,matches,byes,allow_rematches=False,signature=None):
    t=store.tournament(tid)
    if t['settings']['format']!='swiss':raise ValueError('Manual round editing is for Swiss tournaments')
    if t['state']!='paused':raise ValueError('Pause and drain before supplying a round')
    ctx=context(store,t,True)
    if ctx is None:raise ValueError('Finish the existing round before supplying the next one')
    if signature is not None and signature!=ctx['signature']:raise ValueError('Results changed since pairing review. Review the round again.')
    flat=[a for pair in matches for a in pair]+byes
    if any(len(pair)!=2 for pair in matches) or len(flat)!=t['participants'] or set(flat)!=set(range(t['participants'])):raise ValueError('Every participant must occur exactly once in matches or byes')
    if len(byes)!=t['participants']%2:raise ValueError('Exactly one bye is required for an odd field; none for an even field')
    faced={frozenset((g['a'],g['b'])) for g in ctx['records']};rematches=[pair for pair in matches if frozenset(pair) in faced]
    if rematches and not allow_rematches:raise ValueError('This round contains rematches. Explicitly approve them to continue.')
    round_no=t['round']+int(t['round'] in ctx['states'])
    if round_no>=t['settings']['rounds']:raise ValueError('The scheduled Swiss rounds are complete')
    plan={'tid':tid,'signature':ctx['signature'],'round':round_no,'kind':'round','matches':matches,'byes':byes,'manual':True,'rematches':rematches,'scores':{r['slot']:r['points'] for r in ctx['rankings']}}
    if not apply_plan(store,plan,True):raise ValueError('Round inputs changed; review again')
    return {'paired':len(matches),'round':round_no,'byes':byes}

def manual_winner(store,tid,a,b,winner):
    t=store.tournament(tid)
    if t['state']!='paused' or t['settings']['format'] not in ('knockout','double_elimination'):raise ValueError('Pause the elimination tournament first')
    ctx=context(store,t,True)
    if ctx is None:raise ValueError('Finish the active round first')
    previous=ctx['states'].get(t['round']);key=match_key(a,b)
    if not previous or key not in {match_key(*pair) for pair in previous['matches']} or winner not in (a,b):raise ValueError('Choose a participant in the tied matchup')
    plan=build_plan(ctx)
    if (a,b) not in plan.get('manual',[]) and (b,a) not in plan.get('manual',[]):raise ValueError('This matchup does not need a manual tiebreak')
    with store.tx():
        previous.setdefault('manual_winners',{})[key]=winner;store.db.execute('UPDATE round_state SET body=? WHERE tid=? AND round=?',(encode(previous),tid,t['round']));store.db.execute("UPDATE tournaments SET dependency='',note='Manual tiebreak recorded; resume to continue.' WHERE id=?",(tid,));store.audit(tid,'manual_tiebreak',{'round':t['round'],'match':[a,b],'winner':winner})
    return {'winner':winner}
