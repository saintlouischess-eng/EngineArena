"""Validate packaged fastest-core readings during play; use an enabled fixture."""
import argparse
import io
import json
from pathlib import Path
import sqlite3
import time
import urllib.request

import chess.pgn

ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser();parser.add_argument('--ready',type=Path,required=True);args=parser.parse_args()
ready=args.ready.resolve();assert ready.is_relative_to(ROOT/'test-output')
info=json.loads(ready.read_text(encoding='utf-8'));data=ready.parent

def api(path,body=None):
    request=urllib.request.Request(f"http://127.0.0.1:{info['port']}/api/{path}",
        data=None if body is None else json.dumps(body).encode(),
        headers={'X-Arena-Token':info['token'],'Content-Type':'application/json'})
    with urllib.request.urlopen(request,timeout=20) as response:return json.load(response)

config={'fields':['cpu_fastest_clock','cpu_frequency','cpu_temperature','cpu_percent'],'interval':2,
        'gpu':'auto','cpu_sensor':'auto','temperature_unit':'C'}
api('preferences',{'hardware':config});assert api('preferences')['hardware']==config
samples=[];latencies=[]

def sample():
    before=time.perf_counter();value=api('hardware');latencies.append((time.perf_counter()-before)*1000)
    clocks=value['cpu']['clocks'];assert len(clocks)>=2
    fastest=max(clocks,key=lambda s:(s['mhz'],s['id']))
    assert value['cpu_fastest_core']==fastest
    assert value['metrics']['cpu_fastest_clock']==fastest['mhz']/1000
    assert not value['stale'] and value['metrics']['cpu_temperature'] is not None
    samples.append({'sampled_at':value['sampled_at'],'fastest':fastest,'ghz':value['metrics']['cpu_fastest_clock'],
        'nominal_ghz':value['metrics']['cpu_frequency'],'core_count':len(clocks),'collection_ms':value['collection_ms']})

sample()
paths=['validation-engines/stockfish/stockfish/stockfish-windows-x86-64-universal.exe','validation-engines/berserk-14-avx2.exe']
profiles=[api('profiles',{'name':'Clock validation '+str(i+1),'path':str(ROOT/path),'threads':1,'hash':16,'discover':True}) for i,path in enumerate(paths)]
t=api('tournaments',{'name':'Live clock validation','profiles':[p['id'] for p in profiles],
    'settings':{'format':'match','cycles':6,'paired':True,'concurrency':2,'time_control':{'kind':'nodes','nodes':150000},'max_plies':24}})
api(f'tournaments/{t["id"]}/action',{'action':'start'})
deadline=time.monotonic()+90
while time.monotonic()<deadline:
    sample();result=api(f'tournaments/{t["id"]}')
    if result['state']=='completed':break
    time.sleep(2)
assert result['official_games']==12 and result['complete_pairs']==6 and len(samples)>=3
assert len({s['ghz'] for s in samples})>1
assert any(abs(s['ghz']-s['nominal_ghz'])>.1 for s in samples)
stream=io.StringIO((data/'games.pgn').read_text(encoding='utf-8'));games=[]
while game:=chess.pgn.read_game(stream):
    assert not game.errors;games.append(game)
assert len(games)==12 and len({g.headers['AttemptId'] for g in games})==12
db=sqlite3.connect(data/'arena.sqlite3');commands=[r[0].split('> ',1)[-1] for r in db.execute("SELECT line FROM logs WHERE line LIKE '%> go %'")];db.close()
assert commands and all(c=='go nodes 150000' for c in commands)
report={'date':time.strftime('%Y-%m-%d'),'data_directory':str(data),'targeted_backend_tests':13,'javascript_checks':19,
    'live_core_count':samples[0]['core_count'],'min_fastest_ghz':min(s['ghz'] for s in samples),'max_fastest_ghz':max(s['ghz'] for s in samples),
    'nominal_ghz':samples[0]['nominal_ghz'],'samples':samples,'maximum_matches_reported_cores':True,'games':12,'pairs':6,
    'pure_node_commands':len(commands),'legal_unique_pgn':True,'settings_saved':True,
    'scope':'Current provider-reported operating clocks, sampled at the selected interval. No all-time maximum or effective-clock claim; other CPU families unverified.'}
(ROOT/'test-output/fastest-clock-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k!='samples'},indent=2),flush=True)
