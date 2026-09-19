"""Live CPU acceptance; enable the reader in an isolated desktop before running.

Usage: python scripts/validate_cpu_sensors_portable.py --ready PATH --desktop-pid PID
The supplied fixture must be below test-output. Its desktop is force-terminated
after play to check elevated-reader cleanup, then restarted to check persistence.
"""
import argparse
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
args=argparse.ArgumentParser();args.add_argument('--ready',type=Path,required=True);args.add_argument('--desktop-pid',type=int,required=True)
args=args.parse_args();ready=args.ready.resolve();DATA=ready.parent
assert DATA.is_relative_to(ROOT/'test-output'),'Only isolated acceptance data may be used'
info=json.loads(ready.read_text(encoding='utf-8'));desktop=psutil.Process(args.desktop_pid)
assert Path(desktop.exe()).resolve()==ROOT/'release/EngineArena/EngineArena.exe'
assert str(DATA) in ' '.join(desktop.cmdline())

def api(path,body=None):
    request=urllib.request.Request(f"http://127.0.0.1:{info['port']}/api/{path}",
        data=None if body is None else json.dumps(body).encode(),
        headers={'X-Arena-Token':info['token'],'Content-Type':'application/json'})
    with urllib.request.urlopen(request,timeout=20) as response:return json.load(response)

def sensor_pids():
    return {p.info['pid'] for p in psutil.process_iter(['pid','name']) if p.info['name']=='ArenaSensors.exe'}

snapshot=api('hardware');assert snapshot['cpu']['status']=='ok',snapshot['cpu']
selected=snapshot['cpu_selected'];baseline=sensor_pids();assert baseline
config={'fields':['cpu_percent','cpu_temperature','ram_used','gpu_temperature','active_games'],
        'interval':2,'gpu':'auto','cpu_sensor':selected['id'],'temperature_unit':'F'}
api('preferences',{'hardware':config})
paths=['validation-engines/stockfish/stockfish/stockfish-windows-x86-64-universal.exe','validation-engines/berserk-14-avx2.exe']
profiles=[api('profiles',{'name':'CPU temperature acceptance '+str(i+1),'path':str(ROOT/path),'threads':1,'hash':16,'discover':True}) for i,path in enumerate(paths)]
t=api('tournaments',{'name':'CPU sensor acceptance','profiles':[p['id'] for p in profiles],
    'settings':{'format':'match','cycles':12,'paired':True,'concurrency':4,'time_control':{'kind':'nodes','nodes':150000},'max_plies':32}})
api(f'tournaments/{t["id"]}/action',{'action':'start'})
deadline=time.monotonic()+120;latencies=[];samples={};active_samples=0
while time.monotonic()<deadline:
    start=time.perf_counter();status=api('status');latencies.append((time.perf_counter()-start)*1000)
    assert not status['error'];h=status['hardware']
    if h.get('sampled_at') and h['cpu']['status']=='ok':
        samples[h['sampled_at']]=h
        if status['active_games']:active_samples+=1
    result=api(f'tournaments/{t["id"]}')
    if result['state']=='completed':break
    time.sleep(.25)
assert result['official_games']==24 and result['complete_pairs']==12
assert len(samples)>=3 and active_samples>=3
temperatures=[h['metrics']['cpu_temperature'] for h in samples.values()]
assert all(0<v<150 for v in temperatures)
assert len(set(temperatures))>1,'Expected live changing sensor readings'
assert all(h['cpu_selected']['id']==selected['id'] and not h['stale'] for h in samples.values())
# Force the desktop down while its reader is active: the reader watches the
# original process handle, so even PID reuse cannot leave it attached elsewhere.
desktop.kill();desktop.wait(10);deadline=time.monotonic()+10
while baseline & sensor_pids() and time.monotonic()<deadline:time.sleep(.1)
assert not baseline & sensor_pids(),'Elevated CPU reader outlived the desktop'
try:psutil.Process(info['pid']).wait(10)
except psutil.NoSuchProcess:pass
before=(DATA/'games.pgn').read_bytes();stream=io.StringIO(before.decode());games=[]
while game:=chess.pgn.read_game(stream):
    assert not game.errors;games.append(game)
assert len(games)==24 and len({g.headers['AttemptId'] for g in games})==24
prior=info
restarted=subprocess.Popen([str(ROOT/'release/EngineArena/EngineArena.exe'),'--data',str(DATA)],creationflags=subprocess.CREATE_NO_WINDOW)
try:
    deadline=time.monotonic()+45
    while time.monotonic()<deadline:
        try:
            current=json.loads(ready.read_text(encoding='utf-8'))
            if current['pid']==prior['pid']:time.sleep(.1);continue
            info=current;api('status');break
        except (OSError,ValueError):time.sleep(.1)
    assert api('preferences')['hardware']==config
    assert api(f'tournaments/{t["id"]}')['official_games']==24
    restarted_sensors=api('hardware')
    assert restarted_sensors['cpu']['status']=='access_denied'
    assert restarted_sensors['metrics']['cpu_temperature'] is None
    assert 'Enable CPU readings' in restarted_sensors['cpu']['message']
    api('shutdown',{})
    try:psutil.Process(info['pid']).wait(20)
    except psutil.NoSuchProcess:pass
finally:
    if restarted.poll() is None:restarted.terminate();restarted.wait(10)
assert (DATA/'games.pgn').read_bytes()==before
db=sqlite3.connect(DATA/'arena.sqlite3')
commands=[r[0].split('> ',1)[-1] for r in db.execute("SELECT line FROM logs WHERE line LIKE '%> go %'")];db.close()
assert len(commands)==768 and all(c=='go nodes 150000' for c in commands)
latency=sorted(latencies)
report={'date':time.strftime('%Y-%m-%d'),'data_directory':str(DATA),'actual_cpu_readings_verified':True,
    'driver_installation':'installed with user approval','driver_version':'2.2.0','authenticode_status':'Valid','authenticode_signer':'namazso.eu',
    'driver_installer_sha256':'1f519a22e47187f70a1379a48ca604981c4fcf694f4e65b734aaa74a9fba3032',
    'sensor_library':'LibreHardwareMonitorLib 0.9.6','hardware':snapshot['identity'],'sensors':snapshot['cpu']['sensors'],
    'portable':{'games':24,'pairs':12,'concurrency':4,'node_only_commands':len(commands),'unique_samples_during_play':len(samples),
        'temperature_min_c':min(temperatures),'temperature_max_c':max(temperatures),'status_requests':len(latency),
        'status_median_ms':round(latency[len(latency)//2],2),'status_p95_ms':round(latency[int(.95*len(latency))],2),
        'sensor_collection_max_ms':max(h['collection_ms'] for h in samples.values()),
        'reader_exits_after_forced_desktop_termination':True,'settings_and_results_survive_restart':True,
        'restart_requires_explicit_reader_permission':True,'legal_unique_unchanged_pgn':True},
    'scope':'Actual CPU die readings verified on this Threadripper. No independent thermometer calibration, other CPU families, or throughput-neutrality guarantee.'}
(ROOT/'test-output/cpu-sensors-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2),flush=True)
