"""Custom season circuits: immutable played stages and transactional advancement.

Linear stages may contain parallel groups. Conditions are content-addressed once
per competition; checkpoints contain references, never copies of opening books.
"""
import copy
import hashlib
import json
import math
import random
import time
from . import events
from .store import encode, uid


def initialize(store):
    store.db.execute('CREATE TABLE IF NOT EXISTS competition_templates(id TEXT PRIMARY KEY,name TEXT NOT NULL,body TEXT NOT NULL,created REAL NOT NULL)')


def num(value, label, minimum=1):
    return events.integer(value, label, minimum)


def snapshot(store, tid):
    from .tournament_edit import original_openings
    s=copy.deepcopy(store.tournament(tid)['settings']);s['openings']=original_openings(s)
    for k in ('event_context','event_opening_offset','custom_matchups','ko_round_games','season_clinch'):
        s.pop(k,None)
    return s


def intern(conditions, settings):
    key=hashlib.sha256(encode(settings).encode()).hexdigest();conditions[key]=settings;return key


def group_sizes(n, count):
    num(count,'Groups')
    if count>n//2:raise ValueError('Each stage group needs at least two entrants.')
    return [n//count+(i<n%count) for i in range(count)]


def advance(stage, n):
    if stage['advance_mode']=='percent':return math.ceil(n*stage['advance']/100)
    return stage['advance']


def conditions_for(body, stage):
    s=copy.deepcopy(body['conditions'][stage['condition']])
    s.update(format=stage['format'],cycles=stage['pairs'],rounds=stage['rounds'],paired=True,
             opening_policy='pair',opening_order='shuffle',knockout_tiebreak='continuous',
             playoff_cycles=stage['tiebreak_pairs'],seeding='input',
             schedule_order=body['definition']['schedule_order'],schedule_seed=body['definition']['seed'])
    if stage.get('time_control'):s['time_control']=stage['time_control']
    s.update(stage.get('adjudication',{}))
    if stage.get('tiebreak_control'):s['playoff_controls']=[stage['tiebreak_control']]
    else:s['playoff_controls']=[]
    return s


def validate_definition(store, body, definition, imported=False):
    from .models import TimeControl
    from .tournament_queue import validate_resources
    d=copy.deepcopy(definition);d['kind']='circuit'
    num(d.setdefault('seasons',1),'Seasons');num(d.setdefault('seed',7970),'Seed',0)
    if d['seed']>2147483647:raise ValueError('Seed must fit a signed 32-bit integer.')
    if d.setdefault('review_policy','stage') not in ('automatic','stage','season'):raise ValueError('Choose a review policy.')
    if d.setdefault('schedule_order','balanced') not in ('balanced','matchup','shuffle'):raise ValueError('Choose a scheduling order.')
    d['resources']=validate_resources(d.get('resources',{}))
    stages=d.get('stages')
    if not isinstance(stages,list) or not stages:raise ValueError('Add at least one competition stage.')
    ids=set()
    for stage in stages:
        if not isinstance(stage,dict):raise ValueError('Invalid competition stage.')
        stage.setdefault('id',uid());key=stage['id']
        if not isinstance(key,str) or not key or key in ids:raise ValueError('Stage identifiers must be distinct.')
        ids.add(key)
        if not isinstance(stage.get('name'),str) or not stage['name'].strip():raise ValueError('Name every stage.')
        stage['name']=stage['name'].strip()
        if stage.get('format') not in ('round_robin','swiss','knockout'):raise ValueError('Choose round robin, Swiss or knockout for each stage.')
        for k,default in [('groups',1),('pairs',1),('rounds',5),('tiebreak_pairs',1),('advance',1)]:num(stage.setdefault(k,default),k)
        if stage.setdefault('advance_mode','count') not in ('count','percent'):raise ValueError('Choose a count or percentage for advancement.')
        if stage['advance_mode']=='percent' and stage['advance']>100:raise ValueError('Advancement percentage must be between 1 and 100.')
        if stage['format']=='knockout' and (stage['advance_mode']!='count' or stage['advance']!=1):
            raise ValueError('Each knockout group advances its winner. Use several groups for several qualifiers.')
        if stage.setdefault('seeding','balanced') not in ('balanced','consecutive','shuffle'):raise ValueError('Choose a group seeding method.')
        if stage.setdefault('ties','playoff') not in ('playoff','standings'):raise ValueError('Choose how advancement ties are resolved.')
        for k in ('time_control','tiebreak_control'):
            if stage.get(k):TimeControl.parse(stage[k])
        adj=stage.setdefault('adjudication',{})
        if not isinstance(adj,dict) or set(adj)-{'resign_cp','resign_plies','draw_cp','draw_plies','draw_after','max_plies'}:
            raise ValueError('Invalid stage adjudication settings.')
        for k,v in adj.items():
            if k in ('resign_cp','draw_cp'):
                if type(v) not in (int,float) or not math.isfinite(v) or v<0:raise ValueError('Adjudication thresholds must be finite, non-negative centipawn values.')
            else:num(v,k,1 if k in ('resign_plies','draw_plies') else 0)
        # Conditions from an existing event/template are trusted only by content
        # identity already present in this event's immutable snapshot collection.
        if stage.get('source_tid') and not imported:
            s=snapshot(store,stage['source_tid']);stage['condition']=intern(body['conditions'],s)
            stage['source_name']=store.tournament(stage['source_tid'])['name'];stage['common_control']=True
            stage.pop('source_tid')
        elif not stage.get('condition'):
            stage['condition']=body['default_condition'];stage['source_name']=body['source_name']
        if stage['condition'] not in body['conditions']:raise ValueError('Stage conditions are no longer available. Select a saved setup.')
    last=stages[-1]
    if last['groups']!=1 or last['advance_mode']!='count' or last['advance']!=1:
        raise ValueError('The final stage must have one group and crown one winner.')
    body['definition']=d
    return d


def forecast(store, body, n=None, start=0):
    n=len(body['profiles']) if n is None else n;rows=[]
    for i,stage in enumerate(body['definition']['stages'][start:],start):
        sizes=group_sizes(n,stage['groups']);counts=[advance(stage,v) for v in sizes]
        if any(a>v for a,v in zip(counts,sizes)):raise ValueError('Advancement count exceeds the entrants in a group: '+stage['name'])
        if stage['format']=='swiss' and stage['rounds']>min(sizes)-1:raise ValueError('Swiss rounds exceed possible opponents: '+stage['name'])
        s=conditions_for(body,stage);openings=s.pop('openings');games=0
        # Count mathematically by group size; profiles are only copied when a
        # real group is materialized. Do not construct thousands of games here.
        for size in sizes:
            games+=size*(size-1)*stage['pairs'] if stage['format']=='round_robin' else (size//2)*stage['rounds']*2*stage['pairs'] if stage['format']=='swiss' else (size-1)*2*stage['pairs']
        largest=max(sizes)
        positions=(largest*(largest-1)*stage['pairs']//2 if stage['format']=='round_robin' else largest//2*stage['rounds']*stage['pairs'] if stage['format']=='swiss' else (largest-1)*stage['pairs'])
        available=len(openings)
        rows.append(dict(index=i,id=stage['id'],name=stage['name'],format=stage['format'],entrants=n,groups=sizes,
            advances=counts,output=sum(counts),games=games,time_control=s['time_control'],book=s.get('opening_source',{}).get('name',''),
            opening_positions=available,opening_pairs=positions,condition=stage['condition'],
            profile_controls=not(stage.get('time_control') or stage.get('common_control')) and any(p.get('time_control') for p in body['profiles']),
            seeding=stage['seeding'],ties=stage['ties'],pairs=stage['pairs'],rounds=stage['rounds'],
            tiebreak_pairs=stage['tiebreak_pairs'],tiebreak_control=stage.get('tiebreak_control'),
            resign_cp=s['resign_cp'],resign_plies=s['resign_plies'],draw_cp=s['draw_cp'],draw_plies=s['draw_plies'],draw_after=s['draw_after']))
        n=sum(counts)
    return rows


def prepare(store, source_tid, definition):
    t=store.tournament(source_tid);s=snapshot(store,source_tid)
    profiles=[json.loads(r['profile']) for r in store.rows('SELECT profile FROM participants WHERE tid=? ORDER BY slot',(source_tid,))]
    body=dict(profiles=profiles,identities=[uid() for _ in profiles],settings=s,source_name=t['name'],conditions={},updates=[])
    body['default_condition']=intern(body['conditions'],s)
    definition=copy.deepcopy(definition)
    template_id=definition.pop('template_id',None)
    if template_id:
        row=store.one('SELECT body FROM competition_templates WHERE id=?',(template_id,))
        if not row:raise ValueError('Competition template not found.')
        saved=json.loads(row['body']);body['conditions'].update(saved['conditions'])
        definition.setdefault('stages',saved['definition']['stages'])
    validate_definition(store,body,definition)
    reset(body);refresh_forecast(store,body)
    return body,body['regular_games']


def reset(body):
    body['circuit_state']=dict(season=1,index=0,review=True,incoming=list(range(len(body['profiles']))),
        book_offsets={},history=[],resolution=None)


def refresh_forecast(store,body):
    r=body['circuit_state'];d=body['definition']
    body['preview']=forecast(store,body)
    remaining=forecast(store,body,len(r['incoming']),r['index']) if r['season']<=d['seasons'] else []
    done=sum(h['base_games'] for h in r['history'])
    body['regular_games']=done+sum(v['games'] for v in remaining)+max(0,d['seasons']-r['season'])*sum(v['games'] for v in body['preview'])
    if body['regular_games']>9223372036854775807:raise ValueError('Event exceeds 64-bit game numbering capacity.')
    # Parallel groups share their stage's opening sequence for equal conditions;
    # the next stage advances beyond the longest group, including tiebreaks.
    usage={}
    for row in body['preview']:
        s=body['conditions'][row['condition']];key=book_key(s)
        u=usage.setdefault(key,{'available':row['opening_positions'],'needed':0,'book':row['book']})
        u['needed']+=row['opening_pairs']*d['seasons']
    body['opening_plan']=list(usage.values())


def book_key(s):
    return hashlib.sha256(encode([s['openings'],s['seed'],s['chess960']]).encode()).hexdigest()


def groups_for(body):
    r=body['circuit_state'];stage=body['definition']['stages'][r['index']];slots=r['incoming'][:]
    sizes=group_sizes(len(slots),stage['groups']);groups=[[] for _ in sizes]
    if stage['seeding']=='shuffle':random.Random(body['definition']['seed']+r['season']*1000003+r['index']).shuffle(slots)
    if stage['seeding']=='consecutive':
        start=0
        for i,size in enumerate(sizes):groups[i]=slots[start:start+size];start+=size
    else:
        start=0;reverse=False
        while start<len(slots):
            order=range(len(groups)-1,-1,-1) if reverse and stage['seeding']=='balanced' else range(len(groups))
            for i in order:
                if len(groups[i])<sizes[i] and start<len(slots):groups[i].append(slots[start]);start+=1
            reverse=not reverse
    return groups


def child_label(context,bucket,definition,main_groups=None):
    """Distinguish archived and new playoff records without rewriting results."""
    index=context.get('circuit_index')
    if context.get('role')!='playoff' or index is None:
        return context.get('label','')
    config=definition['stages'][index];task=context.get('task') or {}
    count=config['groups'] if main_groups is None else main_groups
    group=f" — Group {task['table']+1}" if count>1 and 'table' in task else ''
    base=context.get('label',config['name']).split(' — Placement playoff')[0]
    if ' — Group ' in base:base=base.rsplit(' — Group ',1)[0]
    return base+group+f" — Placement playoff {max(1,bucket-count+1)}"


def make_child(store,e,slots,bucket,role='circuit',task=None):
    b=e['body'];r=b['circuit_state'];stage=b['definition']['stages'][r['index']]
    s=conditions_for(b,stage);op=s.pop('openings');key=book_key(b['conditions'][stage['condition']])
    if role=='playoff':
        s.update(format='round_robin',cycles=stage['tiebreak_pairs'])
        if stage.get('tiebreak_control'):s['time_control']=stage['tiebreak_control']
    profiles=[copy.deepcopy(b['profiles'][v]) for v in slots]
    if stage.get('time_control') or stage.get('common_control') or role=='playoff' and stage.get('tiebreak_control'):
        for p in profiles:p.pop('time_control',None)
    p,s,total=store.prepare_tournament(profiles,s,op)
    start=r['book_offsets'].get(key,0) if role=='playoff' else r['checkpoint']['runtime']['book_offsets'].get(key,0)
    r['book_offsets'][key]=max(r['book_offsets'].get(key,0),start+total//2)
    label=child_label(dict(role=role,circuit_index=r['index'],task=task),bucket,b['definition']) if role=='playoff' else stage['name']+(f' — Group {bucket+1}' if stage['groups']>1 else '')
    actual_role='championship' if r['index']==len(b['definition']['stages'])-1 and role!='playoff' else role
    s.update(event_opening_offset=start,event_context=dict(id=e['id'],name=e['name'],season=r['season'],stage=e['stage']+1,
        label=label,slots=slots,role=actual_role,base_games=total,identities=[b['identities'][v] for v in slots],
        circuit_index=r['index'],book_key=key,task=task))
    tid=store.insert_tournament(e['name']+f" — Season {r['season']} — "+label,(p,s,total))
    store.db.execute('INSERT INTO event_children(tid,eid,stage,bucket,role) VALUES(?,?,?,?,?)',(tid,e['id'],e['stage'],bucket,actual_role))
    return tid


def table(store,c):
    from .seasons import table as regular
    t=store.tournament(c['tid']);rows=regular(store,c)
    if t['settings']['format']=='knockout':
        from .knockout_results import read
        bracket=read(store,c['tid'],t['settings']);slots=t['settings']['event_context']['slots']
        if bracket['champion_slot'] is None:raise ValueError('Completed knockout has no winner.')
        order={slots[v]:i for i,v in enumerate(bracket['order'])};rows.sort(key=lambda v:order[v['slot']])
        for row in rows:row['rank']=bracket['people'][slots.index(row['slot'])]['ko_finish']
    return rows


def save(store,e,**values):
    events.change(store,e['id'],body=encode(e['body']),**values)


def tick(store,e):
    from .seasons import boundary_ties
    b=e['body'];r=b['circuit_state'];d=b['definition'];eid=e['id'];stage=d['stages'][r['index']]
    if r['review']:events.hold(store,'Review the competition plan and approve the next stage.');return
    children=store.rows('SELECT c.*,t.state,t.dependency,t.note FROM event_children c JOIN tournaments t ON t.id=c.tid WHERE c.eid=? AND c.valid=1 AND c.stage=? ORDER BY c.bucket',(eid,e['stage']))
    with store.tx():
        if not children:
            r['checkpoint']=dict(runtime=copy.deepcopy({k:v for k,v in r.items() if k!='checkpoint'}),definition=copy.deepcopy(d))
            for i,slots in enumerate(groups_for(b)):make_child(store,e,slots,i)
            save(store,e,note='Stage groups prepared.');return
        pending=[c for c in children if c['state']!='completed']
        if pending:
            bad=next((c for c in pending if c['dependency'] or c['activated']),None)
            if bad:events.hold(store,bad['dependency'] or bad['note'] or 'A stage needs attention.');return
            for c in pending:
                store.db.execute("UPDATE tournaments SET state='running',started_once=1,note='' WHERE id=?",(c['tid'],))
                store.db.execute('UPDATE event_children SET activated=1 WHERE tid=?',(c['tid'],))
                store.audit(c['tid'],'state',{'state':'running','source':'event','event':eid})
            save(store,e,active_tid=pending[0]['tid'],note='');return
        for c in children:
            ctx=store.tournament(c['tid'])['settings']['event_context'];key=ctx['book_key']
            r['book_offsets'][key]=max(r['book_offsets'].get(key,0),events.opening_end(store,c['tid']))
        main=[c for c in children if c['role']!='playoff']
        if r['resolution'] is None:
            tables=[table(store,c) for c in main];tasks=[]
            if stage['ties']=='playoff' and stage['format']!='knockout':
                for i,rows in enumerate(tables):
                    for task in boundary_ties(rows,[advance(stage,len(rows))]):tasks.append(dict(task,table=i))
            r['resolution']=dict(tables=tables,tasks=tasks,pending=None,rounds=[])
        res=r['resolution']
        if res['pending']:
            task=res['tasks'].pop(0);played=table(store,{'tid':res['pending']});original=res['tables'][task['table']]
            lookup={row['slot']:row for row in original}
            original[task['start']:task['start']+len(played)]=[lookup[row['slot']] for row in played]
            res['rounds'].append({'tid':res['pending'],'order':[v['slot'] for v in played]})
            sub=[dict(t,start=t['start']+task['start'],table=task['table']) for t in boundary_ties(played,task['cuts'])]
            res['tasks']=sub+res['tasks'];res['pending']=None
        if res['tasks']:
            task=res['tasks'][0]
            used={v['tid'] for v in res['rounds']}
            existing=next((c for c in children if c['role']=='playoff' and c['tid'] not in used),None)
            if existing:
                ctx=store.tournament(existing['tid'])['settings']['event_context']
                if ctx['task']!=task:raise ValueError('Placement playoff dependencies require review.')
                res['pending']=existing['tid']
            else:res['pending']=make_child(store,e,task['slots'],max(c['bucket'] for c in children)+1,'playoff',task)
            save(store,e,active_tid=None,note='Placement tie: additional opening pairs are required.');return
        tables=res['tables'];selected=[]
        for i in range(max(advance(stage,len(rows)) for rows in tables)):
            for rows in tables:
                if i<advance(stage,len(rows)):selected.append(rows[i]['slot'])
        for rows in tables:
            if stage['format']!='knockout':
                for i,row in enumerate(rows):row['rank']=i+1
        decision=dict(stage=e['stage']+1,season=r['season'],phase='circuit',index=r['index'],labels=[stage['name']],
            config=copy.deepcopy(stage),standings=tables,qualified=selected,playoffs=res['rounds'],before=r['checkpoint'],
            policy='Group places interleaved by rank; no comparison of raw points across groups.')
        conditions=conditions_for(b,stage)
        decision['conditions']={k:conditions[k] for k in ('time_control','opening_source','seed','resign_cp','resign_plies','draw_cp','draw_plies','draw_after','max_plies','playoff_controls') if k in conditions}
        decision['conditions']['profile_controls']=not(stage.get('time_control') or stage.get('common_control')) and any(p.get('time_control') for p in b['profiles'])
        r['history'].append(dict(stage=e['stage'],season=r['season'],index=r['index'],base_games=sum(store.tournament(c['tid'])['settings']['event_context']['base_games'] for c in main)))
        if r['index']==len(d['stages'])-1:
            decision.update(champion=b['profiles'][selected[0]]['name'],champion_slot=selected[0])
            r['season']+=1;r['index']=0;r['incoming']=list(range(len(b['profiles'])))
        else:r['index']+=1;r['incoming']=selected
        r['resolution']=None;r.pop('checkpoint',None)
        finished=r['season']>d['seasons'];r['review']=not finished and (d['review_policy']=='stage' or d['review_policy']=='season' and r['index']==0)
        store.db.execute('INSERT INTO event_decisions VALUES(?,?,?)',(eid,e['stage'],encode(decision)))
        store.audit(None,'circuit_advancement',{'event':eid,'stage':e['stage'],'qualified':selected})
        save(store,e,stage=e['stage']+1,active_tid=None,state='completed' if finished else 'paused' if r['review'] else 'running',
             note='All competition seasons completed.' if finished else 'Review the competition plan and approve the next stage.' if r['review'] else '')


def detail(store,e,body):
    r=body['circuit_state'];e['circuit_state']={k:v for k,v in r.items() if k not in ('checkpoint','resolution')}
    e['preview']=body['preview'];e['unbounded']=True
    e['roster']=[{'slot':i,'identity':body['identities'][i],'name':p['name']} for i,p in enumerate(body['profiles'])]
    started=store.one('SELECT 1 FROM event_children WHERE eid=? AND valid=1 AND stage=?',(e['id'],e['stage']))
    e['editable_from']=r['index']+bool(started) if e['state'] not in ('completed','retired') else len(e['definition']['stages'])
    e['stage_conditions']={v['id']:v for v in body['preview']}
    for row in e['decisions']:row.pop('before',None)
    extra=store.one("SELECT coalesce(sum(CASE WHEN c.role='playoff' THEN t.total ELSE t.total-json_extract(t.settings,'$.event_context.base_games') END),0) n FROM event_children c JOIN tournaments t ON t.id=c.tid WHERE c.eid=? AND c.valid=1",(e['id'],))['n']
    e['scheduled_games']=body['regular_games']+extra
    return e


def checked(store,eid,revision):
    e=events.get(store,eid)
    if e['body']['definition']['kind']!='circuit':raise ValueError('Select a custom competition.')
    if type(revision) is not int or revision!=e['revision']:raise ValueError('This event changed. Refresh before trying again.')
    return e


def approve(store,eid,revision):
    e=checked(store,eid,revision)
    if e['state'] in ('completed','retired') or not e['body']['circuit_state']['review']:raise ValueError('This competition is not waiting for review.')
    from .fingerprints import verify
    for p in e['body']['profiles']:verify(p)
    e['body']['circuit_state']['review']=False
    with store.tx():save(store,e,note='Competition plan approved. Run event to continue.')
    return events.detail(store,eid)


def edit(store,eid,revision,definition,preview=False):
    e=checked(store,eid,revision);b=e['body'];r=b['circuit_state']
    if e['state'] in ('running','completed','retired') or store.one("SELECT 1 FROM tournaments t JOIN event_children c ON c.tid=t.id WHERE c.eid=? AND t.state IN ('running','draining')",(eid,)):
        raise ValueError('Pause and drain the competition before editing future stages.')
    old=copy.deepcopy(b['definition']);locked=events.detail(store,eid)['editable_from']
    validate_definition(store,b,definition)
    if b['definition']['stages'][:locked]!=old['stages'][:locked] or len(b['definition']['stages'])<=r['index']:
        raise ValueError('Started and completed stages in this season are locked.')
    if b['definition']['seasons']<r['season']:raise ValueError('Cannot remove a started season.')
    if b['definition']['seed']!=old['seed'] or b['definition']['schedule_order']!=old['schedule_order']:
        raise ValueError('The recorded competition seed and scheduling order are locked.')
    refresh_forecast(store,b)
    if preview:return {'regular_games':b['regular_games'],'preview':b['preview'],'opening_plan':b['opening_plan'],'editable_from':locked}
    r['review']=True
    with store.tx():
        store.audit(None,'circuit_future_edited',{'event':eid,'before':old,'after':b['definition']})
        save(store,e,resources=encode(b['definition']['resources']),note='Future stages updated. Review and approve before continuing.')
    return events.detail(store,eid)


def replacement(store,m,invalidate,apply):
    e=events.get(store,m['eid']);b=e['body']
    saved=store.one('SELECT body FROM event_decisions WHERE eid=? AND stage=?',(m['eid'],m['stage']))
    # Main-stage changes invalidate placement playoffs at the same stage too.
    dependent=bool(saved or store.one("SELECT 1 FROM event_children WHERE eid=? AND valid=1 AND (stage>? OR (stage=? AND role='playoff' AND tid<>?))",(m['eid'],m['stage'],m['stage'],m['tid'])))
    if dependent and not invalidate:return True
    if apply:
        checkpoint=json.loads(saved['body'])['before'] if saved else b['circuit_state'].get('checkpoint')
        if not checkpoint:raise ValueError('The stage recovery checkpoint is unavailable.')
        store.audit(m['tid'],'circuit_decisions_invalidated',{'event':m['eid'],'decisions':store.rows('SELECT * FROM event_decisions WHERE eid=? AND stage>=?',(m['eid'],m['stage']))})
        b['definition']=copy.deepcopy(checkpoint['definition']);b['circuit_state']=copy.deepcopy(checkpoint['runtime']);b['circuit_state']['checkpoint']=copy.deepcopy(checkpoint)
        # Recompute placement playoffs from their parent main results; an
        # explicit playoff replacement keeps that playoff and its prior task.
        store.db.execute("UPDATE event_children SET valid=0 WHERE eid=? AND (stage>? OR (stage=? AND role='playoff' AND (?<>'playoff' OR bucket>?)))",(m['eid'],m['stage'],m['stage'],m['role'],m['bucket']))
        store.db.execute('UPDATE event_children SET activated=0 WHERE eid=? AND valid=1 AND stage=?',(m['eid'],m['stage']))
        store.db.execute('DELETE FROM event_decisions WHERE eid=? AND stage>=?',(m['eid'],m['stage']))
        b['circuit_state']['review']=False;refresh_forecast(store,b)
        save(store,e,stage=m['stage'],state='paused',active_tid=None,note='Dependent stages archived. Replay the corrected stage before continuing.')
    return False


def templates(store,body=None):
    if body is None:return store.rows('SELECT id,name,created FROM competition_templates ORDER BY name,id')
    action=body.get('action')
    if action=='load':
        row=store.one('SELECT * FROM competition_templates WHERE id=?',(body.get('id'),))
        if not row:raise ValueError('Competition template not found.')
        data=json.loads(row['body']);return dict(id=row['id'],name=row['name'],definition=data['definition'])
    if action=='delete':
        with store.tx():store.db.execute('DELETE FROM competition_templates WHERE id=?',(body.get('id'),))
        return {'ok':True}
    if action!='save':raise ValueError('Unknown template action.')
    e=events.get(store,body.get('event_id'));b=e['body']
    if b['definition']['kind']!='circuit':raise ValueError('Select a custom competition.')
    name=str(body.get('name','')).strip()
    if not name:raise ValueError('Name the competition template.')
    key=uid()
    with store.tx():store.db.execute('INSERT INTO competition_templates VALUES(?,?,?,?)',(key,name,encode({'definition':b['definition'],'conditions':b['conditions']}),time.time()))
    return {'id':key,'name':name}
