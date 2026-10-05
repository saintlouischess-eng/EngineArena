"""Durable tournament automation; enqueueing does not start or lock a setup."""
import math
import time
import json
import os
import psutil


def initialize(store):
    store.db.executescript('''
    CREATE TABLE IF NOT EXISTS tournament_queue(tid TEXT PRIMARY KEY,position INTEGER NOT NULL UNIQUE,
      finished INTEGER NOT NULL DEFAULT 0);
    CREATE INDEX IF NOT EXISTS tournament_queue_waiting ON tournament_queue(finished,position);
    CREATE TABLE IF NOT EXISTS queue_control(singleton INTEGER PRIMARY KEY CHECK(singleton=1),
      mode TEXT NOT NULL DEFAULT 'paused',active_tid TEXT,not_before REAL NOT NULL DEFAULT 0,
      revision INTEGER NOT NULL DEFAULT 0,note TEXT NOT NULL DEFAULT '');
    INSERT OR IGNORE INTO queue_control(singleton) VALUES(1);
    ''')
    for table,columns in {'tournament_queue':{'held':'INTEGER NOT NULL DEFAULT 0','priority':'INTEGER NOT NULL DEFAULT 2'},
            'queue_control':{'execution_mode':"TEXT NOT NULL DEFAULT 'sequential'",'resources':"TEXT NOT NULL DEFAULT '{}'"}}.items():
        existing={r['name'] for r in store.rows('PRAGMA table_info('+table+')')}
        for name,kind in columns.items():
            if name not in existing:store.db.execute(f'ALTER TABLE {table} ADD COLUMN {name} {kind}')
    summary(store)


def control(store):
    q=store.one('SELECT * FROM queue_control WHERE singleton=1')
    q['resources']=json.loads(q['resources'])
    return q


def change(store,**values):
    # Caller owns the transaction. Queue mutations also invalidate stale UI actions.
    if 'resources' in values:values['resources']=json.dumps(values['resources'])
    store.db.execute('UPDATE queue_control SET '+','.join([*(k+'=?' for k in values),'revision=revision+1'])+' WHERE singleton=1',tuple(values.values()))


def summary(store):
    q=control(store)
    counts=store.one('SELECT count(*) total,coalesce(sum(finished),0) completed FROM tournament_queue')
    active=store.one('SELECT name,state FROM tournaments WHERE id=?',(q['active_tid'],)) if q['active_tid'] else None
    counts.update(store.one('''SELECT count(*) running FROM tournaments WHERE state IN ('running','draining')'''))
    result={**q,**counts,'remaining':counts['total']-counts['completed'],'active':active}
    store.queue_status=result
    return result


def page(store,offset=0,search='',status='',sort='position',direction='asc'):
    if control(store)['execution_mode']=='parallel':return manager_page(store,offset,search,status,sort,direction)
    offset=max(0,int(offset));q=summary(store)
    rows=store.rows('''SELECT q.*,t.name,t.state,t.total,t.dependency,t.note,t.started_once,
      coalesce((SELECT sum(n) FROM game_counts WHERE tid=t.id AND invalid=0 AND has_official=1),0) official_games
      FROM tournament_queue q JOIN tournaments t ON t.id=q.tid ORDER BY q.position LIMIT 50 OFFSET ?''',(offset,))
    ends=store.one("SELECT min(position) first,max(position) last FROM tournament_queue WHERE finished=0 AND tid<>coalesce(?,'')",(q['active_tid'],))
    for item in rows:
        item['active']=item['tid']==q['active_tid']
        movable=not item['active'] and not item['finished']
        item['can_up']=movable and ends['first'] is not None and item['position']>ends['first']
        item['can_down']=movable and ends['last'] is not None and item['position']<ends['last']
    return {**q,'items':rows,'offset':offset}


def ended(store,tid,state):
    if state=='completed':return True
    # A frozen SPRT boundary is a successful endpoint despite a shorter schedule.
    row=store.one("SELECT 1 FROM sequential_state WHERE tid=? AND json_extract(body,'$.frozen')=1",(tid,))
    return state=='paused' and bool(row)


def add(store,ids=None,all_ready=False):
    ids=list(dict.fromkeys(ids or []))
    if all_ready:
        ids=[r['id'] for r in store.rows("SELECT id FROM tournaments WHERE state='paused' AND started_once=0 AND dependency='' AND id NOT IN (SELECT tid FROM event_children) ORDER BY created,id")]
    if not ids:raise ValueError('Select a saved tournament to add to the queue.')
    added=0
    with store.tx():
        position=store.one('SELECT coalesce(max(position),0) n FROM tournament_queue')['n']
        for tid in ids:
            if store.one('SELECT 1 FROM event_children WHERE tid=?',(tid,)):raise ValueError('Event stages run through their event, not the independent tournament queue.')
            item=store.one('SELECT finished FROM tournament_queue WHERE tid=?',(tid,))
            if item and not item['finished']:continue
            t=store.one('SELECT state,dependency FROM tournaments WHERE id=?',(tid,))
            if not t:raise ValueError('Tournament not found')
            if t['state']!='paused' or t['dependency'] or ended(store,tid,t['state']):
                raise ValueError('Only paused, unfinished tournaments without unresolved dependencies can be queued.')
            if item:store.db.execute('DELETE FROM tournament_queue WHERE tid=?',(tid,))
            position+=1;added+=1
            store.db.execute('INSERT INTO tournament_queue(tid,position) VALUES(?,?)',(tid,position))
            store.audit(tid,'queue_added',{'position':position})
        if added:
            q=control(store)
            change(store,**({'mode':'paused','note':''} if q['mode']=='completed' else {}))
    return {'added':added}


def require_revision(q,value):
    if type(value) is not int or value!=q['revision']:
        raise ValueError('The tournament queue changed. Refresh it before trying again.')


def command(store,action,revision,tid=None,not_before=0):
    with store.tx():
        q=control(store);require_revision(q,revision)
        if q['execution_mode']=='parallel':return parallel_command(store,action,tid,not_before)
        if action=='run':
            if store.one("SELECT 1 FROM events WHERE state='running'"):raise ValueError('Pause the running event first.')
            if q['mode'] in ('running','finish_current'):raise ValueError('The tournament queue is already running.')
            if not store.one('SELECT 1 FROM tournament_queue WHERE finished=0 LIMIT 1'):
                raise ValueError('Add an unfinished tournament before running the queue.')
            if isinstance(not_before,bool) or not isinstance(not_before,(int,float)) or not math.isfinite(not_before) or not_before<0:
                raise ValueError('Choose a valid queue start time.')
            if store.failure:raise ValueError(store.failure)
            change(store,mode='running',not_before=not_before,note='')
            # A paused active tournament resumes when tick sees its ownership;
            # waiting entries remain paused and editable until their own turn.
            if q['active_tid']:
                t=store.one('SELECT state,dependency FROM tournaments WHERE id=?',(q['active_tid'],))
                if t and t['dependency']:raise ValueError(t['dependency'])
                if t and t['state']=='draining':raise ValueError('Wait for active games to drain before resuming the queue.')
                change(store,active_tid=None)
        elif action=='pause':change(store,mode='paused',not_before=0,note='Queue paused. Resume when ready.')
        elif action=='finish_current':
            change(store,mode='finish_current' if q['active_tid'] else 'paused',not_before=0,note='The current tournament will finish; later tournaments will wait.')
        elif action in ('remove','up','down'):
            item=store.one('SELECT * FROM tournament_queue WHERE tid=?',(tid,))
            if not item:raise ValueError('This tournament is no longer in the queue.')
            if tid==q['active_tid']:
                t=store.one('SELECT state FROM tournaments WHERE id=?',(tid,))
                if action!='remove' or q['mode']!='paused' or t['state'] in ('running','draining'):
                    raise ValueError('Pause and drain the queue before removing its current tournament.')
                change(store,active_tid=None)
            if action=='remove':
                store.db.execute('DELETE FROM tournament_queue WHERE tid=?',(tid,));store.audit(tid,'queue_removed',{})
            else:
                if item['finished']:raise ValueError('Only waiting tournaments can be reordered.')
                sign,order=('<','DESC') if action=='up' else ('>','ASC')
                neighbor=store.one(f'''SELECT tid,position FROM tournament_queue WHERE finished=0 AND tid<>coalesce(?, '')
                  AND position {sign} ? ORDER BY position {order} LIMIT 1''',(q['active_tid'],item['position']))
                if neighbor:
                    store.db.execute('UPDATE tournament_queue SET position=-1 WHERE tid=?',(tid,))
                    store.db.execute('UPDATE tournament_queue SET position=? WHERE tid=?',(item['position'],neighbor['tid']))
                    store.db.execute('UPDATE tournament_queue SET position=? WHERE tid=?',(neighbor['position'],tid))
                    store.audit(tid,'queue_moved',{'direction':action})
            change(store,note='')
            if not store.one('SELECT 1 FROM tournament_queue WHERE finished=0 LIMIT 1'):
                change(store,mode='completed',active_tid=None,not_before=0)
        elif action=='clear_finished':
            store.db.execute('DELETE FROM tournament_queue WHERE finished=1');change(store)
        else:raise ValueError('Unknown queue action')
        store.audit(tid,'queue_'+action,{'not_before':not_before} if action=='run' else {})
    return summary(store)


def hold(store,note):
    q=control(store)
    if q['execution_mode']=='parallel':
        with store.tx():
            store.db.execute("UPDATE tournaments SET state='draining' WHERE state='running'")
            if q['mode']!='paused' or q['note']!=note:change(store,mode='paused',note=note)
        return
    if q['mode'] in ('running','finish_current'):
        with store.tx():change(store,mode='paused',note=note)


def recover(store):
    # Called inside the recovery transaction. Never restart engine processes
    # unexpectedly on application launch, including a previously timed queue.
    q=control(store)
    if q['mode'] in ('running','finish_current') or q['active_tid']:
        change(store,mode='paused',note='Queue recovered after restart. Order and results retained. Run the queue when ready.')


def tick(store,live_tids=(),experiment_busy=False):
    q=control(store)
    if q['execution_mode']=='parallel':return parallel_tick(store,live_tids,experiment_busy)
    if store.one("SELECT 1 FROM events WHERE state='running'"):return
    if q['mode'] not in ('running','finish_current'):return
    active=q['active_tid']
    if active:
        t=store.one('SELECT state,dependency,note FROM tournaments WHERE id=?',(active,))
        if not t:
            hold(store,'The current queue tournament was removed. Review the queue before resuming.');return
        if active in live_tids:return
        if ended(store,active,t['state']):
            with store.tx():
                store.db.execute('UPDATE tournament_queue SET finished=1 WHERE tid=?',(active,))
                change(store,active_tid=None,mode='paused' if q['mode']=='finish_current' else 'running',note='')
                store.audit(active,'queue_completed',{})
            if q['mode']=='finish_current':return
            q=control(store)
        elif t['dependency'] or t['state']=='paused':
            hold(store,t['dependency'] or t['note'] or 'The current tournament paused. Review it before resuming the queue.');return
        else:return
    item=store.one('SELECT tid FROM tournament_queue WHERE finished=0 ORDER BY position LIMIT 1')
    if not item:
        with store.tx():change(store,mode='completed',active_tid=None,not_before=0,note='All queued tournaments have finished.')
        return
    if q['not_before']>time.time():return
    # Existing manually-started tournaments and experiments finish first.
    if live_tids or experiment_busy or store.one("SELECT 1 FROM tournaments WHERE state IN ('running','draining') LIMIT 1"):return
    tid=item['tid'];t=store.tournament(tid)
    if ended(store,tid,t['state']):
        with store.tx():store.db.execute('UPDATE tournament_queue SET finished=1 WHERE tid=?',(tid,));change(store)
        return
    if t['dependency'] or t['state']!='paused':
        hold(store,t['dependency'] or 'A queued tournament needs attention before it can start.');return
    # Starting and recording queue ownership commit together, avoiding the crash
    # gap where a tournament runs but the queue cannot identify its current job.
    with store.tx():
        store.db.execute("UPDATE tournaments SET state='running',started_once=1,note=replace(note,' Resume when ready.','') WHERE id=?",(tid,))
        change(store,active_tid=tid,not_before=0,note='')
        store.audit(tid,'state',{'state':'running','source':'automatic_queue'})


def manual_action(store,tid,action):
    from .events import manual_action as event_action
    event_action(store,tid,action)
    q=control(store)
    member=store.one('SELECT finished FROM tournament_queue WHERE tid=?',(tid,))
    if q['execution_mode']=='parallel':
        if action=='start' and not member:
            add(store,[tid]);member={'finished':0}
        if action in ('pause','cancel') and member:
            with store.tx():
                store.db.execute('UPDATE tournament_queue SET held=1 WHERE tid=?',(tid,));change(store)
        if action=='start' and member:
            with store.tx():
                store.db.execute('UPDATE tournament_queue SET held=0,finished=0 WHERE tid=?',(tid,));change(store)
        return
    if action=='start' and member and not member['finished']:
        raise ValueError('This tournament is in the automatic queue. Use Run queue, or remove it from the queue to start it separately.')
    if action=='start' and q['mode'] in ('running','finish_current'):
        raise ValueError('Pause the automatic queue before starting a separate tournament.')
    if action in ('pause','cancel') and q['active_tid']==tid:
        hold(store,'Queue paused with its current tournament. Run the queue to continue.')


def resource_defaults(store):
    groups=store.rows("SELECT DISTINCT json_extract(profile,'$.gpu_group') name FROM participants WHERE coalesce(json_extract(profile,'$.gpu_group'),'')<>''")
    return {'cpu_budget':os.cpu_count() or 1,'memory_budget_mb':max(1,int(psutil.virtual_memory().available/2**20*.85)),
            'concurrency':min(32,os.cpu_count() or 1),'gpu_limits':{r['name']:1 for r in groups}}


def configuration(store):
    q=summary(store)
    return q|{'defaults':resource_defaults(store)}


def configure(store,revision,execution_mode,resources):
    q=control(store);require_revision(q,revision)
    if execution_mode not in ('sequential','parallel'):raise ValueError('Choose one at a time or run together.')
    if execution_mode!=q['execution_mode'] and store.one("SELECT 1 FROM tournaments WHERE state IN ('running','draining') LIMIT 1"):
        raise ValueError('Pause and drain all tournaments before changing execution mode.')
    if execution_mode!=q['execution_mode'] and q['mode'] in ('running','finish_current'):
        raise ValueError('Pause the tournament manager before changing execution mode.')
    if not isinstance(resources,dict):raise ValueError('Enter shared resource limits.')
    result={}
    for key in ('cpu_budget','memory_budget_mb','concurrency'):
        value=resources.get(key)
        if type(value) is not int or value<1 or value>2147483647:raise ValueError('Shared resource limits must be positive whole numbers.')
        result[key]=value
    gpu=resources.get('gpu_limits',{})
    if not isinstance(gpu,dict) or any(not isinstance(k,str) or not k.strip() or k!=k.strip() or len(k)>100 or type(v) is not int or v<0 or v>2147483647 for k,v in gpu.items()):
        raise ValueError('GPU limits require a group name and a nonnegative whole number.')
    result['gpu_limits']=gpu
    with store.tx():
        change(store,execution_mode=execution_mode,resources=result,active_tid=None if execution_mode!=q['execution_mode'] else q['active_tid'])
        store.audit(None,'shared_resources_changed',{'before':{'mode':q['execution_mode'],'resources':q['resources']},'after':{'mode':execution_mode,'resources':result}})
    return summary(store)


def manager_page(store,offset=0,search='',status='',sort='position',direction='asc'):
    q=summary(store);offset=max(0,int(offset));params=[];where=[]
    if search:
        where.append("t.name LIKE ? ESCAPE '\\'");params.append('%'+search.replace('\\','\\\\').replace('%','\\%').replace('_','\\_')+'%')
    if status=='active':where.append("t.state IN ('running','draining')")
    elif status=='waiting':where.append("q.finished=0 AND q.held=0 AND t.state='paused'")
    elif status=='paused':where.append("q.finished=0 AND (q.held=1 OR t.dependency<>'') AND t.state='paused'")
    elif status=='finished':where.append('q.finished=1')
    elif status:raise ValueError('Unknown tournament filter')
    clause=' WHERE '+' AND '.join(where) if where else ''
    source=' FROM tournament_queue q JOIN tournaments t ON t.id=q.tid'
    total=store.one('SELECT count(*) n'+source+clause,tuple(params))['n']
    columns={'position':'q.position','name':'t.name COLLATE NOCASE','state':'t.state','progress':'1.0*official_games/max(t.total,1)','priority':'q.priority','active':'active_games'}
    if sort not in columns or direction not in ('asc','desc'):raise ValueError('Unknown tournament sort')
    rows=store.rows('''SELECT q.*,t.name,t.state,t.total,t.dependency,t.note,t.started_once,
      json_extract(t.settings,'$.concurrency') game_limit,
      coalesce((SELECT sum(n) FROM game_counts WHERE tid=t.id AND invalid=0 AND has_official=1),0) official_games,
      coalesce((SELECT sum(n) FROM game_counts WHERE tid=t.id AND invalid=0 AND state='running'),0) active_games'''+source+clause+
      ' ORDER BY '+columns[sort]+' '+direction+',q.position LIMIT 50 OFFSET ?',tuple(params)+(offset,))
    for item in rows:
        item['active']=item['state'] in ('running','draining');item['can_up']=item['can_down']=False
    return q|{'items':rows,'offset':offset,'filtered_total':total,'search':search,'filter':status,'sort':sort,'direction':direction}


def parallel_tick(store,live_tids=(),experiment_busy=False):
    # Completion is cheap and incremental; waiting jobs retain editable setups.
    done=store.rows('''SELECT q.tid FROM tournament_queue q JOIN tournaments t ON t.id=q.tid
       WHERE q.finished=0 AND (t.state='completed' OR (t.state='paused' AND EXISTS
       (SELECT 1 FROM sequential_state s WHERE s.tid=t.id AND json_extract(s.body,'$.frozen')=1)))''')
    done=[r['tid'] for r in done if r['tid'] not in live_tids]
    q=control(store)
    with store.tx():
        for tid in done:
            store.db.execute('UPDATE tournament_queue SET finished=1 WHERE tid=?',(tid,));store.audit(tid,'queue_completed',{})
        if done:change(store)
        if q['mode']=='finish_current' and not store.one("SELECT 1 FROM tournaments WHERE state IN ('running','draining') LIMIT 1"):
            change(store,mode='paused',note='Active tournaments finished. Waiting tournaments are paused.')
        elif q['mode']=='running' and not store.one('SELECT 1 FROM tournament_queue WHERE finished=0 LIMIT 1'):
            change(store,mode='completed',not_before=0,note='All queued tournaments have finished.')


def candidates(store):
    q=control(store)
    waiting=q['mode']=='running' and q['not_before']<=time.time() and not store.one("SELECT 1 FROM events WHERE state='running' LIMIT 1")
    return store.rows('''SELECT t.id,t.name,t.state,t.dependency,coalesce(q.priority,2) priority,
      coalesce(q.position,0) position,json_extract(t.settings,'$.concurrency') game_limit
      FROM tournaments t LEFT JOIN tournament_queue q ON q.tid=t.id
      WHERE t.state IN ('running','draining') OR (? AND q.finished=0 AND q.held=0 AND t.state='paused' AND t.dependency='')
      ORDER BY coalesce(q.position,0),t.created,t.id''',(waiting,))


def parallel_command(store,action,tid=None,not_before=0):
    q=control(store)
    if action=='run':
        if store.failure:raise ValueError(store.failure)
        if store.one("SELECT 1 FROM events WHERE state='running'"):raise ValueError('Pause the running event first.')
        if q['mode'] in ('running','finish_current'):raise ValueError('The tournament queue is already running.')
        if not store.one('SELECT 1 FROM tournament_queue WHERE finished=0 LIMIT 1'):raise ValueError('Add an unfinished tournament before running the queue.')
        if type(not_before) not in (int,float) or not math.isfinite(not_before) or not_before<0:raise ValueError('Choose a valid queue start time.')
        if not q['resources']:raise ValueError('Save shared resource limits before running together.')
        change(store,mode='running',not_before=not_before,active_tid=None,note='')
    elif action=='pause':
        store.db.execute("UPDATE tournaments SET state='draining' WHERE state='running'")
        change(store,mode='paused',not_before=0,note='Manager paused. Active games finish normally. Resume when ready.')
    elif action=='finish_current':
        change(store,mode='finish_current',not_before=0,note='Finish active tournaments, then pause. Waiting tournaments will not start.')
    elif action=='remove':
        t=store.one('SELECT state FROM tournaments WHERE id=?',(tid,))
        if t and t['state'] in ('running','draining'):raise ValueError('Pause and drain this tournament before removing it.')
        store.db.execute('DELETE FROM tournament_queue WHERE tid=?',(tid,));change(store)
    elif action=='clear_finished':
        store.db.execute('DELETE FROM tournament_queue WHERE finished=1');change(store)
    else:raise ValueError('Unknown manager action')
    store.audit(tid,'queue_'+action,{'not_before':not_before} if action=='run' else {})
    return summary(store)


def manage(store,revision,action,ids,priority=None,concurrency=None):
    q=control(store);require_revision(q,revision)
    if q['execution_mode']!='parallel':raise ValueError('Select Run together first.')
    if not isinstance(ids,list) or not ids or any(not isinstance(x,str) for x in ids):raise ValueError('Select tournaments first.')
    ids=list(dict.fromkeys(ids))
    if action not in ('pause_selected','resume_selected','set_limits'):raise ValueError('Unknown manager action')
    if priority is not None and (type(priority) is not int or priority not in (1,2,4)):raise ValueError('Choose Low, Normal or High priority.')
    if concurrency is not None and (type(concurrency) is not int or concurrency<1 or concurrency>2147483647):raise ValueError('Concurrent games must be a positive whole number')
    with store.tx():
        for tid in ids:
            item=store.one('SELECT q.*,t.state,t.dependency FROM tournament_queue q JOIN tournaments t ON t.id=q.tid WHERE tid=?',(tid,))
            if not item:raise ValueError('A selected tournament is no longer in the manager. Refresh the list.')
            if action=='resume_selected':
                if store.failure:raise ValueError(store.failure)
                if item['finished'] or item['dependency']:raise ValueError(item['dependency'] or 'This tournament has finished.')
                if item['state']=='draining':raise ValueError('Wait for active games to drain before resuming.')
                if store.one("SELECT 1 FROM events WHERE state='running'"):raise ValueError('Pause the running event first.')
                from .sequential import frozen,diagnostics
                if frozen(store,tid) and not diagnostics(store,tid):raise ValueError('SPRT has reached its recorded stopping boundary.')
                store.db.execute('UPDATE tournament_queue SET held=0 WHERE tid=?',(tid,))
                store.db.execute("UPDATE tournaments SET state='running',started_once=1,note=CASE WHEN note LIKE 'No remaining game fits the resource budgets:%' THEN '' ELSE replace(note,' Resume when ready.','') END WHERE id=?",(tid,))
                store.audit(tid,'state',{'state':'running','source':'tournament_manager'})
            elif action=='pause_selected':
                store.db.execute('UPDATE tournament_queue SET held=1 WHERE tid=?',(tid,))
                if item['state']=='running':store.db.execute("UPDATE tournaments SET state='draining' WHERE id=?",(tid,))
            else:
                if priority is not None:store.db.execute('UPDATE tournament_queue SET priority=? WHERE tid=?',(priority,tid))
                if concurrency is not None:
                    if item['state'] not in ('paused','running','draining'):raise ValueError('Concurrency can only change for an unfinished tournament')
                    previous=store.one("SELECT json_extract(settings,'$.concurrency') n FROM tournaments WHERE id=?",(tid,))['n']
                    if previous!=concurrency:
                        store.db.execute("UPDATE tournaments SET settings=json_set(settings,'$.concurrency',?),setup_revision=setup_revision+1 WHERE id=?",(concurrency,tid))
                        active=store.one("SELECT count(*) n FROM games WHERE tid=? AND state='running' AND invalid=0",(tid,))['n']
                        store.audit(tid,'concurrency_changed',{'before':previous,'after':concurrency,'active':active})
            store.audit(tid,'manager_'+action,{'priority':priority,'concurrency':concurrency})
        change(store)
    return summary(store)


def block(store,tid,note):
    with store.tx():
        store.db.execute("UPDATE tournaments SET state='draining',note=? WHERE id=?",(note,tid))
        store.db.execute('UPDATE tournament_queue SET held=1 WHERE tid=?',(tid,));change(store)
