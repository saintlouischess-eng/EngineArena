"""Close only this workspace's known validation instances after saving."""
import json
from pathlib import Path
import urllib.request
import psutil

ROOT=Path(__file__).resolve().parent.parent
allowed={str(p.resolve()).casefold() for p in (ROOT/'release'/'EngineArena'/'EngineArena.exe',ROOT/'test-output'/'native-build'/'EngineArena.exe',ROOT/'test-output'/'native-drop-build'/'EngineArena.exe',ROOT/'desktop'/'bin'/'Release'/'net10.0-windows'/'EngineArena.exe')}
for name in ('format-ui','portable-data','desktop-data','history-live','native-final','portable-isolated','focus-font','clocks-delete','polish','focus-search','live-boards-native'):
    ready=ROOT/'test-output'/name/'worker-ready.json'
    if not ready.exists():continue
    info=json.loads(ready.read_text())
    try:
        worker=psutil.Process(info['pid'])
        parent=next((p for p in worker.parents() if p.exe().casefold() in allowed),None)
        if parent is None:print(name+': no matching validation application');continue
        args=parent.cmdline()
        if '--data' not in args:raise RuntimeError('Expected an explicitly selected validation data directory')
        selected=Path(args[args.index('--data')+1])
        if not selected.is_absolute():selected=Path(parent.cwd())/selected
        if selected.resolve()!=(ROOT/'test-output'/name).resolve():raise RuntimeError('Data directory does not match the expected validation instance')
        req=urllib.request.Request(f"http://127.0.0.1:{info['port']}/api/shutdown",data=b'{}',headers={'X-Arena-Token':info['token'],'Content-Type':'application/json'})
        with urllib.request.urlopen(req,timeout=30) as response:response.read()
        worker.wait(120)
        if parent.is_running():parent.terminate();parent.wait(10)
        print(name+': worker saved and application closed')
    except psutil.NoSuchProcess:print(name+': already closed')
