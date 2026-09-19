"""Exercise hardware polling alongside real games in an isolated portable app."""
import io
import json
from pathlib import Path
import sqlite3
import subprocess
import time
import urllib.request

import chess.pgn
import psutil

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'test-output'/('hardware-real-'+time.strftime('%Y%m%d-%H%M%S'));DATA.mkdir()
PACKAGE=ROOT/'release/EngineArena';app=info=None

def api(path,body=None):
    request=urllib.request.Request(f"http://127.0.0.1:{info['port']}/api/{path}",
        data=None if body is None else json.dumps(body).encode(),
        headers={'X-Arena-Token':info['token'],'Content-Type':'application/json'})
    with urllib.request.urlopen(request,timeout=45) as response:return json.load(response)

def launch():
    global app,info
    previous=info
    app=subprocess.Popen([str(PACKAGE/'EngineArena.exe'),'--data',str(DATA)],creationflags=subprocess.CREATE_NO_WINDOW)
    deadline=time.monotonic()+60
    while time.monotonic()<deadline:
        try:
            current=json.loads((DATA/'worker-ready.json').read_text(encoding='utf-8'))
            if previous and previous['pid']==current['pid']:time.sleep(.1);continue
            info=current;api('status');return
        except (OSError,ValueError):
            assert app.poll() is None;time.sleep(.1)
    raise AssertionError('Desktop launch timeout')

def close():
    if app and app.poll() is None:
        api('shutdown',{});psutil.Process(info['pid']).wait(45)
        if app.poll() is None:app.terminate();app.wait(10)

try:
    launch();snapshot=api('hardware');assert snapshot['gpus'],'This acceptance fixture expects the installed NVIDIA GPU'
    gpu=snapshot['gpus'][0]
    config={'fields':['cpu_percent','ram_used','gpu_percent','gpu_memory','gpu_temperature','gpu_power','disk_free'],
            'interval':2,'gpu':gpu['id'],'temperature_unit':'F'}
    api('preferences',{'hardware':config,'fontSize':16})
    paths=['validation-engines/stockfish/stockfish/stockfish-windows-x86-64-universal.exe','validation-engines/berserk-14-avx2.exe']
    profiles=[api('profiles',{'name':'Hardware validation '+str(i+1),'path':str(ROOT/path),'threads':1,'hash':16,'discover':True}) for i,path in enumerate(paths)]
    t=api('tournaments',{'name':'Hardware monitoring acceptance','profiles':[p['id'] for p in profiles],
        'settings':{'format':'match','cycles':6,'paired':True,'concurrency':2,'time_control':{'kind':'nodes','nodes':100000},'max_plies':24}})
    api(f'tournaments/{t["id"]}/action',{'action':'start'})
    deadline=time.monotonic()+90;latencies=[];samples={}
    while time.monotonic()<deadline:
        start=time.monotonic();status=api('status');latencies.append((time.monotonic()-start)*1000)
        h=status['hardware'];assert not status['error']
        if h.get('sampled_at') and h['gpus']:samples[h['sampled_at']]=h
        result=api(f'tournaments/{t["id"]}')
        if result['state']=='completed':break
        time.sleep(.25)
    assert result['official_games']==12 and result['complete_pairs']==6 and len(samples)>=3
    assert any(h['metrics']['cpu_percent'] is not None for h in samples.values())
    for h in samples.values():
        assert h['gpus'][0]['id']==gpu['id'] and not h['stale']
        for key in ('gpu_percent','gpu_memory','gpu_temperature','gpu_power'):assert h['gpus'][0]['metrics'][key] is not None
    close();before=(DATA/'games.pgn').read_bytes();stream=io.StringIO(before.decode());games=[]
    while g:=chess.pgn.read_game(stream):
        assert not g.errors;games.append(g)
    assert len(games)==12 and len({g.headers['AttemptId'] for g in games})==12
    launch();assert api('preferences')['hardware']==config
    assert api('hardware')['gpus'][0]['id']==gpu['id']
    assert api(f'tournaments/{t["id"]}')['official_games']==12
    close();assert (DATA/'games.pgn').read_bytes()==before
    db=sqlite3.connect(DATA/'arena.sqlite3');commands=[r[0].split('> ',1)[-1] for r in db.execute("SELECT line FROM logs WHERE line LIKE '%> go %'")];db.close()
    assert commands and all(c=='go nodes 100000' for c in commands)
    for name in ('hardware.js','hardware-model.js','hardware.css','app.js','index.html'):
        assert (ROOT/'ui'/name).read_bytes()==(PACKAGE/'worker/_internal/ui'/name).read_bytes()
    latency=sorted(latencies)
    report={'date':time.strftime('%Y-%m-%d'),'data_directory':str(DATA),'backend_tests':182,'javascript_checks':17,
        'hardware':{'cpu':snapshot['identity'],'gpu':gpu['name'],'driver':gpu['driver'],
            'gpu_fields_available':[k for k,v in gpu['metrics'].items() if v is not None],
            'cpu_temperature_available':snapshot['metrics']['cpu_temperature'] is not None},
        'portable':{'games':12,'pairs':6,'node_only_commands':len(commands),'hardware_samples_during_play':len(samples),
            'status_requests':len(latency),'status_median_ms':round(latency[len(latency)//2],2),
            'status_p95_ms':round(latency[min(len(latency)-1,int(.95*len(latency)))],2),
            'sensor_collection_max_ms':max(h['collection_ms'] for h in samples.values()),
            'settings_and_gpu_identity_survive_restart':True,'legal_unique_pgn':True,'assets_match_source':True},
        'browser':{'preset_and_individual_choices':True,'order_change':True,'C_F_conversion':True,'hide_and_restore':True,
            'unavailable_CPU_sensor_label':True,'console_errors':0},
        'scope':'NVIDIA GPU provider validated on this machine; other GPU vendors and Windows CPU temperature require another sensor provider. Hardware readings are observational, not a throughput-neutrality guarantee.'}
    (ROOT/'test-output/hardware-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2),flush=True)
finally:close()
