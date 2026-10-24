"""Audited RR roster revisions; original attempts and rating evidence are retained."""
import hashlib
import json
import time


def standing_slots(settings,count):
    return sorted(set(settings.get('rr_active_slots',range(count)))|set(settings.get('rr_withdrawn_retained',[])))


def initialize(store):
    store.db.executescript('''
      CREATE TABLE IF NOT EXISTS rr_revisions(tid TEXT,revision INTEGER,created REAL,body TEXT,PRIMARY KEY(tid,revision));
      CREATE TABLE IF NOT EXISTS rr_revision_games(tid TEXT,revision INTEGER,gid TEXT,aid TEXT,PRIMARY KEY(tid,revision,gid));
    ''')


def archive(store,tid):
    from .standings import page
    t=store.tournament(tid)
    revision=store.one('SELECT coalesce(max(revision),0)+1 n FROM rr_revisions WHERE tid=?',(tid,))['n']
    shown=set(standing_slots(t['settings'],t['slot_count']))
    body={'name':t['name'],'state':t['state'],'total':t['total'],'settings':t['settings'],
      'participants':[dict(slot=r['slot'],name=json.loads(r['profile'])['name'],withdrawn=r['slot'] in t['settings'].get('rr_withdrawn_retained',[])) for r in store.rows('SELECT slot,profile FROM participants WHERE tid=? ORDER BY slot',(tid,)) if r['slot'] in shown],
      'standings':page(store,tid,t['settings'],0,max(1,t['participants']))}
    store.db.execute('INSERT INTO rr_revisions VALUES(?,?,?,?)',(tid,revision,time.time(),json.dumps(body)))
    store.db.execute('INSERT INTO rr_revision_games SELECT tid,?,id,official FROM games WHERE tid=? AND invalid=0 AND official IS NOT NULL',(revision,tid))
    return revision


def history(store,tid,revision=None):
    store.tournament(tid)
    if revision is None:return store.rows('SELECT revision,created,json_extract(body,\'$.name\') name,json_extract(body,\'$.total\') total FROM rr_revisions WHERE tid=? ORDER BY revision DESC',(tid,))
    r=store.one('SELECT * FROM rr_revisions WHERE tid=? AND revision=?',(tid,int(revision)))
    if not r:raise ValueError('Roster revision not found')
    return dict(revision=r['revision'],created=r['created'],**json.loads(r['body']))


def checked(store,tid,removed,profiles,scheduling='after_existing',result_policy=None):
    from .tournament_extend import reason
    t=store.tournament(tid)
    if reason(t):raise ValueError(reason(t))
    if scheduling not in ('catch_up','balanced','after_existing'):raise ValueError('Unknown newcomer scheduling choice')
    if store.one("SELECT 1 FROM games WHERE tid=? AND state='running' LIMIT 1",(tid,)) or store.one("SELECT 1 FROM attempts a JOIN games g ON g.id=a.gid WHERE g.tid=? AND a.ended IS NULL LIMIT 1",(tid,)):
        raise ValueError('Wait for all active games to finish draining')
    ongoing=t['state']=='paused'
    result_policy=result_policy or ('keep' if ongoing else 'ratings_only')
    if result_policy not in ('keep','ratings_only'):raise ValueError('Unknown withdrawn-result policy')
    if not ongoing and result_policy=='keep':raise ValueError('Completed roster revisions exclude withdrawn results from standings')
    keep_played=result_policy=='keep'
    previous=t['settings'].get('rr_withdrawn_retained',[])
    official=store.one('SELECT count(*) n FROM games WHERE tid=? AND invalid=0 AND official IS NOT NULL',(tid,))['n']
    if not ongoing:
        if store.one("SELECT 1 FROM games WHERE tid=? AND invalid=0 AND (state<>'completed' OR official IS NULL) LIMIT 1",(tid,)):raise ValueError('Finish all scheduled games and replays first')
        if official!=t['total']:raise ValueError('All scheduled games must have a committed official result')
    active=t['settings'].get('rr_active_slots',list(range(t['slot_count'])))
    if not isinstance(removed,list) or (not removed and not (result_policy=='ratings_only' and previous)) or any(type(v) is not int or v not in active for v in removed) or len(set(removed))!=len(removed):raise ValueError('Choose distinct active entrants to withdraw')
    excluded_slots=sorted(set(removed)|set(previous)) if result_policy=='ratings_only' else []
    if len(active)-len(removed)+len(profiles)<2:raise ValueError('At least two active entrants are required')
    ids=[p.get('id') for p in profiles]
    existing=[json.loads(r['profile']).get('id') for r in store.rows('SELECT profile FROM participants WHERE tid=?',(tid,))]
    if any(not p for p in ids) or len(set(ids))!=len(ids) or set(ids)&set(existing):raise ValueError('Replacement profiles need their own new participant identity')
    from .move_books import validate
    from .models import TimeControl
    profiles=[dict(p,move_book=validate(store,p.get('move_book'))) for p in profiles]
    for p in profiles:
        if p.get('time_control'):TimeControl.parse(p['time_control'])
    remaining=[x for x in active if x not in removed];n=len(remaining);m=len(profiles);s=t['settings'];legs=2 if s['paired'] else 1
    # Active entrants still have a complete mutual schedule. Previously played
    # games involving withdrawn entrants are additional, retained evidence.
    raw=json.dumps(remaining)
    historical_sql='''SELECT count(*) n FROM games WHERE tid=? AND invalid=0 AND official IS NOT NULL
      AND (white NOT IN (SELECT value FROM json_each(?)) OR black NOT IN (SELECT value FROM json_each(?)))'''
    historical_args=(tid,raw,raw)
    if not keep_played:
        historical_sql+=' AND white NOT IN (SELECT value FROM json_each(?)) AND black NOT IN (SELECT value FROM json_each(?))'
        historical_args+=(json.dumps(excluded_slots),json.dumps(excluded_slots))
    historical=store.one(historical_sql,historical_args)['n']
    existing=n*(n-1)//2*s['cycles']*legs+historical;added=(n*m+m*(m-1)//2)*s['cycles']*legs
    excluded=store.one('''SELECT count(*) n FROM games WHERE tid=? AND invalid=0 AND official IS NOT NULL
      AND (white IN (SELECT value FROM json_each(?)) OR black IN (SELECT value FROM json_each(?)))''',
      (tid,json.dumps(excluded_slots),json.dumps(excluded_slots)))['n']
    retained=official-excluded
    rev=store.one('SELECT revision FROM report_revisions WHERE tid=?',(tid,))
    token=hashlib.sha256(json.dumps([tid,t['setup_revision'],t['state'],t['total'],rev,removed,profiles,scheduling,result_policy],sort_keys=True).encode()).hexdigest()
    return t,profiles,{'expected':token,'removed':removed,'remaining':remaining,'retained_games':retained,
      'excluded_games':excluded,'canceled_games':t['total']-existing-excluded if ongoing else 0,
      'keep_played':keep_played,'ongoing':ongoing,'result_policy':result_policy,'excluded_slots':excluded_slots,
      'games_per_active_engine':(n+m-1)*s['cycles']*legs if not keep_played else None,
      'scheduling':scheduling,'existing_schedule':existing,'additional_games':added,'total_games':existing+added,
      'new_participants':n+m,'removed_names':[store.participant(tid,i)['name'] for i in removed],'new_names':[p['name'] for p in profiles]}


def preview(store,tid,removed,profiles=(),scheduling='after_existing',result_policy=None):return checked(store,tid,removed,profiles,scheduling,result_policy)[2]


def change(store,tid,removed,profiles,expected,scheduling='after_existing',result_policy=None):
    from .reliability import delta
    with store.tx():
        t,profiles,p=checked(store,tid,removed,profiles,scheduling,result_policy)
        if expected!=p['expected']:raise ValueError('The roster or results changed. Preview again.')
        archive(store,tid)
        # Reverse only revised-standing contributions. Never call rating sync:
        # those historical games retain their original engine identities/results.
        affected_slots=removed if p['keep_played'] else p['excluded_slots']
        args=(tid,json.dumps(affected_slots),json.dumps(affected_slots))
        affected="tid=? AND invalid=0 AND (white IN (SELECT value FROM json_each(?)) OR black IN (SELECT value FROM json_each(?)))"
        if p['keep_played']:
            # Cancel only future games, including retries without an official
            # result. An already-scored game queued for replay keeps its result.
            store.db.execute("UPDATE games SET invalid=1,state='invalidated' WHERE "+affected+' AND official IS NULL',args)
            store.db.execute("UPDATE games SET state='completed' WHERE "+affected+" AND official IS NOT NULL AND state<>'completed'",args)
        else:
            for row in store.rows('SELECT DISTINCT pair_no FROM games WHERE '+affected,args):store._pair_delta(tid,row['pair_no'],-1)
            cursor=store.db.execute('SELECT * FROM games WHERE '+affected,args)
            while batch:=cursor.fetchmany(100):
                for row in batch:
                    g=dict(row);a=store.one('SELECT result,reason,mode FROM attempts WHERE id=?',(g['official'],))
                    if a:store._result_delta(g,a['result'],-1);delta(store,g,a,official=-1)
            store.db.execute("UPDATE games SET invalid=1,state=CASE WHEN official IS NULL THEN 'invalidated' ELSE 'completed' END WHERE "+affected,args)
            raw=json.dumps(affected_slots)
            store.db.execute('DELETE FROM rankings WHERE tid=? AND slot IN (SELECT value FROM json_each(?))',(tid,raw))
            store.db.execute('DELETE FROM aggregates WHERE tid=? AND (a IN (SELECT value FROM json_each(?)) OR b IN (SELECT value FROM json_each(?)))',(tid,raw,raw))
        s=t['settings'];s['rr_active_slots']=p['remaining'];s['rr_schedule_total']=s.get('rr_schedule_total',t['total'])
        if p['keep_played']:s['rr_withdrawn_retained']=sorted(set(s.get('rr_withdrawn_retained',[]))|set(removed))
        else:
            s['rr_withdrawn_retained']=[]
            s['rr_withdrawn_excluded']=sorted(set(s.get('rr_withdrawn_excluded',[]))|set(affected_slots))
        if rule:=s.get('rr_admission'):
            for key in ('old_slots','new_slots'):rule[key]=[v for v in rule[key] if v in p['remaining']]
        store.db.execute('UPDATE tournaments SET settings=?,total=?,started_once=1,setup_revision=setup_revision+1 WHERE id=?',(json.dumps(s),p['existing_schedule'],tid))
        if profiles:
            from .tournament_extend import preview as add_preview,extend
            new=add_preview(store,tid,profiles,scheduling)
            extend(store,tid,profiles,new['expected'],scheduling,in_transaction=True)
        else:
            store.db.execute('INSERT INTO report_revisions VALUES(?,1) ON CONFLICT(tid) DO UPDATE SET revision=revision+1',(tid,))
        if p['ongoing']:
            store.db.execute('UPDATE tournament_queue SET finished=0,held=1 WHERE tid=?',(tid,))
        store.audit(tid,'round_robin_roster_revised',p)
    return store.tournament(tid)
