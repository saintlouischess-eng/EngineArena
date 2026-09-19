"""Repeated worker-only / full-dashboard comparisons using identical games."""
import argparse
import csv
import io
import json
from pathlib import Path
import statistics
import time
import urllib.request
import uuid
import chess.pgn
import psutil

ROOT=Path(__file__).resolve().parent.parent
parser=argparse.ArgumentParser();parser.add_argument('phase');parser.add_argument('--prepare',action='store_true');parser.add_argument('--run',action='store_true');args=parser.parse_args()
ready=json.loads((ROOT/'test-output/graph-load-ready.json').read_text());base=f"http://127.0.0.1:{ready['port']}/api/"
def api(path,body=None,raw=False):
    req=urllib.request.Request(base+path,data=json.dumps(body).encode() if body is not None else None,headers={'X-Arena-Token':ready['token'],'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=60) as f:return f.read().decode() if raw else json.load(f)

current=ROOT/'test-output/graph-load-current.json';output=ROOT/'test-output/graph-load-results.json'
if args.run:
    t=json.loads(current.read_text());assert t['phase']==args.phase
else:
    assert api('status')['active_games']==0
    profiles=api('profiles')['items']
    if not profiles:
        for profile in json.loads((ROOT/'test-output/real-validation/report.json').read_text())['engines']:api('profiles',profile|{'discover':False})
        profiles=api('profiles')['items']
    assert len(profiles)==2
    settings={'cycles':128,'concurrency':32,'time_control':{'kind':'nodes','nodes':100000},'max_plies':0,'retry_limit':0,'cpu_budget':32,'hang_timeout':300}
    t=api('tournaments',{'name':'Graph load '+args.phase,'profiles':[p['id'] for p in profiles],'resource_preset':{'threads':1,'hash':32},'settings':settings})
    t['phase']=args.phase;current.write_text(json.dumps(t,indent=2),encoding='utf-8')
    if args.phase.startswith('live'):
        kinds=['evaluation','mate','wdl','depth','nodes','nps','moveTime','clock','hash','tablebase','cpu','memory','score','draw','elo','sprt'];graphs=[{'id':'graph-'+str(uuid.uuid4()),'kind':kind,'game':0,'slot':0,'ci':'conservative'} for kind in kinds]
        panels={g['id']:{'column':'right','visible':True,'height':440} for g in graphs}
        api('preferences',{'theme':'dark','pieceSet':'classic','boardCount':32,'light':'#dae1d6','dark':'#718e88','split':50,'panels':panels,'graphs':graphs,'layouts':{}})
    print(json.dumps({'phase':args.phase,'tournament':t['id'],'games':t['total'],'url':f"http://127.0.0.1:{ready['port']}/?token={ready['token']}"}),flush=True)
if args.prepare:raise SystemExit(0)
if args.phase.startswith('baseline'):api('ui-metrics',{'visible':False,'closed_for_baseline':True})
previous=json.loads(output.read_text()) if output.exists() else []
assert not any(r['phase']==args.phase for r in previous),'Choose a new phase label to preserve prior evidence'
api('tournaments/'+t['id']+'/action',{'action':'start'});started=time.monotonic();latencies=[];samples=[];last_progress=0;psutil.cpu_percent()
while time.monotonic()-started<1200:
    before=time.perf_counter();snapshot=api('tournaments/'+t['id']);latencies.append((time.perf_counter()-before)*1000)
    status=api('status');elapsed=time.monotonic()-started
    samples.append({'elapsed':elapsed,'official':snapshot['official_games'],'active':status['active_games'],'host_cpu':psutil.cpu_percent(),'host_used_gib':psutil.virtual_memory().used/2**30,'ui':status.get('ui_metrics')})
    assert not status['error'],status['error']
    if elapsed-last_progress>=20:print(f"{args.phase}: {elapsed:.1f}s, {snapshot['official_games']}/256 games, {status['active_games']} active",flush=True);last_progress=elapsed
    if snapshot['state']=='completed':break
    time.sleep(.5)
assert snapshot['state']=='completed'
text=api('export/'+t['id']+'/pgn',raw=True);stream=io.StringIO(text);ids=[]
while game:=chess.pgn.read_game(stream):
    assert not game.errors;ids.append(game.headers['GameId'])
    assert game.headers['Termination'] not in ('max_plies_adjudication','crash','hang','illegal_move','timeout','interrupted')
assert len(ids)==256 and len(set(ids))==256
record={'phase':args.phase,'tournament':t['id'],'games':256,'pairs':snapshot['complete_pairs'],'elapsed_seconds':elapsed,'peak_concurrency':max(s['active'] for s in samples),'snapshot_p50_ms':statistics.median(latencies),'snapshot_p95_ms':sorted(latencies)[int(.95*len(latencies))],'legal_unique_pgns':True,'samples':samples}
previous.append(record);output.write_text(json.dumps(previous,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in record.items() if k!='samples'}),flush=True)
