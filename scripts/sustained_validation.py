"""Full-game node-only desktop load with worker and browser telemetry."""
import io
import json
from pathlib import Path
import statistics
import time
import urllib.request
import chess.pgn

ROOT=Path(__file__).resolve().parent.parent
ready=json.loads((ROOT/'test-output'/'desktop-data'/'worker-ready.json').read_text());base=f"http://127.0.0.1:{ready['port']}/api/"
def api(path,body=None,raw=False):
    request=urllib.request.Request(base+path,data=json.dumps(body).encode() if body is not None else None,headers={'X-Arena-Token':ready['token'],'Content-Type':'application/json'})
    with urllib.request.urlopen(request,timeout=60) as r:return r.read().decode() if raw else json.load(r)

profiles=api('profiles')['items'];assert len(profiles)==2
t=api('tournaments',{'name':'Sustained responsiveness acceptance · 512 full games · 32 concurrent','profiles':[p['id'] for p in profiles],'settings':{'cycles':256,'concurrency':32,'time_control':{'kind':'nodes','nodes':100000},'max_plies':0,'retry_limit':0,'cpu_budget':32,'hang_timeout':300}})
api(f"tournaments/{t['id']}/action",{'action':'start'})
print('Running tournament '+t['id']+' with '+str(t['total'])+' full games',flush=True)
start=time.monotonic();samples=[];latencies=[];last_print=0
while time.monotonic()-start<1800:
    before=time.perf_counter();snap=api('tournaments/'+t['id']);latencies.append((time.perf_counter()-before)*1000)
    status=api('status');elapsed=time.monotonic()-start
    samples.append({'elapsed':elapsed,'official':snap['official_games'],'active':status['active_games'],'cpu_percent':status['cpu_percent'],'memory_used_gb':status['memory_used_gb'],'ui':status.get('ui_metrics')})
    if status['error']:raise AssertionError(status['error'])
    if elapsed-last_print>=20:print(f"{elapsed:.1f}s: {snap['official_games']}/{t['total']} completed, {status['active_games']} active",flush=True);last_print=elapsed
    if snap['state']=='completed':break
    time.sleep(1)
assert snap['state']=='completed',snap['state']
stream=io.StringIO(api('export/'+t['id']+'/pgn',raw=True));games=[]
while game:=chess.pgn.read_game(stream):assert not game.errors;games.append(game)
assert len(games)==t['total'] and len({g.headers['GameId'] for g in games})==t['total']
assert all(g.headers['Termination'] not in ('max_plies_adjudication','interrupted','crash','hang','illegal_move','timeout') for g in games)
report={'tournament':t['id'],'settings':t['settings'],'elapsed_seconds':elapsed,'games':len(games),'peak_concurrency':max(s['active'] for s in samples),'snapshot_p50_ms':statistics.median(latencies),'snapshot_p95_ms':sorted(latencies)[int(len(latencies)*.95)],'pg_errors':0,'terminations':{r:sum(g.headers['Termination']==r for g in games) for r in {g.headers['Termination'] for g in games}},'samples':samples}
(ROOT/'test-output'/'sustained-report.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k not in ('samples','settings')},indent=2))
