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


def get(store,eid):
    e=store.one('SELECT * FROM events WHERE id=?',(eid,))
    if not e:raise ValueError('Event not found.')
    e['body']=json.loads(e['body']);return e


def integer(value,label,minimum=1):
    if type(value) is not int or value<minimum:raise ValueError(label+' must be a positive whole number.')
    return value


def prepare(store,source_tid,definition):
    t=store.tournament(source_tid);s=copy.deepcopy(t['settings']);n=t['participants'];d=copy.deepcopy(definition)
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
    if d.get('initial_format') not in ('round_robin','swiss'):raise ValueError('Choose round robin or Swiss for the first stage.')
    if d.get('final_format') not in ('knockout','round_robin'):raise ValueError('Choose knockout or round robin for the final stage.')
    advance=integer(d.get('advance',1),'Qualifiers per group')
    if d['kind']=='multistage' and (any(advance>len(g) for g in groups) or advance*len(groups)<2):raise ValueError('The final stage needs at least two qualifiers; the count must fit every group.')
    for k in ('initial_cycles','final_cycles','initial_rounds'):integer(d.get(k,1),k)
    if d.get('final_time_control'):TimeControl.parse(d['final_time_control'])
    d.setdefault('initial_cycles',1);d.setdefault('final_cycles',1);d.setdefault('initial_rounds',5);d['advance']=advance
    from .tournament_edit import original_openings
    s['openings']=original_openings(s)
    for k in ('custom_matchups','ko_round_games','event_context'):s.pop(k,None)
    profiles=[json.loads(r['profile']) for r in store.rows('SELECT profile FROM participants WHERE tid=? ORDER BY slot',(source_tid,))]
    body={'definition':d,'profiles':profiles,'settings':s,'source_name':t['name']}
    total=sum(prepared_child(store,body,g,0)[2] for g in groups)
    if d['kind']=='league':total*=d['seasons']
    else:total+=prepared_child(store,body,list(range(advance*len(groups))),1)[2]
    if total>9223372036854775807:raise ValueError('Event exceeds 64-bit game numbering capacity.')
    return body,total


def prepared_child(store,body,slots,stage):
    d=body['definition'];s=copy.deepcopy(body['settings']);openings=s.pop('openings')
    final=stage==1 and d['kind']=='multistage'
    s.update(format=d['final_format'] if final else d['initial_format'],cycles=d['final_cycles'] if final else d['initial_cycles'],
             rounds=d['initial_rounds'],knockout_tiebreak='continuous')
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
        store.db.execute('INSERT INTO events(id,name,body,created) VALUES(?,?,?,?)',(eid,name,encode(body),time.time()))
        store.audit(None,'event_created',{'event':eid,'name':name,'regular_games':total})
    return detail(store,eid)


def child(store,e,slots,stage,bucket):
    from .store import encode
    p,s,total=prepared_child(store,e['body'],slots,stage)
    d=e['body']['definition']
    label=f"Season {stage+1} — {d['division_names'][bucket]}" if d['kind']=='league' else f'Group {bucket+1}' if stage==0 else 'Final stage'
    s['event_context']={'id':e['id'],'name':e['name'],'stage':stage+1,'label':label,'slots':slots}
    tid=store.insert_tournament(e['name']+' — '+label,(p,s,total))
    store.db.execute('INSERT INTO event_children VALUES(?,?,?,?,1)',(tid,e['id'],stage,bucket))
    return tid


def change(store,eid,**values):
    store.db.execute('UPDATE events SET '+','.join([*(k+'=?' for k in values),'revision=revision+1'])+' WHERE id=?',(*values.values(),eid))


def detail(store,eid,offset=0,full=False):
    e=get(store,eid);body=e.pop('body');d=body['definition'];e.update(definition=d,participants=len(body['profiles']),regular_games=body['regular_games'],
        source_name=body['source_name'],unbounded=d['kind']=='multistage' and d['final_format']=='knockout',time_control=body['settings']['time_control'],tiebreaks=body['settings']['tiebreaks'],
        paired=body['settings']['paired'],opening_source=body['settings'].get('opening_source',{}),opening_positions=len(body['settings']['openings']))
    e['children']=store.rows('''SELECT c.*,t.name,t.state,t.total,t.note,t.dependency,
      coalesce((SELECT sum(n) FROM game_counts WHERE tid=t.id AND invalid=0 AND has_official=1),0) official_games
      FROM event_children c LEFT JOIN tournaments t ON t.id=c.tid WHERE c.eid=? ORDER BY c.stage,c.bucket,c.valid DESC,c.tid LIMIT ? OFFSET ?''',(eid,-1 if full else 50,0 if full else max(0,offset)))
    e['child_count']=store.one('SELECT count(*) n FROM event_children WHERE eid=?',(eid,))['n']
    e['official_games']=store.one('''SELECT coalesce(sum(g.n),0) n FROM game_counts g JOIN event_children c ON c.tid=g.tid
      WHERE c.eid=? AND c.valid=1 AND g.invalid=0 AND g.has_official=1''',(eid,))['n']
    e['decisions']=[json.loads(r['body']) for r in store.rows('SELECT body FROM event_decisions WHERE eid=? ORDER BY stage',(eid,))]
    return e


def listing(store,offset=0):
    return {'total':store.one('SELECT count(*) n FROM events')['n'],'items':store.rows('SELECT id,name,state,stage,note,revision FROM events ORDER BY created DESC LIMIT 50 OFFSET ?',(max(0,offset),))}


def command(store,eid,action,revision):
    e=get(store,eid)
    if type(revision) is not int or revision!=e['revision']:raise ValueError('This event changed. Refresh before trying again.')
    if action=='run':
        if e['state']=='retired':raise ValueError('This event is retired. Create a new event to play again.')
        if e['state']=='completed':raise ValueError('This event has completed.')
        if e['state']=='running':raise ValueError('This event is already running.')
        if store.failure:raise ValueError(store.failure)
        if store.one("SELECT 1 FROM events WHERE state='running' AND id<>?",(eid,)):raise ValueError('Pause the running event first.')
        if store.queue_call('summary')['mode'] in ('running','finish_current'):raise ValueError('Pause the automatic tournament queue first.')
        if store.one("SELECT 1 FROM tournaments WHERE state IN ('running','draining') LIMIT 1"):raise ValueError('Pause and drain running tournaments first.')
        if store.one('SELECT 1 FROM event_children c LEFT JOIN tournaments t ON t.id=c.tid WHERE c.eid=? AND c.valid=1 AND t.id IS NULL LIMIT 1',(eid,)):raise ValueError('An event tournament was deleted. Retire this event or create a new one.')
        with store.tx():change(store,eid,state='running',active_tid=None,note='')
    elif action=='pause':
        if e['state']!='running':raise ValueError('Only a running event can be paused.')
        with store.tx():
            change(store,eid,state='paused',note='Event paused. Active games drain before further changes.')
            if e['active_tid']:store.db.execute("UPDATE tournaments SET state='draining' WHERE id=? AND state='running'",(e['active_tid'],))
    elif action=='next_season':
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
            with store.tx():change(store,m['eid'],state='paused',note='Event paused with its current tournament.')


def recovery(store):
    store.db.execute("UPDATE events SET state='paused',revision=revision+1,note='Event recovered. Committed results and qualification decisions retained; resume when ready.' WHERE state='running'")


def replacement(store,tid,invalidate,apply=False):
    m=membership(store,tid)
    if not m:return False
    if not m['valid']:raise ValueError('Superseded event stages are archived. Select a current stage.')
    if m['event_state']=='running' or store.one("SELECT 1 FROM tournaments t JOIN event_children c ON c.tid=t.id WHERE c.eid=? AND t.state IN ('running','draining') LIMIT 1",(m['eid'],)):
        raise ValueError('Pause and drain the whole event before replacing a stage result.')
    later=bool(store.one('SELECT 1 FROM event_children WHERE eid=? AND valid=1 AND stage>? LIMIT 1',(m['eid'],m['stage'])))
    if later and not invalidate:return True
    if apply:
        # Keep every original game/attempt and advancement decision in the audit.
        store.audit(tid,'event_advancement_invalidated',{'event':m['eid'],'from_stage':m['stage'],'previous_decisions':store.rows('SELECT * FROM event_decisions WHERE eid=? AND stage>=?',(m['eid'],m['stage']))})
        store.db.execute('UPDATE event_children SET valid=0 WHERE eid=? AND stage>?',(m['eid'],m['stage']))
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
    if experiment_busy or live_tids:return
    e=store.one("SELECT id FROM events WHERE state='running' ORDER BY created LIMIT 1")
    if not e:return
    if store.one("SELECT 1 FROM tournaments WHERE state IN ('running','draining') LIMIT 1"):return
    e=get(store,e['id']);eid=e['id']
    children=store.rows('SELECT c.*,t.state,t.dependency,t.note FROM event_children c JOIN tournaments t ON t.id=c.tid WHERE c.eid=? AND c.valid=1 AND c.stage=? ORDER BY c.bucket',(eid,e['stage']))
    if not children:
        if e['stage']!=0:raise ValueError('Event stage is missing; review saved event data.')
        with store.tx():
            for i,g in enumerate(e['body']['definition']['groups']):child(store,e,g,0,i)
            change(store,eid,note='')
        return
    pending=next((c for c in children if c['state']!='completed'),None)
    if pending:
        if pending['dependency'] or pending['tid']==e['active_tid']:
            with store.tx():change(store,eid,state='paused',note=pending['dependency'] or pending['note'] or 'Current stage needs attention.')
            return
        with store.tx():
            store.db.execute("UPDATE tournaments SET state='running',started_once=1 WHERE id=?",(pending['tid'],))
            change(store,eid,active_tid=pending['tid'],note='')
            store.audit(pending['tid'],'state',{'state':'running','source':'event','event':eid})
        return
    from .store import encode
    decision=advancement(store,e,children)
    with store.tx():
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
    if store.one("SELECT 1 FROM events WHERE state='running'"):
        with store.tx():store.db.execute("UPDATE events SET state='paused',revision=revision+1,note=? WHERE state='running'",(note,))
