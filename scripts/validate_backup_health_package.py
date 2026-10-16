"""Native startup and browser regression against a fresh disposable workspace."""
import hashlib,json,sqlite3,subprocess,time
from pathlib import Path
from rc_acceptance import Candidate,ROOT
from arena import __version__

tag='v'+__version__.replace('.','')
out=ROOT/'test-output'/f'{tag}-backup-health'
out.mkdir(exist_ok=True)
folder=out/str(time.time_ns())
folder.mkdir()
c=Candidate(ROOT/'release/EngineArena/EngineArena.exe',folder)
proof={'passed':False,'version':__version__,'scope':'Native and browser checks on a new isolated workspace; no production modifications'}
try:
 c.launch()
 c.api('preferences',{'fontSize':18,'language':'en'})
 assert c.api('status')['error']==''
 ready=out/'ready.json';ready.write_text(json.dumps({'url':f"http://127.0.0.1:{c.info['port']}/?token={c.info['token']}"}))
 result=subprocess.run(['node','scripts/validate_backup_health_ui.cjs',str(ready),str(out/'ui.json')],cwd=ROOT,creationflags=subprocess.CREATE_NO_WINDOW,capture_output=True,text=True,encoding='utf-8',timeout=150)
 print(result.stdout,flush=True);print(result.stderr,flush=True)
 assert result.returncode==0,'Packaged browser validation failed'
 proof['browser']=json.loads((out/'ui.json').read_text())
 deadline=time.monotonic()+20
 while time.monotonic()<deadline and 'Interface ready' not in (folder/'startup.log').read_text():time.sleep(.1)
 assert 'Interface ready' in (folder/'startup.log').read_text()
 c.stop()
 copies=list((folder/'backups').glob('recovery-*.sqlite3'))
 assert copies,'Clean shutdown did not leave a recovery copy'
 for copy in copies:
  with sqlite3.connect(copy.as_uri()+'?mode=ro',uri=True) as db:assert db.execute('PRAGMA quick_check').fetchone()[0]=='ok'
 c.launch()
 assert c.api('preferences')['fontSize']==18
 assert not c.api('status')['error']
 proof.update(passed=True,restartPreservedPreferences=True,recoveryCopiesChecked=len(copies))
finally:
 c.stop()
 with (ROOT/'release/EngineArena/worker/ArenaWorker.exe').open('rb') as stream:proof['worker_sha256']=hashlib.file_digest(stream,'sha256').hexdigest()
 proof['startupSeconds']=c.timings
 (ROOT/f'test-output/{tag}-package.json').write_text(json.dumps(proof,indent=2))
print(json.dumps(proof,indent=2))
