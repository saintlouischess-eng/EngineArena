"""Configurable season stages. Decisions and their successor commit together.

Existing events continue through the original scheduler. New season events keep
explicit checkpoints, so replacing a result restores the exact earlier roster,
opening cursor and advancement state without discarding any original attempt.
"""
import copy
import json
import time
import hashlib
from . import events
from . import season_admission as admission
from .store import encode,uid


def number(value,label,minimum=1):
    return events.integer(value,label,minimum)


def groups_valid(groups,n,movement):
    if not isinstance(groups,list) or not groups or any(not isinstance(g,list) or len(g)<2 for g in groups):
        raise ValueError('Each division needs at least two engines.')
    slots=[s for g in groups for s in g]
    if any(type(s) is not int or not 0<=s<n for s in slots) or len(slots)!=len(set(slots)):
        raise ValueError('Assign each selected engine to exactly one division.')
    if len(movement)!=len(groups)-1 or any(type(v) is not int or v<0 for v in movement):
        raise ValueError('Enter a nonnegative movement count for each division boundary.')
    for i,g in enumerate(groups):
        if (movement[i-1] if i else 0)+(movement[i] if i<len(movement) else 0)>len(g):
            raise ValueError('Promotion and relegation places overlap in a division. Reduce the movement counts.')


def prepare(store,source_tid,definition):
    d=copy.deepcopy(definition);t=store.tournament(source_tid);s=copy.deepcopy(t['settings'])
    profiles=[json.loads(r['profile']) for r in store.rows('SELECT profile FROM participants WHERE tid=? ORDER BY slot',(source_tid,))]
    n=len(profiles);sizes=d.get('sizes',[])
    if not isinstance(sizes,list) or not sizes or any(type(v) is not int or v<2 for v in sizes):
        raise ValueError('Each division needs at least two engines.')
    admission.validate(d,n)
    if not admission.enabled(d) and sum(sizes)!=n:
        raise ValueError('Division sizes must total the participant count, with at least two engines per division.')
    offset=0;groups=[]
    for size in sizes:groups.append(list(range(offset,offset+size)));offset+=size
    if d.get('groups') is not None:groups=d['groups']
    if (not admission.enabled(d) and sorted(v for g in groups for v in g)!=list(range(n))) or list(map(len,groups))!=sizes:
        raise ValueError('Assign every participant once and match the selected division sizes.')
    d.setdefault('movement',[1]*(len(groups)-1));groups_valid(groups,n,d['movement']);d['groups']=groups
    d.setdefault('mode','divisions');d.setdefault('update_policy','season');d.setdefault('review_policy','season');d.setdefault('tie_policy','playoff')
    for key,allowed in [('mode',('divisions','progressive')),('update_policy',('frozen','season','stage')),('review_policy',('automatic','season','stage')),('tie_policy',('standings','playoff'))]:
        if d[key] not in allowed:raise ValueError('Invalid season policy: '+key)
    d['seasons']=number(d.get('seasons',1),'Seasons');d['cycles']=number(d.get('cycles',1),'Pairs per matchup')
    d['playoff_pairs']=number(d.get('playoff_pairs',1),'Playoff pairs')
    names=d.get('division_names') or ['Division '+str(i+1) for i in range(len(groups))]
    if len(names)!=len(groups) or any(not isinstance(v,str) or not v.strip() for v in names) or len(set(names))!=len(names):
        raise ValueError('Enter distinct division names, highest first.')
    d['division_names']=names
    q=d.setdefault('qualifier',{'enabled':False});q.setdefault('format','swiss');q.setdefault('rounds',7);q.setdefault('cycles',1)
    if type(q.get('enabled')) is not bool or q['format'] not in ('swiss','round_robin'):raise ValueError('Choose a qualifying format.')
    number(q['rounds'],'Swiss rounds');number(q['cycles'],'Qualification pairs')
    if q['enabled'] and q['format']=='swiss' and q['rounds']>n-1:raise ValueError('Swiss rounds cannot exceed the number of possible opponents.')
    final=d.setdefault('championship',{'enabled':True,'games':8,'tiebreak_games':2})
    from .leagues import validate
    # Reuse championship control validation without imposing legacy movement rules.
    fake={'groups':[[0,1],[2,3]],'championship':final};validate(fake);d['championship']=fake['championship']
    final.setdefault('play_all',True)
    if type(final['play_all']) is not bool:raise ValueError('Choose whether to play all championship games.')
    from .tournament_queue import validate_resources
    d['resources']=validate_resources(d.get('resources',dict(cpu_budget=s['cpu_budget'],memory_budget_mb=s['memory_budget_mb'],concurrency=s['concurrency'],gpu_limits=s['gpu_limits'])))
    from .tournament_edit import original_openings
    s['openings']=original_openings(s)
    for key in ('custom_matchups','ko_round_games','event_context','event_opening_offset'):s.pop(key,None)
    s.update(paired=True,opening_policy='pair',schedule_order=d.get('schedule_order','balanced'),schedule_seed=d.get('schedule_seed',7970))
    from .schedule_order import validate as schedule_validate
    schedule_validate(s)
    templates={}
    for key,source in d.get('stage_sources',{}).items():
        if key not in ['qualification','championship',*map(str,range(len(groups)))]:raise ValueError('Unknown stage conditions.')
        template=store.tournament(source)['settings'];template=copy.deepcopy(template)
        template['openings']=original_openings(template)
        for field in ('custom_matchups','ko_round_games','event_context','event_opening_offset'):template.pop(field,None)
        templates[key]=template
    for key,value in d.get('stage_cycles',{}).items():
        if key not in list(map(str,range(len(groups)))):raise ValueError('Unknown stage conditions.')
        number(value,'Stage pairs per matchup')
    runtime={'season':1,'phase':'qualification' if q['enabled'] else 'division','bucket':len(groups)-1 if d['mode']=='progressive' else 0,
             'groups':groups,'next_groups':[[] for _ in groups],'incoming':[],'offset':0,'review':True,'season_start':True,'history':[]}
    body={'definition':d,'profiles':profiles,'identities':[uid() for _ in profiles],'settings':s,'source_name':t['name'],
          'templates':templates,'season_state':runtime,'updates':[]}
    if admission.enabled(d):
        runtime['candidates']=list(range(n));admission.begin(body)
    body['opening_keys']={key:hashlib.sha256(encode([value['openings'],value['seed'],value['chess960']]).encode()).hexdigest() for key,value in {'source':s,**templates}.items()}
    body['regular_games']=minimum(store,body)
    return body,body['regular_games']


def stage_settings(body,key):
    s=copy.deepcopy(body['templates'].get(key,body['settings']))
    # A season stage is always paired; its schedule does not depend on the source format.
    s.update(paired=True,opening_policy='pair',opening_order='shuffle',schedule_order=body['settings']['schedule_order'],schedule_seed=body['settings']['schedule_seed'])
    s['season_opening_key']=body['opening_keys'][key if key in body['templates'] else 'source']
    return s


def prepared(store,body,slots,role,bucket=0):
    d=body['definition'];key=str(bucket) if role=='division' else role
    s=stage_settings(body,key);openings=s.pop('openings')
    s.update(format='round_robin',cycles=d.get('stage_cycles',{}).get(str(bucket),d['cycles']))
    if role=='qualification':
        s.update(format=d['qualifier']['format'],rounds=min(d['qualifier']['rounds'],len(slots)-1) if admission.enabled(d) else d['qualifier']['rounds'],cycles=d['qualifier']['cycles'])
    if role=='championship':
        f=d['championship'];s.update(format='knockout',cycles=f['games']//2,knockout_tiebreak='continuous',playoff_cycles=f['tiebreak_games']//2,playoff_controls=f.get('controls',[]),seeding='input')
        s['season_clinch']=not f['play_all']
    if role=='playoff':s.update(format='round_robin',cycles=d['playoff_pairs'])
    profiles=[copy.deepcopy(body['profiles'][i]) for i in slots]
    if key in body['templates']:
        for p in profiles:p.pop('time_control',None)
    return store.prepare_tournament(profiles,s,openings)


def minimum(store,body):
    if admission.enabled(body['definition']):return admission_minimum(store,body,1)
    d=body['definition'];groups=body['season_state']['groups'];total=0
    for i,g in enumerate(groups):
        field=g+([-1]*d['movement'][i] if d['mode']=='progressive' and i<len(groups)-1 else [])
        total+=prepared(store,body,[0]*len(field),'division',i)[2]
    if d['championship']['enabled']:total+=d['championship']['games']
    total*=d['seasons']
    if d['qualifier']['enabled']:total+=prepared(store,body,[0]*sum(map(len,groups)),'qualification')[2]
    if total>9223372036854775807:raise ValueError('Event exceeds 64-bit game numbering capacity.')
    return total


def admission_minimum(store,body,start,remaining=False):
    """Forecast without materializing games or engine processes."""
    d=body['definition'];r=body['season_state'];total=0
    for season in range(start,d['seasons']+1):
        current=season==r['season'] and remaining
        phase=r.get('resolution',{}).get('phase',r['phase']) if current else 'qualification'
        if phase=='qualification':
            count=len(r['admission_plan']['contestants']) if current else len(admission.pool(body))-(sum(d['sizes'])-d['admission']['places'] if season>1 and d['admission']['policy']=='challenge' else 0)
            if count>1:total+=prepared(store,body,[0]*count,'qualification')[2]
        if phase!='championship':
            for i,size in enumerate(d['sizes']):
                if current and phase=='division' and d['mode']=='progressive' and i>r['bucket']:continue
                count=size+(d['movement'][i] if d['mode']=='progressive' and i<len(d['sizes'])-1 else 0)
                total+=prepared(store,body,[0]*count,'division',i)[2]
        if d['championship']['enabled']:total+=d['championship']['games']
    if total>9223372036854775807:raise ValueError('Event exceeds 64-bit game numbering capacity.')
    return total


def checkpoint(body):
    return copy.deepcopy({k:body[k] for k in ('season_state','profiles','identities','updates','definition','regular_games')})


def remaining_minimum(store,body):
    """Remaining regular schedule at a review boundary, excluding played stages."""
    r=body['season_state'];d=body['definition'];total=0
    if admission.enabled(d):return admission_minimum(store,body,r['season'],True)
    for season in range(r['season'],d['seasons']+1):
        if season==r['season'] and r['phase']=='championship':
            total+=d['championship']['games'];continue
        for i,g in enumerate(r['groups']):
            if season==r['season'] and d['mode']=='progressive' and i>r['bucket']:continue
            count=len(g)+(d['movement'][i] if d['mode']=='progressive' and i<len(r['groups'])-1 else 0)
            total+=prepared(store,body,[0]*count,'division',i)[2]
        if d['championship']['enabled']:total+=d['championship']['games']
    if r['phase']=='qualification':total+=prepared(store,body,[0]*sum(map(len,r['groups'])),'qualification')[2]
    return total


def make_child(store,e,slots,role,bucket=0,*,playoff_for=None):
    b=e['body'];r=b['season_state'];d=b['definition'];p,s,total=prepared(store,b,slots,role,bucket)
    if role=='playoff':
        task=r['resolution']['tasks'][0]
        key='qualification' if r['resolution']['phase']=='qualification' else str(r['bucket'] if d['mode']=='progressive' else task['table'])
        s=stage_settings(b,key);op=s.pop('openings');s.update(format='round_robin',cycles=d['playoff_pairs'])
        if key in b['templates']:
            for profile in p:profile.pop('time_control',None)
        p,s,total=store.prepare_tournament(p,s,op)
    label=(('Season '+str(r['season'])+' — ' if admission.enabled(d) else '')+'Qualification' if role=='qualification' else 'Season '+str(r['season'])+' — '+('Championship' if role=='championship' else 'Placement playoff' if role=='playoff' else d['division_names'][bucket]))
    s.update(event_opening_offset=r.get('book_offsets',{}).get(s['season_opening_key'],0),event_context={'id':e['id'],'name':e['name'],'stage':e['stage']+1,'season':r['season'],'label':label,'slots':slots,'role':role,'base_games':total,'identities':[b['identities'][v] for v in slots]})
    tid=store.insert_tournament(e['name']+' — '+label,(p,s,total))
    store.db.execute('INSERT INTO event_children(tid,eid,stage,bucket,valid,role) VALUES(?,?,?,?,1,?)',(tid,e['id'],e['stage'],bucket,role))
    return tid


def table(store,c):
    from .rankings import rows
    t=store.tournament(c['tid']);slots=t['settings']['event_context']['slots'];result=[]
    for i,row in enumerate(rows(store,c['tid'],t['settings'])):
        result.append({'slot':slots[row['slot']],'name':store.participant(c['tid'],row['slot'])['name'],'points':row['points'],'rank':i+1})
    return result


def boundary_ties(rows,cuts):
    tasks=[];start=0
    while start<len(rows):
        end=start+1
        while end<len(rows) and rows[end]['points']==rows[start]['points']:end+=1
        local=[c-start for c in cuts if start<c<end]
        if local:tasks.append({'start':start,'slots':[v['slot'] for v in rows[start:end]],'cuts':local})
        start=end
    return tasks


def cuts_for(d,r,bucket,rows):
    if r['phase']=='qualification':
        if admission.enabled(d):return admission.cuts({'definition':d,'season_state':r})
        total=0;cuts=[]
        for g in r['groups'][:-1]:total+=len(g);cuts.append(total)
        return cuts
    cuts=admission.risk_cuts(d,bucket,len(rows))
    if bucket>0 and d['movement'][bucket-1]:cuts.append(d['movement'][bucket-1])
    if bucket<len(r['groups'])-1 and d['movement'][bucket]:cuts.append(len(rows)-d['movement'][bucket])
    if bucket==0:cuts.append(2 if d['championship']['enabled'] else 1)
    return sorted(set(c for c in cuts if 0<c<len(rows)))


def save(store,e,**values):
    events.change(store,e['id'],body=encode(e['body']),**values)


def tick(store,e):
    b=e['body'];r=b['season_state'];d=b['definition'];eid=e['id']
    if r['review']:
        events.hold(store,'Review the season roster and approve the next stage.');return
    children=store.rows('SELECT c.*,t.state,t.dependency,t.note FROM event_children c JOIN tournaments t ON t.id=c.tid WHERE c.eid=? AND c.valid=1 AND c.stage=? ORDER BY c.bucket',(eid,e['stage']))
    with store.tx():
        if not children:
            r['checkpoint']=checkpoint({**b,'season_state':{k:v for k,v in r.items() if k!='checkpoint'}})
            if r['phase']=='qualification':
                slots=r['admission_plan']['contestants'] if admission.enabled(d) else [v for g in r['groups'] for v in g]
                if len(slots)<2:
                    decision={'stage':e['stage']+1,'season':r['season'],'phase':'qualification','standings':[],
                              'labels':['Season '+str(r['season'])+' — Qualification'], 'before':r.pop('checkpoint'),
                              'policy':'Uncontested admission; no game or rating result created.'}
                    advance(b,[[{'slot':s,'name':b['profiles'][s]['name'],'points':0} for s in slots]],decision)
                    decision['after']=checkpoint(b)
                    store.db.execute('INSERT OR REPLACE INTO event_decisions VALUES(?,?,?)',(eid,e['stage'],encode(decision)))
                    save(store,e,stage=e['stage']+1,state='paused' if r['review'] else 'running',note='Review the season roster and approve the next stage.' if r['review'] else '')
                    return
                make_child(store,e,slots,'qualification')
            elif r['phase']=='division':
                if d['mode']=='progressive':make_child(store,e,r['groups'][r['bucket']]+r['incoming'],'division',r['bucket'])
                else:
                    for i,g in enumerate(r['groups']):make_child(store,e,g,'division',i)
            elif r['phase']=='championship':make_child(store,e,r['finalists'],'championship')
            elif r['phase']=='playoff':
                task=r['resolution']['tasks'][0];make_child(store,e,task['slots'],'playoff')
            save(store,e);return
        pending=[c for c in children if c['state']!='completed']
        if pending:
            bad=next((c for c in pending if c['dependency'] or c['activated']),None)
            if bad:events.hold(store,bad['dependency'] or bad['note'] or 'Current stage needs attention.');return
            for c in pending:
                store.db.execute("UPDATE tournaments SET state='running',started_once=1,note='' WHERE id=?",(c['tid'],))
                store.db.execute('UPDATE event_children SET activated=1 WHERE tid=?',(c['tid'],))
            save(store,e,active_tid=pending[0]['tid']);return
        tables=[table(store,c) for c in children]
        r['offset']=max(events.opening_end(store,c['tid']) for c in children)
        for c in children:
            key=store.tournament(c['tid'])['settings']['season_opening_key']
            r.setdefault('book_offsets',{})[key]=max(r.get('book_offsets',{}).get(key,0),events.opening_end(store,c['tid']))
        decision={'stage':e['stage']+1,'season':r['season'],'phase':r['phase'],'standings':tables,'qualified':[],
                  'labels':[store.tournament(c['tid'])['settings']['event_context']['label'] for c in children],
                  'before':r.pop('checkpoint'),'policy':'Complete opening pairs; '+('played boundary playoffs' if d['tie_policy']=='playoff' else 'configured standings tiebreaks, then recorded seed')}
        if r['phase']=='playoff':
            resolution=r['resolution'];task=resolution['tasks'].pop(0);ranked=tables[0]
            # Reorder the original standings without adding playoff points to
            # regular points, ratings, or other divisions.
            original={v['slot']:v for v in resolution['tables'][task['table']]}
            resolution['tables'][task['table']][task['start']:task['start']+len(ranked)]=[original[v['slot']] for v in ranked]
            for i,row in enumerate(resolution['tables'][task['table']]):row['rank']=i+1
            again=boundary_ties(ranked,task['cuts'])
            for item in again:item.update(start=item['start']+task['start'],table=task['table'])
            resolution['tasks']=again+resolution['tasks']
            decision['qualified']=[v['slot'] for v in ranked]
            if not resolution['tasks']:
                r['phase']=resolution['phase'];resolved=resolution['tables'];del r['resolution'];advance(b,resolved,decision)
        elif r['phase']=='championship':
            from .knockout_results import read
            final=store.tournament(children[0]['tid']);result=read(store,final['id'],final['settings'])
            winner=result['champion_slot']
            if winner is None:raise ValueError('Completed championship has no winner.')
            slot=final['settings']['event_context']['slots'][winner]
            decision.update(champion=store.participant(final['id'],winner)['name'],champion_slot=slot,championship={'tid':final['id'],'state':'completed','matches':result['rounds'][0]['matches'],'games':final['total']})
            finish_season(b,decision)
        else:
            tasks=[]
            if d['tie_policy']=='playoff':
                for i,rows in enumerate(tables):
                    bucket=r['bucket'] if d['mode']=='progressive' else i
                    for task in boundary_ties(rows,cuts_for(d,r,bucket,rows)):task['table']=i;tasks.append(task)
            if tasks:
                r['resolution']={'phase':r['phase'],'tables':tables,'tasks':tasks,'key':'qualification' if r['phase']=='qualification' else str(r['bucket'] if d['mode']=='progressive' else 0)}
                r['phase']='playoff'
            else:advance(b,tables,decision)
        decision['after']=checkpoint(b)
        store.db.execute('INSERT OR REPLACE INTO event_decisions VALUES(?,?,?)',(eid,e['stage'],encode(decision)))
        state='completed' if r['phase']=='completed' else 'paused' if r['review'] else 'running'
        save(store,e,stage=e['stage']+1,state=state,active_tid=None,note='All scheduled seasons completed.' if state=='completed' else 'Review the season roster and approve the next stage.' if r['review'] else '')


def advance(body,tables,decision):
    r=body['season_state'];d=body['definition'];phase=r['phase']
    if phase=='qualification':
        order=[v['slot'] for v in tables[0]]
        if admission.enabled(d):admission.place(body,order,decision)
        else:
            r['groups']=[order[sum(d['sizes'][:i]):sum(d['sizes'][:i+1])] for i in range(len(d['sizes']))]
            r['phase']='division';r['season_start']=True;decision['qualified']=order;decision['placements']=copy.deepcopy(r['groups'])
    elif d['mode']=='progressive':
        i=r['bucket'];ranked=[v['slot'] for v in tables[0]];up=d['movement'][i-1] if i else 0;down=d['movement'][i] if i<len(r['groups'])-1 else 0
        if admission.enabled(d):r.setdefault('division_rankings',{})[str(i)]=ranked
        retained=ranked[up:len(ranked)-down if down else len(ranked)]
        r['next_groups'][i]=retained
        if down:r['next_groups'][i+1].extend(ranked[-down:])
        decision['qualified']=ranked[:up];r['incoming']=ranked[:up]
        if i:r['bucket']-=1
        else:r['finalists']=ranked[:2];r['regular_winner']=tables[0][0]['name'];end_divisions(body,decision)
    else:
        r['next_groups']=[[] for _ in tables];movement=[]
        for i,rows in enumerate(tables):
            up=d['movement'][i-1] if i else 0;down=d['movement'][i] if i<len(tables)-1 else 0
            for j,row in enumerate(rows):
                to=i-1 if j<up else i+1 if down and j>=len(rows)-down else i
                r['next_groups'][to].append(row['slot'])
                if to!=i:movement.append({'slot':row['slot'],'name':row['name'],'from':i,'to':to,'outcome':'Promoted' if to<i else 'Relegated'})
        decision['movement']=movement;r['finalists']=[v['slot'] for v in tables[0][:2]];r['regular_winner']=tables[0][0]['name'];end_divisions(body,decision)
    if r['phase']!='completed':
        r['review']=d['review_policy']=='stage' or (r['season_start'] and d['review_policy']=='season')


def end_divisions(body,decision):
    r=body['season_state'];decision['regular_winner']=r['regular_winner'];decision['next_groups']=copy.deepcopy(r['next_groups'])
    if body['definition']['championship']['enabled']:r['phase']='championship';r['season_start']=False
    else:decision['champion']=r['regular_winner'];finish_season(body,decision)


def finish_season(body,decision):
    r=body['season_state'];d=body['definition'];decision['next_groups']=copy.deepcopy(r['next_groups'])
    if admission.enabled(d) and d['mode']=='progressive':
        order={}
        for bucket,slots in sorted(r.pop('division_rankings',{}).items(),key=lambda item:-int(item[0])):
            order.update({s:(int(bucket),i) for i,s in enumerate(slots)})
        r['next_groups']=[sorted(g,key=lambda s:order[s]) for g in r['next_groups']]
        decision['next_groups']=copy.deepcopy(r['next_groups'])
    r['history'].append({'season':r['season'],'champion':decision.get('champion'),'regular_winner':r['regular_winner'],'groups':copy.deepcopy(r['next_groups'])})
    r.update(groups=copy.deepcopy(r['next_groups']),incoming=[],next_groups=[[] for _ in r['groups']],bucket=len(r['groups'])-1 if d['mode']=='progressive' else 0,season_start=True)
    if r['season']>=d['seasons']:r.update(phase='completed',review=False)
    else:
        r.update(season=r['season']+1,phase='division',review=d['review_policy'] in ('season','stage'))
        if admission.enabled(d):admission.begin(body)


def review(store,eid,revision,replacements=None,groups=None,approve=False,dry_run=False,candidates=None):
    e=events.get(store,eid);b=e['body'];r=b['season_state'];d=b['definition']
    if type(revision) is not int or revision!=e['revision']:raise ValueError('This event changed. Refresh before trying again.')
    if e['state'] in ('running','retired') or not r['review']:raise ValueError('Roster changes require a scheduled review window.')
    if store.one("SELECT 1 FROM event_children c JOIN tournaments t ON t.id=c.tid WHERE c.eid=? AND (t.state IN ('running','draining') OR (c.valid=1 AND c.stage=?)) LIMIT 1",(eid,e['stage'])):
        raise ValueError('Finish and drain the current stage before changing the roster.')
    allowed=d['update_policy']=='stage' or (d['update_policy']=='season' and r['season_start'])
    before_total=remaining_minimum(store,b);changes=[];new_slots={};seen=set();appended=[]
    for item in replacements or []:
        slot=item.get('slot');new=item.get('new_entry',False)
        if slot is not None and slot in seen:raise ValueError('Choose each roster place only once.')
        if slot is not None:seen.add(slot)
        if type(new) is not bool:raise ValueError('Choose an engine upgrade or a new entrant.')
        append=slot is None and new
        if append:
            if not r['season_start']:raise ValueError('New entrants require a season boundary.')
            bucket=item.get('division');slot=len(b['profiles'])
            if admission.enabled(d):r['candidates'].append(slot);appended.append(slot)
            else:
                if type(bucket) is not int or not 0<=bucket<len(r['groups']):raise ValueError('Choose a division for the new entrant.')
                r['groups'][bucket].append(slot)
            b['profiles'].append({'name':'New entrant'});b['identities'].append(uid())
        if type(slot) is not int or not 0<=slot<len(b['profiles']):raise ValueError('Choose an existing roster place.')
        if slot not in admission.pool(b):raise ValueError('Engine is not in the current roster.')
        if not allowed and not (new and r['season_start']):raise ValueError('Engine updates are not allowed in this window.')
        if new and not r['season_start']:raise ValueError('New entrants require a season boundary.')
        row=store.one('SELECT body FROM profiles WHERE id=?',(item.get('profile_id'),))
        if not row:raise ValueError('Select a registered engine version.')
        p=json.loads(row['body']);store.validate_profile(p)
        from pathlib import Path
        if p.get('path') and Path(p['path']).is_file() and not p.get('fingerprints'):
            from .fingerprints import capture
            p['fingerprints']=capture(p);p['sha256']=p['fingerprints']['executable']['sha256']
        # An upgrade at the same file path would make older attempts impossible
        # to replay with their recorded binary. Require a versioned installation.
        if p.get('sha256') and store.one("""SELECT 1 FROM participants p JOIN event_children c ON c.tid=p.tid
            WHERE c.eid=? AND lower(json_extract(p.profile,'$.path'))=lower(?)
            AND json_extract(p.profile,'$.sha256')<>? LIMIT 1""",(eid,p.get('path',''),p['sha256'])):
            raise ValueError('Install the updated engine in a separate version folder to preserve earlier games.')
        from .fingerprints import verify
        verify(p)
        from .uci import validated_options
        if p.get('advertised'):validated_options(p.get('options',{}),p['advertised'])
        old=copy.deepcopy(b['profiles'][slot]);identity=b['identities'][slot]
        if new:
            if append:target=slot;b['profiles'][slot]=p
            else:target=len(b['profiles']);b['profiles'].append(p);b['identities'].append(uid())
            if not admission.enabled(d):r['groups']=[[target if v==slot else v for v in g] for g in r['groups']]
            if admission.enabled(d):r['candidates']=[target if v==slot else v for v in r['candidates']]
            new_slots[slot]=target
        else:target=slot;b['profiles'][slot]=p
        changes.append({'season':r['season'],'stage':e['stage']+1,'from':old,'to':p,'previous_identity':identity,'identity':b['identities'][target],'slot':target,'new_entry':new,'at':time.time()})
    if groups is not None:
        if admission.enabled(d):raise ValueError('Division places are earned through qualification; edit the candidate pool instead.')
        if not r['season_start']:raise ValueError('Division changes require a season boundary.')
        groups=[[new_slots.get(v,v) for v in g] for g in groups]
        groups_valid(groups,len(b['profiles']),d['movement'])
        if len(groups)!=len(r['groups']):raise ValueError('Keep the division count; create a fresh competition to change its structure.')
        r['groups']=groups;r['next_groups']=[[] for _ in groups]
    groups_valid(r['groups'],len(b['profiles']),d['movement'])
    # Record withdrawals/placements even when there is no executable upgrade.
    if groups is not None:changes.append({'season':r['season'],'stage':e['stage']+1,'from':{'name':'Division assignments'},'to':{'name':'Division assignments'},'groups':copy.deepcopy(groups),'at':time.time()})
    if admission.enabled(d):
        if candidates is not None:
            if not r['season_start']:raise ValueError('Candidate changes require a season boundary.')
            admission.validate_pool(b,candidates+appended if isinstance(candidates,list) else candidates)
            r['candidates']=[new_slots.get(s,s) for s in candidates]+appended
            changes.append({'season':r['season'],'stage':e['stage']+1,'from':{'name':'Candidate pool'},'to':{'name':'Candidate pool'},'candidates':r['candidates'][:],'at':time.time()})
        admission.validate_pool(b,r['candidates'])
        if r['season_start']:admission.begin(b)
    elif r['phase']=='qualification':d['sizes']=list(map(len,r['groups']))
    b['regular_games']+=remaining_minimum(store,b)-before_total
    if b['regular_games']>9223372036854775807:raise ValueError('Event exceeds 64-bit game numbering capacity.')
    if approve:
        from .fingerprints import verify
        for slot in admission.pool(b):verify(b['profiles'][slot])
        r['review']=False;r['season_start']=False
    b['updates'].extend(changes)
    if dry_run:return {'ok':True}
    with store.tx():save(store,e,note='Roster approved. Run event to continue.' if approve else 'Roster changes saved. Review before approving.')
    return events.detail(store,eid)


def replacement(store,m,invalidate,apply):
    e=events.get(store,m['eid']);later=bool(store.one('SELECT 1 FROM event_decisions WHERE eid=? AND stage>=? LIMIT 1',(m['eid'],m['stage'])))
    if later and not invalidate:return True
    if apply:
        saved=store.one('SELECT body FROM event_decisions WHERE eid=? AND stage=?',(m['eid'],m['stage']))
        if saved:
            decision=json.loads(saved['body']);e['body'].update(copy.deepcopy(decision['before']));e['body']['season_state']['checkpoint']=copy.deepcopy(decision['before'])
        store.audit(m['tid'],'season_decisions_invalidated',{'event':m['eid'],'decisions':store.rows('SELECT * FROM event_decisions WHERE eid=? AND stage>=?',(m['eid'],m['stage']))})
        store.db.execute('UPDATE event_children SET valid=0 WHERE eid=? AND stage>?',(m['eid'],m['stage']))
        store.db.execute('UPDATE event_children SET activated=0 WHERE eid=? AND stage=?',(m['eid'],m['stage']))
        store.db.execute('DELETE FROM event_decisions WHERE eid=? AND stage>=?',(m['eid'],m['stage']))
        save(store,e,stage=m['stage'],state='paused',active_tid=None,note='Later stages archived. Replay the corrected stage before continuing.')
    return False


def extend(store,e):
    if e['state']!='completed':raise ValueError('Finish the current season before adding another.')
    b=e['body'];d=b['definition'];r=b['season_state'];before=minimum(store,b);d['seasons']+=1
    b['regular_games']+=minimum(store,b)-before
    r.update(season=r['season']+1,phase='division',review=True,season_start=True)
    if admission.enabled(d):admission.begin(b)
    with store.tx():save(store,e,state='paused',active_tid=None,note='Review the season roster and approve the next stage.')


def clinch(store,t,states):
    """Close only an already-decided regular final, between complete pairs."""
    if not t['settings'].get('season_clinch') or len(states)!=1:return False
    row=states[0];state=json.loads(row['body']);chunks=state.get('chunks',[])
    if len(chunks)!=1 or chunks[0]['phase']!='regular':return False
    chunk=chunks[0];records=store.rows('SELECT g.white,a.result FROM games g JOIN attempts a ON a.id=g.official WHERE g.tid=? AND g.invalid=0',(t['id'],))
    count=len(records);maximum=chunk['count']*2
    if not count or count%2 or count>=maximum:return False
    points=sum(.5 if g['result']=='1/2-1/2' else float((g['result']=='1-0')==(g['white']==chunk['a'])) for g in records)
    if abs(points*2-count)<=maximum-count:return False
    chunk['count']=chunk['materialized']=count//2
    for batch in state.get('schedule_batches',[]):
        batch['count']=batch['done']=count//2;batch['chunks'][0]['count']=count//2
    for span in state['regular_pairs'].values():span[1]=span[0]+count//2
    with store.tx():
        store.db.execute('UPDATE round_state SET body=? WHERE tid=? AND round=?',(encode(state),t['id'],row['round']))
        store.db.execute('UPDATE tournaments SET total=?,cursor=? WHERE id=?',(count,count//2,t['id']))
        store.audit(t['id'],'championship_clinched',{'planned_games':maximum,'played_games':count,'points':points})
    return True
