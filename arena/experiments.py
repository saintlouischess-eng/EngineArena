"""Durable EPD best/avoid suites and reproducible node/thread benchmarks."""
import asyncio
import copy
import json
import math
from pathlib import Path
import time
import chess
from .models import Clock,TimeControl,go_command
from .uci import UciEngine,EngineFailure
from .store import DEFAULTS,encode,uid,now

def parse_suite(path):
    cases=[]
    for number,line in enumerate(Path(path).read_text(encoding='utf-8-sig').splitlines(),1):
        if not line.strip() or line.lstrip().startswith('#'):continue
        board=chess.Board()
        try:operations=board.set_epd(line)
        except ValueError as e:raise ValueError(f'Invalid EPD on line {number}: {e}') from e
        if not board.is_valid():raise ValueError(f'Invalid EPD on line {number}')
        bm=[m.uci() for m in operations.get('bm',[])];am=[m.uci() for m in operations.get('am',[])]
        if not bm and not am:raise ValueError(f'EPD line {number} has no bm or am operation')
        if not any(board.legal_moves) or set(bm)&set(am) or any(not chess.Move.from_uci(m) for m in bm+am):raise ValueError(f'EPD line {number} has contradictory or unplayable answers')
        cases.append({'fen':board.fen(),'id':str(operations.get('id',number)),'bm':bm,'am':am})
    if not cases:raise ValueError('No EPD test cases found')
    return cases

def case_count(cases):
    return len(cases) if isinstance(cases,list) else len(cases['thread_counts'])*cases['repeats']

def case_at(cases,index):
    if isinstance(cases,list):return cases[index]
    threads=cases['thread_counts'][index//cases['repeats']];repeat=index%cases['repeats']+1
    return {'id':f'{threads} threads / repeat {repeat}','fen':cases['fen'],'threads':threads,'repeat':repeat}

def metrics(body):
    # Small indexed-row payload: refreshing a large experiment never scans UCI logs.
    return encode({k:body.get(k) for k in ('profile','profile_slot','official','correct','reason','elapsed_seconds','measured_nps','effective_threads')}|{'threads':body.get('case',{}).get('threads')})

def initialize(store):
    store.db.executescript('''
    CREATE TABLE IF NOT EXISTS experiments(id TEXT PRIMARY KEY,name TEXT,kind TEXT,state TEXT,created REAL,settings TEXT,profiles TEXT,cases TEXT,total INTEGER,cursor INTEGER DEFAULT 0);
    CREATE TABLE IF NOT EXISTS experiment_attempts(id TEXT PRIMARY KEY,eid TEXT,number INTEGER,started REAL,ended REAL,body TEXT);
    CREATE INDEX IF NOT EXISTS experiments_queue ON experiments(state,created);
    CREATE INDEX IF NOT EXISTS experiment_results ON experiment_attempts(eid,number);
    ''')
    if 'summary' not in {r['name'] for r in store.rows('PRAGMA table_info(experiment_attempts)')}:
        with store.tx():
            store.db.execute('ALTER TABLE experiment_attempts ADD COLUMN summary TEXT')
            for row in store.db.execute('SELECT id,body FROM experiment_attempts'):
                store.db.execute('UPDATE experiment_attempts SET summary=? WHERE id=?',(metrics(json.loads(row['body'])),row['id']))
    store.db.execute('CREATE INDEX IF NOT EXISTS experiment_summary ON experiment_attempts(eid,summary,ended)')
    with store.tx():
        store.db.execute("UPDATE experiments SET state='paused' WHERE state='running'")
        for row in store.rows('SELECT id,body FROM experiment_attempts WHERE ended IS NULL'):
            body=json.loads(row['body']);body.update(reason='interrupted',detail='Worker interrupted; case can restart on resume')
            store.db.execute('UPDATE experiment_attempts SET ended=?,body=?,summary=? WHERE id=?',(now(),encode(body),metrics(body),row['id']))

def create(store,name,kind,profiles,settings,path=None):
    if not profiles:raise ValueError('Select at least one engine profile')
    if not isinstance(name,str) or not name.strip():raise ValueError('Experiment name is required')
    s=DEFAULTS|settings;tc=TimeControl.parse(s['time_control'])
    s['ponder']=False;s['chess960']=False
    for key in ('startup_timeout','readiness_timeout','hang_timeout','stop_timeout','tolerance'):
        value=s[key]
        if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or value<0 or (key!='tolerance' and value==0):raise ValueError(key+' must be finite and positive')
    if tc.kind not in ('nodes','depth','movetime'):raise ValueError('Suites and benchmarks require nodes, depth or fixed move time')
    if kind=='suite':cases=parse_suite(path)
    elif kind=='benchmark':
        threads=settings.get('thread_counts',[1,2,4,8]);repeats=settings.get('repeats',3)
        if not isinstance(threads,list) or not threads or any(type(n) is not int or n<1 for n in threads):raise ValueError('Thread counts must be positive integers')
        if len(set(threads))!=len(threads):raise ValueError('Thread counts must not repeat; use the repeat count instead')
        if type(repeats) is not int or repeats<1:raise ValueError('Positive repeat count required')
        board=chess.Board(settings.get('fen',chess.STARTING_FEN))
        if not board.is_valid() or not any(board.legal_moves):raise ValueError('Benchmark position must be valid with legal moves')
        cases={'thread_counts':threads,'repeats':repeats,'fen':board.fen()}
    else:raise ValueError('Unknown experiment kind')
    count=case_count(cases);total=count*len(profiles)
    if total>9223372036854775807:raise ValueError('Experiment case count exceeds the storage integer range')
    eid=uid()
    with store.tx():
        store.db.execute('INSERT INTO experiments(id,name,kind,state,created,settings,profiles,cases,total) VALUES(?,?,?,?,?,?,?,?,?)',(eid,name.strip(),kind,'paused',now(),encode(s),encode(profiles),encode(cases),total))
        store.audit(eid,'experiment_created',{'kind':kind,'cases':count,'profiles':len(profiles)})
    return get(store,eid)

def get(store,eid,offset=0,limit=None):
    row=store.one('SELECT * FROM experiments WHERE id=?',(eid,))
    if not row:raise ValueError('Experiment not found')
    for key in ('settings','profiles','cases'):row[key]=json.loads(row[key])
    if type(offset) is not int or offset<0:raise ValueError('Invalid result offset')
    if limit is not None and (type(limit) is not int or not 1<=limit<=100):raise ValueError('Invalid result page size')
    summary=store.one("""SELECT count(*) attempts,
        coalesce(sum(json_extract(summary,'$.official')=1),0) completed,
        coalesce(sum(json_extract(summary,'$.official')=1 AND json_extract(summary,'$.correct')=1),0) correct,
        coalesce(sum(json_extract(summary,'$.official')=1 AND json_extract(summary,'$.reason')<>'completed'),0) failures,
        coalesce(sum(ended IS NULL),0) active FROM experiment_attempts WHERE eid=?""",(eid,))
    row.update(summary);row['offset']=offset;row['limit']=limit;row['case_count']=case_count(row['cases'])
    row['accuracy_pct']=100*row['correct']/row['completed'] if row['completed'] and row['kind']=='suite' else None
    row['benchmark_summary']=store.rows("""SELECT json_extract(summary,'$.profile') profile,
        json_extract(summary,'$.profile_slot') profile_slot,json_extract(summary,'$.effective_threads') threads,
        count(*) samples,count(json_extract(summary,'$.measured_nps')) nps_samples,avg(json_extract(summary,'$.measured_nps')) mean_nps,
        min(json_extract(summary,'$.measured_nps')) min_nps,max(json_extract(summary,'$.measured_nps')) max_nps,
        avg(json_extract(summary,'$.elapsed_seconds')) mean_seconds
        FROM experiment_attempts WHERE eid=? AND json_extract(summary,'$.official')=1
        AND json_extract(summary,'$.reason')='completed'
        GROUP BY json_extract(summary,'$.profile_slot'),json_extract(summary,'$.profile'),json_extract(summary,'$.effective_threads')""",(eid,)) if row['kind']=='benchmark' else []
    body='body' if limit is None else "json_remove(body,'$.log','$.profile_snapshot') body"
    row['results']=[{'attempt_id':a['id'],'number':a['number'],'started':a['started'],'ended':a['ended'],**json.loads(a['body'])} for a in store.rows(f'SELECT id,number,started,ended,{body} FROM experiment_attempts WHERE eid=? ORDER BY number,started,id LIMIT ? OFFSET ?',(eid,-1 if limit is None else limit,offset))]
    if limit is not None:
        row.pop('cases');row['profiles']=[{'name':p['name']} for p in row['profiles']]
    return row

def state(store,eid,value):
    if value not in ('running','paused'):raise ValueError('Invalid experiment state')
    job=store.one('SELECT cursor,total FROM experiments WHERE id=?',(eid,))
    if not job:raise ValueError('Experiment not found')
    with store.tx():store.db.execute('UPDATE experiments SET state=? WHERE id=?',('completed' if job['cursor']>=job['total'] else value,eid))

def claim(store,eid):
    job=store.one('SELECT * FROM experiments WHERE id=?',(eid,))
    if not job:raise ValueError('Experiment not found')
    for key in ('settings','profiles','cases'):job[key]=json.loads(job[key])
    if job['state']!='running':return None
    if job['cursor']>=job['total']:
        with store.tx():store.db.execute("UPDATE experiments SET state='completed' WHERE id=?",(eid,))
        return None
    if store.one('SELECT id FROM experiment_attempts WHERE eid=? AND ended IS NULL',(eid,)):return None
    index=job['cursor'];count=case_count(job['cases']);slot=index//count
    profile=copy.deepcopy(job['profiles'][slot]);case=case_at(job['cases'],index%count)
    if 'threads' in case:
        profile['threads']=case['threads']
        from .engine_options import find_name
        key=find_name(profile.get('options',{}),'Threads')
        if key:profile['options'][key]=case['threads']
    aid=uid();body={'profile':profile['name'],'profile_slot':slot,'profile_snapshot':profile,'case':case,'official':False}
    with store.tx():store.db.execute('INSERT INTO experiment_attempts(id,eid,number,started,ended,body,summary) VALUES(?,?,?,?,?,?,?)',(aid,eid,index,now(),None,encode(body),metrics(body)))
    return {'id':aid,'eid':eid,'number':index,'profile':profile,'case':case,'settings':job['settings'],'kind':job['kind']}

def finish(store,case,result):
    row=store.one('SELECT * FROM experiment_attempts WHERE id=?',(case['id'],))
    if not row or row['eid']!=case['eid'] or row['number']!=case['number']:raise ValueError('Experiment attempt does not match its case')
    if row['ended'] is not None:return False
    body=json.loads(row['body'])|result
    with store.tx():
        store.db.execute('UPDATE experiment_attempts SET ended=?,body=?,summary=? WHERE id=?',(now(),encode(body),metrics(body),case['id']))
        if result.get('official'):store.db.execute("UPDATE experiments SET cursor=cursor+1,state=CASE WHEN cursor+1>=total THEN 'completed' ELSE state END WHERE id=? AND cursor=?",(case['eid'],case['number']))
        else:store.db.execute("UPDATE experiments SET state='paused' WHERE id=?",(case['eid'],))
    return True

async def execute(db,case):
    settings=case['settings']|{'ponder':False};engine=UciEngine(case['profile'],settings);board=chess.Board(case['case']['fen']);start=None;solved=None;stable=None
    def correct(move):
        c=case['case'];return (not c.get('bm') or move in c['bm']) and move not in c.get('am',[])
    def info_hook(info):
        nonlocal solved,stable
        if case['kind']!='suite' or not engine.last_update.get('pv'):return
        try:move=board.parse_uci(info['pv'].split()[0]);matches=bool(move) and correct(move.uci())
        except ValueError:matches=False
        if matches:
            elapsed=time.perf_counter()-engine.search_started
            if solved is None:solved=elapsed
            if stable is None:stable=elapsed
        else:stable=None
    result={'official':True}
    try:
        await engine.start()
        from .engine_options import find_name
        options=engine.runtime.get('options',{});effective=options.get(find_name(options,'Threads'))
        result.update(effective_threads=effective,identity=engine.identity,runtime=engine.runtime)
        if case['kind']=='benchmark' and effective!=case['case']['threads']:raise EngineFailure('protocol_error','Thread-scaling benchmark requires an advertised Threads option matching the requested count')
        engine.info_hook=info_hook;clock=Clock(TimeControl.parse(settings['time_control']));start=time.perf_counter()
        move,elapsed,info=await engine.play(board,go_command(clock,clock,clock),clock.budget)
        result.update(move=move.uci(),san=board.san(move),elapsed_seconds=elapsed,reported_nodes=info.get('nodes'),reported_nps=info.get('nps'),measured_nps=info['nodes']/elapsed if info.get('nodes') is not None and elapsed else None,info=info,reason='completed',identity=engine.identity)
        if case['kind']=='suite':result.update(correct=correct(move.uci()),first_correct_pv_seconds=solved,time_to_solve_seconds=min(elapsed,stable if stable is not None else elapsed) if correct(move.uci()) else None,solve_definition='final_uninterrupted_correct_pv')
    except EngineFailure as e:result.update(correct=False,reason=e.reason,detail=str(e))
    except asyncio.CancelledError:result.update(official=False,reason='interrupted',detail='Experiment stopped; current case restarts on resume')
    except Exception as e:result.update(official=False,reason='interrupted',detail=str(e))
    finally:
        await engine.close();result['log']=list(engine.log);await db.call('experiment_finish',case,result)
