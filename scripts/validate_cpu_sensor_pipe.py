"""Check the real sensor pipe after GUI permission, using isolated test data."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import time

import psutil

ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser();parser.add_argument('--ready',type=Path,required=True);args=parser.parse_args()
ready=args.ready.resolve();assert ready.is_relative_to(ROOT/'test-output')
info=json.loads(ready.read_text(encoding='utf-8'))
pipe=psutil.Process(info['pid']).environ()['ARENA_CPU_SENSOR_PIPE'];path='\\\\.\\pipe\\'+pipe
env=dict(os.environ,ARENA_CPU_SENSOR_PIPE=pipe)

def read():
    result=subprocess.run([str(ROOT/'release/EngineArena/ArenaSensors.exe')],env=env,capture_output=True,text=True,
        encoding='utf-8',timeout=6,creationflags=subprocess.CREATE_NO_WINDOW,check=True)
    value=json.loads(result.stdout);assert value['status']=='ok',value
    assert value['sensors'] and all(0<s['celsius']<150 for s in value['sensors'])
    return value

sample=read()
try:
    with open(path,'wb',buffering=0):pass
except PermissionError:pass
else:raise AssertionError('Sensor pipe accepted write access')
start=time.perf_counter()
for _ in range(100):read()
elapsed=time.perf_counter()-start
for _ in range(3):
    # A consumer that opens the pipe but never reads must not prevent the next
    # reading. Disconnecting after the bounded drain releases the pending IO.
    with open(path,'rb',buffering=0):time.sleep(2.5)
    read()
for _ in range(20):
    with open(path,'rb',buffering=0):pass
    read()
report={'consecutive_valid_reads':100,'elapsed_seconds':round(elapsed,3),
        'write_access_denied':True,'stalled_readers_recovered':3,'early_disconnects_recovered':20,'sample':sample}
(ROOT/'test-output/cpu-sensors-pipe-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2),flush=True)
