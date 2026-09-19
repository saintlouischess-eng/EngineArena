"""Durable EPD best/avoid suites and reproducible node/thread benchmarks."""
import asyncio
import copy
import json
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
        board=chess.Board();operations=board.set_epd(line)
        if not board.is_valid():raise ValueError(f'Invalid EPD on line {number}')
        bm=[m.uci() for m in operations.get('bm',[])];am=[m.uci() for m in operations.get('am',[])]
        if not bm and not am:raise ValueError(f'EPD line {number} has no bm or am operation')
        cases.append({'fen':board.fen(),'id':str(operations.get('id',number)),'bm':bm,'am':am})
    if not cases:raise ValueError('No EPD test cases found')
    return cases

def initialize(store):
    store.db.executescript('''
    CREATE TABLE IF NOT EXISTS experiments(id TEXT PRIMARY KEY,name TEXT,kind TEXT,state TEXT,created REAL,settings TEXT,profiles TEXT,cases TEXT,total INTEGER,cursor INTEGER DEFAULT 0);
    CREATE TABLE IF NOT EXISTS experiment_attempts(id TEXT PRIMARY KEY,eid TEXT,number INTEGER,started REAL,ended REAL,body TEXT);
    CREATE INDEX IF NOT EXISTS experiments_queue ON experiments(state,created);
    CREATE INDEX IF NOT EXISTS experiment_results ON experiment_attempts(eid,number);
    ''')
    with store.tx():
        store.db.execute("UPDATE experiments SET state='paused' WHERE state='running'")
        for row in store.rows('SELECT id,body FROM experiment_attempts WHERE ended IS NULL'):
            body=json.loads(row['body']);body.update(reason='interrupted',detail='Worker interrupted; case can restart on resume')
            store.db.execute('UPDATE experiment_attempts SET ended=?,body=? WHERE id=?',(now(),encode(body),row['id']))

def create(store,name,kind,profiles,settings,path=None):
    if not profiles:raise ValueError('Select at least one engine profile')
    s=DEFAULTS|settings;tc=TimeControl.parse(s['time_control'])
    if tc.kind not in ('nodes','depth','movetime'):raise ValueError('Suites and benchmarks require nodes, depth or fixed move time')
    if kind=='suite':cases=parse_suite(path)
    elif kind=='benchmark':
        threads=settings.get('thread_counts',[1,2,4,8]);repeats=settings.get('repeats',3)
        if not threads or any(not isinstance(n,int) or n<1 for n in threads):raise ValueError('Thread counts must be positive integers')
        if not isinstance(repeats,int) or repeats<1:raise ValueError('Positive repeat count required')
        board=chess.Board(settings.get('fen',chess.STARTING_FEN))
        if not board.is_valid():raise ValueError('Invalid benchmark position')
        cases=[{'id':f'{n} threads / repeat {r+1}','fen':board.fen(),'threads':n,'repeat':r+1} for n in threads for r in range(repeats)]
    else:raise ValueError('Unknown experiment kind')
    eid=uid()
    with store.tx():
        store.db.execute('INSERT INTO experiments(id,name,kind,state,created,settings,profiles,cases,total) VALUES(?,?,?,?,?,?,?,?,?)',(eid,name,kind,'paused',now(),encode(s),encode(profiles),encode(cases),len(profiles)*len(cases)))
        store.audit(eid,'experiment_created',{'kind':kind,'cases':len(cases),'profiles':len(profiles)})
    return get(store,eid)

def get(store,eid):
    row=store.one('SELECT * FROM experiments WHERE id=?',(eid,))
    if not row:raise ValueError('Experiment not found')
    for key in ('settings','profiles','cases'):row[key]=json.loads(row[key])
    row['results']=[{'attempt_id':a['id'],'number':a['number'],'started':a['started'],'ended':a['ended'],**json.loads(a['body'])} for a in store.rows('SELECT * FROM experiment_attempts WHERE eid=? ORDER BY number,started',(eid,))]
    official=[r for r in row['results'] if r.get('official')]
    row['completed']=len(official);row['correct']=sum(r.get('correct') is True for r in official);row['accuracy_pct']=100*row['correct']/len(official) if official and row['kind']=='suite' else None
    return row

def state(store,eid,value):
    if value not in ('running','paused'):raise ValueError('Invalid experiment state')
    with store.tx():store.db.execute('UPDATE experiments SET state=? WHERE id=?',(value,eid))

def claim(store,eid):
    job=store.one('SELECT * FROM experiments WHERE id=?',(eid,))
    if not job:raise ValueError('Experiment not found')
    for key in ('settings','profiles','cases'):job[key]=json.loads(job[key])
    if job['state']!='running':return None
    if job['cursor']>=job['total']:
        with store.tx():store.db.execute("UPDATE experiments SET state='completed' WHERE id=?",(eid,))
        return None
    index=job['cursor'];profile=copy.deepcopy(job['profiles'][index//len(job['cases'])]);case=job['cases'][index%len(job['cases'])]
    if 'threads' in case:
        profile['threads']=case['threads']
        for key in list(profile.get('options',{})):
            if key.casefold()=='threads':profile['options'][key]=case['threads']
    aid=uid();body={'profile':profile['name'],'profile_snapshot':profile,'case':case,'official':False}
    with store.tx():store.db.execute('INSERT INTO experiment_attempts VALUES(?,?,?,?,?,?)',(aid,eid,index,now(),None,encode(body)))
    return {'id':aid,'eid':eid,'number':index,'profile':profile,'case':case,'settings':job['settings'],'kind':job['kind']}

def finish(store,case,result):
    row=store.one('SELECT body FROM experiment_attempts WHERE id=?',(case['id'],));body=json.loads(row['body'])|result
    with store.tx():
        store.db.execute('UPDATE experiment_attempts SET ended=?,body=? WHERE id=?',(now(),encode(body),case['id']))
        if result.get('official'):store.db.execute('UPDATE experiments SET cursor=cursor+1 WHERE id=? AND cursor=?',(case['eid'],case['number']))
        else:store.db.execute("UPDATE experiments SET state='paused' WHERE id=?",(case['eid'],))

async def execute(db,case):
    settings=case['settings']|{'ponder':False};engine=UciEngine(case['profile'],settings);board=chess.Board(case['case']['fen']);start=None;solved=None
    def correct(move):
        c=case['case'];return (not c.get('bm') or move in c['bm']) and move not in c.get('am',[])
    def info_hook(info):
        nonlocal solved
        if case['kind']=='suite' and solved is None and info.get('pv') and correct(info['pv'].split()[0]):solved=time.perf_counter()-start
    result={'official':True}
    try:
        await engine.start();engine.info_hook=info_hook;clock=Clock(TimeControl.parse(settings['time_control']));start=time.perf_counter()
        move,elapsed,info=await engine.play(board,go_command(clock,clock,clock),clock.budget)
        result.update(move=move.uci(),san=board.san(move),elapsed_seconds=elapsed,reported_nodes=info.get('nodes'),reported_nps=info.get('nps'),measured_nps=info['nodes']/elapsed if info.get('nodes') is not None and elapsed else None,info=info,reason='completed',identity=engine.identity)
        if case['kind']=='suite':result.update(correct=correct(move.uci()),first_correct_pv_seconds=solved,time_to_solve_seconds=(solved if solved is not None else elapsed) if correct(move.uci()) else None)
    except EngineFailure as e:result.update(correct=False,reason=e.reason,detail=str(e))
    except asyncio.CancelledError:result.update(official=False,reason='interrupted',detail='Experiment stopped; current case restarts on resume')
    except Exception as e:result.update(official=False,reason='interrupted',detail=str(e))
    finally:
        await engine.close();result['log']=list(engine.log);await db.call('experiment_finish',case,result)
