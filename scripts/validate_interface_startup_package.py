"""Startup, standings and saved-game recovery in disposable source/package data."""
import hashlib,json,sqlite3,subprocess,sys,time
from rc_acceptance import Candidate,ROOT
from validate_extension_package import Source
from arena import __version__

mode=sys.argv[1] if len(sys.argv)>1 else 'package'
assert mode in ('source','package')
out=ROOT/'test-output'/('v'+__version__.replace('.','')+'-interface-'+mode)
out.mkdir(exist_ok=True)
folder=out/str(time.time_ns());folder.mkdir()
c=(Source if mode=='source' else Candidate)(ROOT/'release/EngineArena/EngineArena.exe',folder)
proof={'passed':False,'version':__version__,'mode':mode,'scope':'Fresh isolated workspace; production tournament untouched'}
try:
 c.launch();c.api('preferences',{'fontSize':18,'language':'en'})
 profiles=[]
 for name in ('Startup test White','Startup test Black'):
  p=c.api('profiles',{'name':name,'path':str(ROOT/'.venv/Scripts/python.exe'),
   'args':[str(ROOT/'tests/fault_engine.py')],'threads':1,'hash':16,'discover':True})
  profiles.append(p['id'])
 t=c.tournament('Startup regression',profiles,{'cycles':1,'paired':True,'concurrency':1,'cpu_budget':1,'max_plies':8})
 c.action(t['id'],'start');done,timing=c.wait(t['id'],timeout=90);assert done['official_games']==2
 proof['pgn']=c.pgn(t['id'],2)
 ready=out/'ready.json';ready.write_text(json.dumps({'url':f"http://127.0.0.1:{c.info['port']}/?token={c.info['token']}"}))
 result=subprocess.run(['node','scripts/validate_interface_startup_ui.cjs',str(ready),str(out/'ui.json')],cwd=ROOT,
  creationflags=subprocess.CREATE_NO_WINDOW,capture_output=True,text=True,encoding='utf-8',timeout=180)
 print(result.stdout,flush=True);print(result.stderr,flush=True)
 assert result.returncode==0,'Delayed-script browser test failed'
 proof['browser']=json.loads((out/'ui.json').read_text())
 c.stop()
 copies=list((folder/'backups').glob('recovery-*.sqlite3'));assert copies
 for copy in copies:
  with sqlite3.connect(copy.as_uri()+'?mode=ro',uri=True) as db:assert db.execute('PRAGMA quick_check').fetchone()[0]=='ok'
 c.launch();assert c.api('preferences')['fontSize']==18
 assert c.api('tournaments/'+t['id'])['official_games']==2
 assert not c.api('status')['error']
 proof.update(passed=True,restartPreservedResults=True,restartPreservedPreferences=True,recoveryCopiesChecked=len(copies),startupSeconds=c.timings)
finally:
 c.stop()
 if mode=='package':
  with (ROOT/'release/EngineArena/worker/ArenaWorker.exe').open('rb') as f:proof['worker_sha256']=hashlib.file_digest(f,'sha256').hexdigest()
 ready=out/'ready.json';ready.unlink(missing_ok=True)
 (out/'validation.json').write_text(json.dumps(proof,indent=2))
print(json.dumps({'passed':proof['passed'],'mode':mode,'output':str(out)},indent=2))
