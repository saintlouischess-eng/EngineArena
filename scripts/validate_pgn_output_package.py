"""Exercise the packaged worker against disposable copied fixture data only."""
import contextlib,hashlib,json,os,sqlite3,subprocess,time,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
previous=json.loads((ROOT/'test-output/pgn-output-ready.json').read_text())
source=Path(previous['folder']).resolve();assert source.is_relative_to(ROOT/'test-output')
base=ROOT/'test-output'/('pgn-output-package-'+str(time.time_ns()));folder=base/'data';folder.mkdir(parents=True)
with contextlib.closing(sqlite3.connect((source/'arena.sqlite3').as_uri()+'?mode=ro',uri=True)) as src,contextlib.closing(sqlite3.connect(folder/'arena.sqlite3')) as dst:
    src.backup(dst)
    dst.execute("UPDATE tournaments SET state='paused'")
    for table in ('pgn_links','pgn_changes','pgn_targets'):dst.execute('DELETE FROM '+table)
    dst.execute("DELETE FROM preferences WHERE name IN ('ui','tournament_draft')")
    dst.commit()
ready_file=base/'worker-ready.json';log=(base/'worker.log').open('w',encoding='utf-8')
worker=ROOT/'release/EngineArena/worker/ArenaWorker.exe'
proc=subprocess.Popen([str(worker),'--data',str(folder),'--ready',str(ready_file)],stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
info=None
def api(endpoint,body=None):
    request=urllib.request.Request(f"http://127.0.0.1:{info['port']}/api/{endpoint}",headers={'X-Arena-Token':info['token'],'Content-Type':'application/json'},data=None if body is None else json.dumps(body).encode())
    with urllib.request.urlopen(request,timeout=30) as response:return json.load(response)
try:
    deadline=time.monotonic()+60
    while not ready_file.exists():
        if proc.poll() is not None or time.monotonic()>deadline:raise RuntimeError('Packaged PGN worker failed to start')
        time.sleep(.2)
    info=json.loads(ready_file.read_text());assert api('status')['active_games']==0
    ready=previous|{'folder':str(folder),'output':str(base/'packaged.pgn'),'url':f"http://127.0.0.1:{info['port']}/?token={info['token']}"}
    ready_path=base/'browser-ready.json';ready_path.write_text(json.dumps(ready))
    env=os.environ|{'ARENA_PGN_READY':str(ready_path),'ARENA_PGN_OUT':str(ROOT/'test-output/pgn-output-packaged')}
    subprocess.run(['node','scripts/validate_pgn_output.cjs'],cwd=ROOT,env=env,check=True,timeout=120,creationflags=subprocess.CREATE_NO_WINDOW)
    assert api('status')['active_games']==0
    # Restart the actual packaged process with the same data and destination.
    exported=Path(ready['output']);before=exported.read_bytes();api('shutdown',{});proc.wait(timeout=30)
    ready_file.unlink()
    proc=subprocess.Popen([str(worker),'--data',str(folder),'--ready',str(ready_file)],stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
    deadline=time.monotonic()+60
    while not ready_file.exists():
        if proc.poll() is not None or time.monotonic()>deadline:raise RuntimeError('Packaged restart failed')
        time.sleep(.2)
    info=json.loads(ready_file.read_text())
    deadline=time.monotonic()+30
    while True:
        status=api('status');outputs=status.get('pgn_outputs',[])
        if outputs and outputs[0]['state']=='saved':break
        assert not any(o.get('error') for o in outputs),outputs
        if time.monotonic()>deadline:raise RuntimeError('Packaged PGN recovery did not settle')
        time.sleep(.1)
    assert exported.read_bytes()==before
    result={'passed':True,'version':'1.5.12','worker_sha256':hashlib.sha256(worker.read_bytes()).hexdigest(),'restart_no_duplicates':True,'no_real_engine_games':True,'ui':json.loads((ROOT/'test-output/pgn-output-packaged/result.json').read_text())}
    (ROOT/'test-output/pgn-output-package.json').write_text(json.dumps(result,indent=2));print('Packaged PGN acceptance passed; restart retained exact bytes.',flush=True)
finally:
    if info and proc.poll() is None:api('shutdown',{});proc.wait(timeout=30)
    elif proc.poll() is None:proc.terminate();proc.wait(timeout=10)
    log.close()
