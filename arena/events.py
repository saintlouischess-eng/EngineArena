"""Durable events composed of normal tournaments, with audited advancement.

An event never merges stage ratings. Each child owns games, opening pairs and
statistics. Advancement and child creation commit together. Superseded children
remain inspectable after an explicit correction, but cannot resume play.
"""
import copy
import json
import random
import time
from .models import TimeControl


def initialize(store):
    store.db.executescript('''
    CREATE TABLE IF NOT EXISTS events(id TEXT PRIMARY KEY,name TEXT NOT NULL,body TEXT NOT NULL,
      state TEXT NOT NULL DEFAULT 'paused',stage INTEGER NOT NULL DEFAULT 0,active_tid TEXT,
      revision INTEGER NOT NULL DEFAULT 0,note TEXT NOT NULL DEFAULT '',created REAL NOT NULL);
    CREATE TABLE IF NOT EXISTS event_children(tid TEXT PRIMARY KEY,eid TEXT NOT NULL,stage INTEGER NOT NULL,
      bucket INTEGER NOT NULL,valid INTEGER NOT NULL DEFAULT 1);
    CREATE INDEX IF NOT EXISTS events_state ON events(state,created);
    CREATE INDEX IF NOT EXISTS event_children_stage ON event_children(eid,valid,stage,bucket);
    CREATE TABLE IF NOT EXISTS event_decisions(eid TEXT NOT NULL,stage INTEGER NOT NULL,body TEXT NOT NULL,
      PRIMARY KEY(eid,stage));
    ''')
    from .circuits import initialize as initialize_circuits
    initialize_circuits(store)
    for table,columns in {'events':{'execution_mode':"TEXT NOT NULL DEFAULT 'sequential'",'resources':"TEXT NOT NULL DEFAULT '{}'"},
            'event_children':{'role':"TEXT NOT NULL DEFAULT 'division'",'activated':'INTEGER NOT NULL DEFAULT 0'}}.items():
        existing={r['name'] for r in store.rows('PRAGMA table_info('+table+')')}
        for name,kind in columns.items():
            if name not in existing:store.db.execute(f'ALTER TABLE {table} ADD COLUMN {name} {kind}')


def get(store,eid):
    e=store.one('SELECT * FROM events WHERE id=?',(eid,))
    if not e:raise ValueError('Event not found.')
    e['body']=json.loads(e['body']);return e


def integer(value,label,minimum=1):
    if type(value) is not int or value<minimum:raise ValueError(label+' must be a positive whole number.')
    return value


def prepare(store,source_tid,definition):
    if definition.get('kind')=='circuit':
        from .circuits import prepare as circuit_prepare
        return circuit_prepare(store,source_tid,definition)
    if definition.get('kind')=='season':
        from .seasons import prepare as season_prepare
        return season_prepare(store,source_tid,definition)
    t=store.tournament(source_tid);s=copy.deepcopy(t['settings']);n=t['participants'];d=copy.deepcopy(definition)
    if d.get('schedule_order','source')!='source':
        from .schedule_order import validate as validate_schedule
        s.update(schedule_order=d['schedule_order'],schedule_seed=d.get('schedule_seed',7970))
        validate_schedule(s)
    if d.get('kind','multistage') not in ('multistage','league'):raise ValueError('Unknown event type.')
    d.setdefault('kind','multistage');groups=d.get('groups')
    if not isinstance(groups,list) or not groups or any(not isinstance(g,list) or len(g)<2 for g in groups):
        raise ValueError('Each group needs at least two engines.')
    flat=[v for group in groups for v in group]
    if any(type(v) is not int for v in flat) or sorted(flat)!=list(range(n)):
        raise ValueError('Assign every participant to exactly one group.')
    if d['kind']=='league':
        from .leagues import validate
        validate(d)
        if d.get('execution_mode')=='parallel':
            from .tournament_queue import validate_resources
            d['resources']=validate_resources(d.get('resources'))
    if d.get('initial_format') not in ('round_robin','swiss'):raise ValueError('Choose round robin or Swiss for the first stage.')
    if d.get('final_format') not in ('knockout','round_robin'):raise ValueError('Choose knockout or round robin for the final stage.')
    advance=integer(d.get('advance',1),'Qualifiers per group')
    if d['kind']=='multistage' and (any(advance>len(g) for g in groups) or advance*len(groups)<2):raise ValueError('The final stage needs at least two qualifiers; the count must fit every group.')
    for k in ('initial_cycles','final_cycles','initial_rounds'):integer(d.get(k,1),k)
    if d.get('final_time_control'):TimeControl.parse(d['final_time_control'])
    d.setdefault('initial_cycles',1);d.setdefault('final_cycles',1);d.setdefault('initial_rounds',5);d['advance']=advance
    from .tournament_edit import original_openings
    s['openings']=original_openings(s)
    if d['kind']=='league' and d.get('season_openings')=='advance':
        from .openings import unique_openings
        s['openings']=unique_openings(s['openings'],s['chess960'])
    for k in ('custom_matchups','ko_round_games','event_context','event_opening_offset'):s.pop(k,None)
    profiles=[json.loads(r['profile']) for r in store.rows('SELECT profile FROM participants WHERE tid=? ORDER BY slot',(source_tid,))]
    body={'definition':d,'profiles':profiles,'settings':s,'source_name':t['name']}
    counts=[prepared_child(store,body,g,0)[2] for g in groups]
    total=sum(counts)
    if d['kind']=='league':
        if d.get('championship',{}).get('enabled'):total+=prepared_child(store,body,groups[0][:2],0,championship=True)[2]
        total*=d['seasons']
        if d.get('season_openings')=='advance':
            per_season=max(counts)//(2 if s['paired'] else 1)+(d['championship']['games']//2 if d.get('championship',{}).get('enabled') else 0)
            body['opening_plan']={'positions_per_season':per_season,'required_minimum':per_season*d['seasons'],
                'available':len(s['openings']),'reuse_expected':per_season*d['seasons']>len(s['openings'])}
    else:total+=prepared_child(store,body,list(range(advance*len(groups))),1)[2]
    if total>9223372036854775807:raise ValueError('Event exceeds 64-bit game numbering capacity.')
    return body,total


def prepared_child(store,body,slots,stage,*,championship=False,opening_offset=0):
    d=body['definition'];s=copy.deepcopy(body['settings']);openings=s.pop('openings')
    final=stage==1 and d['kind']=='multistage'
    s.update(format=d['final_format'] if final else d['initial_format'],cycles=d['final_cycles'] if final else d['initial_cycles'],
             rounds=d['initial_rounds'],knockout_tiebreak='continuous')
    if d['kind']=='league' and d.get('season_openings')=='advance':
        s.update(opening_policy='pair',opening_order='shuffle',event_opening_offset=opening_offset)
    if championship:
        config=d['championship']
        s.update(format='knockout',cycles=config['games']//2,paired=True,seeding='input',
                 playoff_cycles=config['tiebreak_games']//2,playoff_controls=config.get('controls',[]),opening_policy='pair')
    profiles=[copy.deepcopy(body['profiles'][i]) for i in slots]
    if final and d.get('final_time_control'):
        s['time_control']=d['final_time_control']
        for p in profiles:p.pop('time_control',None)
    return store.prepare_tournament(profiles,s,openings)


def create(store,name,source_tid,definition):
    from .store import uid,encode
    name=str(name).strip()
    if not name:raise ValueError('Enter an event name.')
    body,total=prepare(store,source_tid,definition);body['regular_games']=total;eid=uid()
    with store.tx():
        store.db.execute('INSERT INTO events(id,name,body,created,execution_mode,resources) VALUES(?,?,?,?,?,?)',
                         (eid,name,encode(body),time.time(),'parallel' if body['definition']['kind'] in ('season','circuit') else definition.get('execution_mode','sequential') if body['definition']['kind']=='league' else 'sequential',encode(body['definition'].get('resources',{}))))
        store.audit(None,'event_created',{'event':eid,'name':name,'regular_games':total})
    return detail(store,eid)


def child(store,e,slots,stage,bucket,*,championship=False,opening_offset=None):
    from .store import encode
    d=e['body']['definition']
    if opening_offset is None:
        previous=store.one('SELECT body FROM event_decisions WHERE eid=? AND stage=?',(e['id'],stage-1))
        opening_offset=json.loads(previous['body']).get('next_opening_offset',0) if previous else 0
    p,s,total=prepared_child(store,e['body'],slots,stage,championship=championship,opening_offset=opening_offset)
    role='championship' if championship else 'division'
    label=f"Season {stage+1} — "+('Championship final' if championship else d['division_names'][bucket]) if d['kind']=='league' else f'Group {bucket+1}' if stage==0 else 'Final stage'
    s['event_context']={'id':e['id'],'name':e['name'],'stage':stage+1,'label':label,'slots':slots,'role':role,'base_games':total}
    tid=store.insert_tournament(e['name']+' — '+label,(p,s,total))
    store.db.execute('INSERT INTO event_children(tid,eid,stage,bucket,valid,role) VALUES(?,?,?,?,1,?)',(tid,e['id'],stage,bucket,role))
    return tid


def change(store,eid,**values):
    store.db.execute('UPDATE events SET '+','.join([*(k+'=?' for k in values),'revision=revision+1'])+' WHERE id=?',(*values.values(),eid))


def detail(store,eid,offset=0,full=False):
    e=get(store,eid);body=e.pop('body');d=body['definition'];e.update(definition=d,participants=len(body['profiles']),regular_games=body['regular_games'],
        source_name=body['source_name'],unbounded=(d['kind']=='multistage' and d['final_format']=='knockout') or bool(d.get('championship',{}).get('enabled')),time_control=body['settings']['time_control'],tiebreaks=body['settings']['tiebreaks'],
        paired=body['settings']['paired'],opening_source=body['settings'].get('opening_source',{}),opening_positions=len(body['settings']['openings']),
        schedule_order=body['settings'].get('schedule_order','legacy'),schedule_seed=body['settings'].get('schedule_seed',7970))
    e['children']=store.rows('''SELECT c.*,t.name,t.state,t.total,t.note,t.dependency,
      json_extract(t.settings,'$.event_context') display_context,
      coalesce((SELECT sum(n) FROM game_counts WHERE tid=t.id AND invalid=0 AND has_official=1),0) official_games
      FROM event_children c LEFT JOIN tournaments t ON t.id=c.tid WHERE c.eid=? ORDER BY c.stage,c.bucket,c.valid DESC,c.tid LIMIT ? OFFSET ?''',(eid,-1 if full else 50,0 if full else max(0,offset)))
    display_groups={(r['stage'],r['valid']):r['n'] for r in store.rows("SELECT stage,valid,count(*) n FROM event_children WHERE eid=? AND role<>'playoff' GROUP BY stage,valid",(eid,))} if d['kind']=='circuit' else {}
    for child in e['children']:
        context=json.loads(child.pop('display_context') or '{}')
        if context:
            child['season']=context.get('season')
            if d['kind']=='circuit':
                from .circuits import child_label
                child['display_label']=child_label(context,child['bucket'],d,display_groups.get((child['stage'],child['valid'])))
            else:child['display_label']=context.get('label')
    e['child_count']=store.one('SELECT count(*) n FROM event_children WHERE eid=?',(eid,))['n']
    e['official_games']=store.one('''SELECT coalesce(sum(g.n),0) n FROM game_counts g JOIN event_children c ON c.tid=g.tid
      WHERE c.eid=? AND c.valid=1 AND g.invalid=0 AND g.has_official=1''',(eid,))['n']
    e['decisions']=[json.loads(r['body']) for r in store.rows('SELECT body FROM event_decisions WHERE eid=? ORDER BY stage',(eid,))]
    for decision in e['decisions']:
        final=decision.get('championship')
        if final and final['state']!='completed':
            t=store.tournament(final['tid'])
            from .knockout_results import read
            result=read(store,final['tid'],t['settings'])
            final.update(state=t['state'],games=t['total'],matches=[m for r in result['rounds'] for m in r['matches']])
    e['resources']=json.loads(e['resources'])
    e['opening_plan']=body.get('opening_plan');e['opening_seed']=body['settings']['seed']
    e['scheduled_games']=body['regular_games']+store.one('''SELECT coalesce(sum(max(0,t.total-coalesce(json_extract(t.settings,'$.event_context.base_games'),t.total))),0) n
      FROM event_children c JOIN tournaments t ON t.id=c.tid WHERE c.eid=? AND c.valid=1''',(eid,))['n']
    if 'season_state' in body:
        e['scheduled_games']=body['regular_games']+store.one("SELECT coalesce(sum(t.total-coalesce(json_extract(t.settings,'$.event_context.base_games'),t.total)),0) n FROM event_children c JOIN tournaments t ON t.id=c.tid WHERE c.eid=? AND c.valid=1",(eid,))['n']
        e['season_state']={k:v for k,v in body['season_state'].items() if k not in ('checkpoint','resolution')}
        from . import season_admission
        if season_admission.enabled(d):e['admission']=season_admission.summary(body)
        e['roster']=[{'slot':i,'identity':body['identities'][i],'name':p['name'],'version':p.get('identity',{}).get('name',''),'sha256':p.get('sha256'),'path':p.get('path',''),'threads':p.get('threads',1),'hash':p.get('hash',1024)} for i,p in enumerate(body['profiles'])]
        e['updates']=body['updates'];e['unbounded']=e['unbounded'] or body['definition']['tie_policy']=='playoff'
        from .seasons import stage_settings
        keys=(['qualification'] if d['qualifier']['enabled'] else [])+list(map(str,range(len(d['groups']))))+(['championship'] if d['championship']['enabled'] else [])
        e['stage_conditions']={key:{'time_control':v['time_control'],'opening_source':v.get('opening_source',{}),'opening_positions':len(v['openings']),'seed':v['seed'],'max_plies':v['max_plies'],'resign_cp':v['resign_cp'],'draw_cp':v['draw_cp'],'cycles':d['qualifier']['cycles'] if key=='qualification' else d['championship']['games']//2 if key=='championship' else d.get('stage_cycles',{}).get(key,d['cycles'])} for key in keys for v in [stage_settings(body,key)]}
        e['scheduled_games']+=store.one("SELECT coalesce(sum(t.total),0) n FROM event_children c JOIN tournaments t ON t.id=c.tid WHERE c.eid=? AND c.valid=1 AND c.role='playoff'",(eid,))['n']
        if not full:
            for decision in e['decisions']:
                decision.pop('before',None);decision.pop('after',None)
    if 'circuit_state' in body:
        from .circuits import detail as circuit_detail
        circuit_detail(store,e,body)
    return e


def listing(store,offset=0):
    return {'total':store.one('SELECT count(*) n FROM events')['n'],'items':store.rows('SELECT id,name,state,stage,note,revision FROM events ORDER BY created DESC LIMIT 50 OFFSET ?',(max(0,offset),))}


def insights(store,eid,season=None,offset=0,full=False,entry_offsets=None):
    from .event_insights import overview
    return overview(store,eid,season,offset,full,entry_offsets)


def careers(store,eid,search='',offset=0,identity=None,rival_offset=0):
    from .event_insights import careers as read_careers
    return read_careers(store,eid,search,offset,identity,rival_offset)


def command(store,eid,action,revision):
    e=get(store,eid)
    if type(revision) is not int or revision!=e['revision']:raise ValueError('This event changed. Refresh before trying again.')
    if action=='run':
        if (e['body'].get('season_state') or e['body'].get('circuit_state') or {}).get('review'):raise ValueError('Review and approve the roster before running the next stage.')
        if e['state']=='retired':raise ValueError('This event is retired. Create a new event to play again.')
        if e['state']=='completed':raise ValueError('This event has completed.')
        if e['state']=='running':raise ValueError('This event is already running.')
        if store.failure:raise ValueError(store.failure)
        if store.one("SELECT 1 FROM events WHERE state='running' AND id<>?",(eid,)):raise ValueError('Pause the running event first.')
        if store.queue_call('summary')['mode'] in ('running','finish_current'):raise ValueError('Pause the automatic tournament queue first.')
        if store.one("SELECT 1 FROM tournaments WHERE state IN ('running','draining') LIMIT 1"):raise ValueError('Pause and drain running tournaments first.')
        if store.one('SELECT 1 FROM event_children c LEFT JOIN tournaments t ON t.id=c.tid WHERE c.eid=? AND c.valid=1 AND t.id IS NULL LIMIT 1',(eid,)):raise ValueError('An event tournament was deleted. Retire this event or create a new one.')
        with store.tx():
            change(store,eid,state='running',active_tid=None,note='')
            store.db.execute('UPDATE event_children SET activated=0 WHERE eid=? AND valid=1 AND stage=?',(eid,e['stage']))
    elif action=='pause':
        if e['state']!='running':raise ValueError('Only a running event can be paused.')
        with store.tx():
            change(store,eid,state='paused',note='Event paused. Active games drain before further changes.')
            drain(store,eid)
    elif action=='next_season':
        if 'season_state' in e['body']:
            from .seasons import extend
            extend(store,e)
        else:
            from .leagues import extend
            extend(store,e)
    elif action=='retire':
        if e['state']=='running' or store.one("SELECT 1 FROM tournaments t JOIN event_children c ON c.tid=t.id WHERE c.eid=? AND t.state IN ('running','draining')",(eid,)):
            raise ValueError('Pause and drain the event before retiring it.')
        with store.tx():
            change(store,eid,state='retired',active_tid=None,note='Retired. Stage tournaments are retained and may be deleted individually.')
            store.db.execute('UPDATE event_children SET valid=0 WHERE eid=?',(eid,))
    else:raise ValueError('Unknown event action.')
    return detail(store,eid)


def membership(store,tid):
    member=store.one('SELECT c.*,e.state event_state,e.name event_name FROM event_children c JOIN events e ON e.id=c.eid WHERE c.tid=?',(tid,))
    if member:
        member['can_diagnostic_start']=bool(member['event_state']!='running' and
            store.one("SELECT 1 FROM games WHERE tid=? AND invalid=0 AND state='pending' AND mode='diagnostic' LIMIT 1",(tid,)) and
            not store.one("SELECT 1 FROM games WHERE tid=? AND invalid=0 AND state='pending' AND mode<>'diagnostic' LIMIT 1",(tid,)))
    return member


def manual_action(store,tid,action):
    m=membership(store,tid)
    if action=='start':
        if store.one("SELECT 1 FROM events WHERE state='running'"):raise ValueError('Pause the running event first.')
        if m:
            # Diagnostic replay cannot change qualifications or official scores.
            diagnostic=store.one("SELECT 1 FROM games WHERE tid=? AND invalid=0 AND state='pending' AND mode='diagnostic' LIMIT 1",(tid,))
            official=store.one("SELECT 1 FROM games WHERE tid=? AND invalid=0 AND state='pending' AND mode<>'diagnostic' LIMIT 1",(tid,))
            if not diagnostic or official:raise ValueError('This tournament belongs to an event. Use Run event; superseded stages remain archived.')
    if m and action in ('pause','cancel'):
        if m['event_state']=='running':
            with store.tx():
                change(store,m['eid'],state='paused',note='Event paused with its current tournament.')
                drain(store,m['eid'])


def recovery(store):
    store.db.execute("UPDATE events SET state='paused',revision=revision+1,note='Event recovered. Committed results and qualification decisions retained; resume when ready.' WHERE state='running'")


def replacement(store,tid,invalidate,apply=False):
    m=membership(store,tid)
    if not m:return False
    if not m['valid']:raise ValueError('Superseded event stages are archived. Select a current stage.')
    if m['event_state']=='running' or store.one("SELECT 1 FROM tournaments t JOIN event_children c ON c.tid=t.id WHERE c.eid=? AND t.state IN ('running','draining') LIMIT 1",(m['eid'],)):
        raise ValueError('Pause and drain the whole event before replacing a stage result.')
    if 'circuit_state' in get(store,m['eid'])['body']:
        from .circuits import replacement as replace_circuit
        return replace_circuit(store,m,invalidate,apply)
    if 'season_state' in get(store,m['eid'])['body']:
        from .seasons import replacement as replace_season
        return replace_season(store,m,invalidate,apply)
    dependent="(stage>? OR (stage=? AND role='championship' AND ?<>'championship'))"
    args=(m['eid'],m['stage'],m['stage'],m['role'])
    later=bool(store.one('SELECT 1 FROM event_children WHERE eid=? AND valid=1 AND '+dependent+' LIMIT 1',args))
    if later and not invalidate:return True
    if apply:
        # Keep every original game/attempt and advancement decision in the audit.
        store.audit(tid,'event_advancement_invalidated',{'event':m['eid'],'from_stage':m['stage'],'previous_decisions':store.rows('SELECT * FROM event_decisions WHERE eid=? AND stage>=?',(m['eid'],m['stage']))})
        store.db.execute('UPDATE event_children SET valid=0 WHERE eid=? AND '+dependent,args)
        store.db.execute('DELETE FROM event_decisions WHERE eid=? AND stage>=?',(m['eid'],m['stage']))
        change(store,m['eid'],stage=m['stage'],state='paused',active_tid=None,note='Result replacement requested. Later stages are archived; qualification will be recalculated after replay.')
    return False


def advancement(store,e,children):
    from .rankings import rows
    d=e['body']['definition'];tables=[]
    for c in children:
        t=store.tournament(c['tid']);slots=t['settings']['event_context']['slots'];ranks=rows(store,c['tid'],t['settings'])
        tables.append([{'slot':slots[r['slot']],'name':e['body']['profiles'][slots[r['slot']]]['name'],'points':r['points'],'rank':i+1} for i,r in enumerate(ranks)])
    if d['kind']=='league':
        from .leagues import movement
        return movement(d,tables,e['stage'])
    selected=[table[i]['slot'] for i in range(d['advance']) for table in tables] if e['stage']==0 else []
    return {'stage':e['stage']+1,'standings':tables,'qualified':selected,'policy':'Game points, configured standings tiebreaks, then recorded initial seed. KO final order follows match progression.'}


def tick(store,live_tids=(),experiment_busy=False):
    # During games, never deserialize a potentially large saved opening library.
    if experiment_busy:return
    e=store.one("SELECT id,execution_mode FROM events WHERE state='running' ORDER BY created LIMIT 1")
    if not e:return
    if live_tids or store.one("SELECT 1 FROM tournaments WHERE state IN ('running','draining') LIMIT 1"):
        # No large opening-library decode while engines are playing. A paused
        # child means attention is needed, even while other divisions are busy.
        bad=store.one("""SELECT t.note,t.dependency FROM event_children c JOIN tournaments t ON t.id=c.tid
          WHERE c.eid=? AND c.valid=1 AND c.activated=1 AND (t.state='paused' OR t.dependency<>'') LIMIT 1""",(e['id'],))
        if bad:hold(store,bad['dependency'] or bad['note'] or 'A division paused. Review the event before resuming.')
        return
    e=get(store,e['id']);eid=e['id']
    if 'circuit_state' in e['body']:
        from .circuits import tick as circuit_tick
        return circuit_tick(store,e)
    if 'season_state' in e['body']:
        from .seasons import tick as season_tick
        return season_tick(store,e)
    children=store.rows('SELECT c.*,t.state,t.dependency,t.note FROM event_children c JOIN tournaments t ON t.id=c.tid WHERE c.eid=? AND c.valid=1 AND c.stage=? ORDER BY c.bucket',(eid,e['stage']))
    if not children:
        if e['stage']!=0:raise ValueError('Event stage is missing; review saved event data.')
        with store.tx():
            for i,g in enumerate(e['body']['definition']['groups']):child(store,e,g,0,i)
            change(store,eid,note='')
        return
    pending=[c for c in children if c['state']!='completed']
    if pending:
        bad=next((c for c in pending if c['dependency'] or c['activated'] or c['tid']==e['active_tid']),None)
        if bad:
            hold(store,bad['dependency'] or bad['note'] or 'Current stage needs attention.')
            return
        with store.tx():
            for c in pending if e['execution_mode']=='parallel' else pending[:1]:
                store.db.execute("UPDATE tournaments SET state='running',started_once=1,note='' WHERE id=?",(c['tid'],))
                store.db.execute('UPDATE event_children SET activated=1 WHERE tid=?',(c['tid'],))
                store.audit(c['tid'],'state',{'state':'running','source':'event','event':eid})
            change(store,eid,active_tid=pending[0]['tid'],note='')
        return
    from .store import encode
    divisions=[c for c in children if c['role']!='championship']
    decision=advancement(store,e,divisions)
    with store.tx():
        if e['body']['definition']['kind']=='league':
            last=max((opening_end(store,c['tid']) for c in divisions),default=0)
            if e['body']['definition'].get('championship',{}).get('enabled'):
                final=next((c for c in children if c['role']=='championship'),None)
                if final is None:
                    slots=[r['slot'] for r in decision['standings'][0][:2]]
                    tid=child(store,e,slots,e['stage'],len(divisions),championship=True,opening_offset=last)
                    decision['championship']={'tid':tid,'state':'pending'}
                    store.db.execute('INSERT OR REPLACE INTO event_decisions VALUES(?,?,?)',(eid,e['stage'],encode(decision)))
                    change(store,eid,active_tid=None,note='Division standings complete. Championship final is ready.')
                    return
                from .knockout_results import read
                ft=store.tournament(final['tid']);result=read(store,final['tid'],ft['settings'])
                if result['champion_slot'] is None:raise ValueError('Completed championship has no match winner.')
                slot=ft['settings']['event_context']['slots'][result['champion_slot']]
                decision.update(champion=e['body']['profiles'][slot]['name'],champion_slot=slot,
                    championship={'tid':final['tid'],'state':'completed','winner':e['body']['profiles'][slot]['name'],
                                  'winner_slot':slot,'matches':result['rounds'][0]['matches'],'games':ft['total']})
                last=opening_end(store,final['tid'])
            decision['next_opening_offset']=last
        store.db.execute('INSERT OR REPLACE INTO event_decisions VALUES(?,?,?)',(eid,e['stage'],encode(decision)))
        store.audit(None,'event_advancement',dict(decision,event=eid))
        if e['body']['definition']['kind']=='league':
            if e['stage']+1<e['body']['definition']['seasons']:
                for i,g in enumerate(decision['next_groups']):child(store,e,g,e['stage']+1,i)
                change(store,eid,stage=e['stage']+1,active_tid=None)
            else:change(store,eid,state='completed',active_tid=None,note='All scheduled league seasons completed. Next-season division placements are saved.')
        elif e['stage']==0:
            child(store,e,decision['qualified'],1,0);change(store,eid,stage=1,active_tid=None)
        else:change(store,eid,state='completed',active_tid=None,note='All event stages completed.')


def hold(store,note):
    e=store.one("SELECT id FROM events WHERE state='running'")
    if e:
        with store.tx():
            change(store,e['id'],state='paused',note=note)
            drain(store,e['id'])


def drain(store,eid):
    store.db.execute("""UPDATE tournaments SET state='draining' WHERE state='running'
      AND id IN (SELECT tid FROM event_children WHERE eid=? AND valid=1)""",(eid,))


def opening_end(store,tid):
    row=store.one("SELECT total,json_extract(settings,'$.paired') paired,coalesce(json_extract(settings,'$.event_opening_offset'),0) offset FROM tournaments WHERE id=?",(tid,))
    return row['offset']+row['total']//(2 if row['paired'] else 1)


def scheduling(store):
    """Small scheduler descriptor; never deserialize source profiles or openings."""
    e=store.one("""SELECT id,execution_mode,resources FROM events WHERE state='running' OR
      EXISTS (SELECT 1 FROM event_children c JOIN tournaments t ON t.id=c.tid
        WHERE c.eid=events.id AND c.valid=1 AND t.state='draining') ORDER BY created LIMIT 1""")
    if not e:return None
    e['resources']=json.loads(e['resources'])
    return e


def set_resources(store,eid,revision,resources):
    from .store import encode
    from .tournament_queue import validate_resources
    e=get(store,eid)
    if type(revision) is not int or revision!=e['revision']:raise ValueError('This event changed. Refresh before trying again.')
    if e['execution_mode']!='parallel' or e['state']=='retired':raise ValueError('Shared resources require a current parallel event.')
    limits=validate_resources(resources)
    with store.tx():
        store.audit(None,'event_resources_changed',{'event':eid,'before':json.loads(e['resources']),'after':limits})
        e['body']['definition']['resources']=limits
        change(store,eid,resources=encode(limits),body=encode(e['body']))
    return detail(store,eid)


def delete_preview(store,ids):
    from .event_deletion import preview
    return preview(store,ids)


def delete_events(store,ids,expected,keep_ratings=True):
    from .event_deletion import delete
    return delete(store,ids,expected,keep_ratings)


def review_roster(store,*args,**kwargs):
    from .seasons import review
    return review(store,*args,**kwargs)


def fresh(store,eid,name):
    e=get(store,eid);body=copy.deepcopy(e['body'])
    if not str(name).strip():raise ValueError('Enter an event name.')
    if 'circuit_state' in body:
        from .circuits import reset,refresh_forecast
        reset(body);refresh_forecast(store,body)
    if 'season_state' in body:
        from .seasons import minimum
        from . import season_admission
        candidates=season_admission.pool(body)[:]
        d=body['definition'];groups=body['season_state']['groups'];d['groups']=copy.deepcopy(groups);d['sizes']=list(map(len,groups))
        body['season_state']={'season':1,'phase':'qualification' if d['qualifier']['enabled'] else 'division','bucket':len(groups)-1 if d['mode']=='progressive' else 0,'groups':copy.deepcopy(groups),'next_groups':[[] for _ in groups],'incoming':[],'offset':0,'review':True,'season_start':True,'history':[]}
        if season_admission.enabled(d):
            body['season_state']['candidates']=candidates;season_admission.begin(body)
        body['updates']=[];body['regular_games']=minimum(store,body)
    from .store import uid,encode
    new=uid()
    with store.tx():
        store.db.execute('INSERT INTO events(id,name,body,created,execution_mode,resources) VALUES(?,?,?,?,?,?)',(new,name.strip(),encode(body),time.time(),e['execution_mode'],e['resources']))
    return detail(store,new)


def circuit_call(store,method,*args,**kwargs):
    from . import circuits
    if method not in ('templates','edit','approve'):raise ValueError('Unknown competition action.')
    return getattr(circuits,method)(store,*args,**kwargs)
