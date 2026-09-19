"""Force-terminate the actual WPF application and verify recovery after relaunch."""
import io
import json
import os
from pathlib import Path
import subprocess
import time
import urllib.error
import urllib.request
import chess.pgn
import psutil
import argparse
import sqlite3

ROOT=Path(__file__).resolve().parent.parent
parser=argparse.ArgumentParser();parser.add_argument('--portable',action='store_true');parser.add_argument('--prepare',action='store_true');args=parser.parse_args()
DATA=ROOT/'test-output'/('portable-data' if args.portable else 'desktop-data')
READY=DATA/'worker-ready.json'
EXE=ROOT/'release'/'EngineArena'/'EngineArena.exe' if args.portable else ROOT/'desktop'/'bin'/'Release'/'net10.0-windows'/'EngineArena.exe'
info=json.loads(READY.read_text());old_worker=info['pid']
def api(path,body=None):
    req=urllib.request.Request(f"http://127.0.0.1:{info['port']}/api/"+path,data=json.dumps(body).encode() if body is not None else None,headers={'X-Arena-Token':info['token'],'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=15) as r:return json.load(r)

if args.prepare:
    # Repeated portable smoke runs can register several profiles of one binary.
    # Select distinct executables so this acceptance run still uses both engines.
    profiles=list({p['path'].casefold():p for p in api('profiles?limit=10000')['items']}.values());assert len(profiles)>=2
    t=api('tournaments',{'name':'Portable forced-termination acceptance','profiles':[p['id'] for p in profiles[:2]],'settings':{'cycles':16,'concurrency':4,'time_control':{'kind':'nodes','nodes':500000},'max_plies':120}})
    tid=t['id'];api('tournaments/'+tid+'/action',{'action':'start'});deadline=time.monotonic()+120
    while time.monotonic()<deadline:
        snap=api('tournaments/'+tid);live=api('status')['live']
        if snap['official_games']>=2 and any(g['tid']==tid and g['ply']>=5 for g in live):break
        time.sleep(.1)
    else:raise AssertionError('Prepared crash tournament did not reach completed and midgame results')
else:
    tournaments=api('tournaments');tid=next(t['id'] for t in tournaments if t['state']=='running')
before=api('tournaments/'+tid);games=api('tournaments/'+tid+'/games')['items'];observed_official={g['id']:g['official'] for g in games if g['official']};observed_running=[api('games/'+g['id']) for g in games if g['state']=='running']
api('tournaments/'+tid+'/ratings',{'slot':1,'rating':2800})
pool_before=api('tournaments/'+tid+'/ratings') # Also exercises cleanup of the fitting subprocess.
deadline=time.monotonic()+60
while time.monotonic()<deadline:
    live=api('status')['live']
    if any(g['tid']==tid and g['ply']>=10 for g in live):break
    time.sleep(.05)
else:raise AssertionError('No midgame was available after warming the rating subprocess')
games=api('tournaments/'+tid+'/games')['items'];observed_official={g['id']:g['official'] for g in games if g['official']};observed_running=[api('games/'+g['id']) for g in games if g['state']=='running']
assert observed_running and observed_official,'Crash injection requires both completed and active games'
parent=next(p for p in psutil.Process(old_worker).parents() if Path(p.exe()).resolve()==EXE.resolve())
descendants=[(p.pid,p.create_time()) for p in parent.children(recursive=True)]
parent.kill();parent.wait(15)
time.sleep(.5)
survivors=[]
for pid,created in descendants:
    try:
        p=psutil.Process(pid)
        if abs(p.create_time()-created)<.01 and p.is_running():survivors.append(pid)
    except psutil.NoSuchProcess:pass
assert not survivors,('Descendant processes survived the killed application',survivors)
# A game can finish between an HTTP observation and the actual process kill.
# Read the committed crash boundary after all descendants have exited and before
# app recovery; this distinguishes legitimate late completions from lost games.
with sqlite3.connect((DATA/'arena.sqlite3').as_uri()+'?mode=ro',uri=True) as crash_db:
    crash_db.row_factory=sqlite3.Row
    at_crash=[dict(g) for g in crash_db.execute('SELECT * FROM games WHERE tid=? AND invalid=0',(tid,))]
    official={g['id']:g['official'] for g in at_crash if g['official']}
    running=[]
    for g in at_crash:
        if g['state']!='running':continue
        a=dict(crash_db.execute('SELECT * FROM attempts WHERE gid=? ORDER BY seq DESC LIMIT 1',(g['id'],)).fetchone())
        g['opening']=json.loads(g['opening']);g['aid_at_crash']=a['id'];g['move_count_at_crash']=crash_db.execute('SELECT count(*) FROM moves WHERE aid=?',(a['id'],)).fetchone()[0];running.append(g)
assert running,'Force termination missed active games; rerun with a longer search'
assert sum(g['move_count_at_crash'] for g in running)>0,'Crash injection missed committed midgame moves'
assert all(official.get(gid)==aid for gid,aid in observed_official.items())
(ROOT/'test-output'/'crash-boundary.json').write_text(json.dumps({'tournament':tid,'official':official,'running':running},indent=2),encoding='utf-8')
proc=subprocess.Popen([str(EXE),'--data',str(DATA)],creationflags=subprocess.CREATE_NO_WINDOW)
deadline=time.time()+60
while time.time()<deadline:
    try:
        current=json.loads(READY.read_text())
        if current['pid']!=old_worker:
            info=current;after=api('tournaments/'+tid);break
    except (OSError,ValueError,urllib.error.URLError):pass
    time.sleep(.1)
else:raise AssertionError('Relaunched desktop did not become ready')
assert after['state']=='paused'
pool_after=api('tournaments/'+tid+'/ratings');assert pool_after['anchor']['slot']==1 and pool_after['anchor']['rating']==2800
assert pool_after['samples']==after['complete_pairs']
for gid,aid in official.items():assert api('games/'+gid)['official']==aid
for g in running:
    recovered=api('games/'+g['id']);assert recovered['state']=='pending';assert recovered['opening']==g['opening']
    old=next(a for a in recovered['attempts'] if a['id']==g['aid_at_crash']);assert old['reason']=='interrupted';assert len(old['moves'])==g['move_count_at_crash']
api('tournaments/'+tid+'/action',{'action':'start'})
deadline=time.time()+20
while time.time()<deadline:
    live=api('status')['live']
    if len([g for g in live if g['tid']==tid])>=len(running):break
    time.sleep(.1)
assert len([g for g in live if g['tid']==tid])>=len(running)
api('tournaments/'+tid+'/action',{'action':'cancel'})
f=io.StringIO((DATA/'games.pgn').read_text(encoding='utf-8'));pgn_ids=[]
while g:=chess.pgn.read_game(f):assert not g.errors;pgn_ids.append(g.headers['AttemptId'])
assert len(pgn_ids)==len(set(pgn_ids))
report={'portable_build':args.portable,'forced_application_termination':True,'old_worker_pid':old_worker,'restarted_worker_pid':info['pid'],'retained_official_results':len(official),'completed_between_observation_and_kill':len(official)-len(observed_official),'interrupted_games_requeued':len(running),'preserved_move_records':sum(g['move_count_at_crash'] for g in running),'orphan_processes':survivors,'resumed_live_games':len(live),'pgn_attempts':len(pgn_ids),'pgn_duplicates':0,'recovered_state':after['state']}
report.update(rating_reference_recovered=True,recovered_rating_samples=pool_after['samples'])
(ROOT/'test-output'/('portable-crash-report.json' if args.portable else 'desktop-crash-report.json')).write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report))
