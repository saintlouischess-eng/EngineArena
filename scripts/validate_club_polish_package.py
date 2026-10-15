"""Validate the private live-club polish installer in a disposable native workspace.

Run without arguments after the portable build, then --verify after packaging.
Never reads or modifies the owner's Engine Arena data.
"""
from contextlib import closing
from datetime import datetime, timezone
import hashlib,json,os,sqlite3,subprocess,sys,time
from pathlib import Path
from rc_acceptance import Candidate,ROOT
from arena import __version__

def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def digest(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def run():
 previous=read(ROOT/'test-output/workflow-ready.json');source=Path(previous['folder']).resolve()
 assert source.is_relative_to(ROOT/'test-output') and source.name.startswith('workflow-')
 folder=ROOT/'test-output'/('workflow-club-polish-'+str(time.time_ns()));folder.mkdir()
 with closing(sqlite3.connect((source/'arena.sqlite3').as_uri()+'?mode=ro',uri=True)) as src,closing(sqlite3.connect(folder/'arena.sqlite3')) as dst:
  src.backup(dst)
  row=dst.execute("SELECT body FROM preferences WHERE name='ui'").fetchone();prefs=json.loads(row[0]) if row else {}
  prefs.update(focus3d=False,player3d=False,pieces3d='staunton1849',scene3d={'environment':'studio','live':False})
  dst.execute('INSERT OR REPLACE INTO preferences VALUES(?,?)',('ui',json.dumps(prefs)));dst.commit()
 c=Candidate(ROOT/'release/EngineArena/EngineArena.exe',folder)
 proof={'passed':False,'version':__version__,'scope':'Disposable native application and software WebGL; no production access','checks':{}}
 with closing(c.db()) as db:before=[tuple(r) for r in db.execute('SELECT id,official,opening FROM games WHERE official IS NOT NULL ORDER BY id')]
 try:
  c.launch();assert c.api('status')['active_games']==0
  ready=previous|{'folder':str(folder),'url':f"http://127.0.0.1:{c.info['port']}/?token={c.info['token']}"}
  ready_path=ROOT/'test-output/club-polish-package-ready.json';ready_path.write_text(json.dumps(ready))
  for script,key,outkey,out in [('validate_club_motion.cjs','ARENA_SCENE_READY','ARENA_MOTION_OUT','v184-motion-packaged'),('validate_club.cjs','ARENA_SCENE_READY','ARENA_CLUB_OUT','v184-club-packaged'),('validate_camera_polish.cjs','ARENA_POLISH_READY','ARENA_POLISH_OUT','v184-camera-packaged'),('validate_graphics_recovery.cjs','ARENA_GRAPHICS_READY','ARENA_GRAPHICS_OUT','v184-recovery-packaged')]:
   result=subprocess.run(['node','scripts/'+script],cwd=ROOT,env=os.environ|{key:str(ready_path),outkey:'test-output/'+out},creationflags=subprocess.CREATE_NO_WINDOW,capture_output=True,text=True,encoding='utf-8',timeout=720)
   print(result.stdout,flush=True);print(result.stderr,flush=True);assert result.returncode==0,script
   proof['checks'][script]=read(ROOT/'test-output'/out/'result.json');assert proof['checks'][script]['passed']
  with closing(c.db()) as db:
   assert before==[tuple(r) for r in db.execute('SELECT id,official,opening FROM games WHERE official IS NOT NULL ORDER BY id')]
   assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
  assert not c.api('status')['error']
  proof.update(passed=True,committed_results_preserved=len(before),worker_sha256=digest(ROOT/'release/EngineArena/worker/ArenaWorker.exe'))
 finally:
  c.stop();proof['timings']=c.timings;(ROOT/'test-output/v184-package.json').write_text(json.dumps(proof,indent=2))

def verify():
 payload=ROOT/'build/installer-payload';manifest=read(payload/'package-manifest.json');count=0
 for item in manifest:
  target=(payload/item['path']).resolve();assert target.is_relative_to(payload.resolve())
  assert target.stat().st_size==item['bytes'] and digest(target)==item['sha256'],item['path']
 for source in [*(ROOT/'ui').rglob('*'),*(ROOT/'locales').rglob('*')]:
  if not source.is_file():continue
  relative=source.relative_to(ROOT)
  for base in [payload,ROOT/'release/EngineArena']:assert digest(source)==digest(base/'worker/_internal'/relative),str(relative)
  assert digest(source)==digest(payload/'Source'/relative);count+=1
 for name in ['scripts/build_club_cast.py','scripts/club_cast_details.py','prototypes/live-club/room.js','prototypes/live-club/art/PROVENANCE.md']:assert digest(ROOT/name)==digest(payload/'Source'/name)
 scripts=(ROOT/'installer/source-scripts.txt').read_text(encoding='utf-8').splitlines()
 for name in scripts:assert digest(ROOT/'scripts'/name)==digest(payload/'Source/scripts'/name),name
 docs=(ROOT/'installer/public-docs.txt').read_text(encoding='utf-8').splitlines()
 for name in docs:
  assert digest(ROOT/'docs'/name)==digest(payload/'docs'/name)==digest(payload/'Source/docs'/name),name
 assert digest(ROOT/'prototypes/live-club/art/younger-player-reference.png')==digest(payload/'Source/prototypes/live-club/art/younger-player-reference.png')
 assert not (payload/'Source/prototypes/tal1962/reference').exists()
 proof=read(ROOT/'test-output/v184-package.json');assert proof['passed'] and proof['version']==__version__
 assert proof['worker_sha256']==digest(payload/'worker/ArenaWorker.exe')==digest(ROOT/'release/EngineArena/worker/ArenaWorker.exe')
 installer=ROOT/f'release/EngineArenaSetup-{__version__}-win-x64.exe'
 report={'version':__version__,'installer':installer.name,'bytes':installer.stat().st_size,'sha256':digest(installer),'created_utc':datetime.now(timezone.utc).isoformat(),'payload_files_verified':len(manifest),'ui_catalog_files_verified':count,'checks':proof,'scope':'Actual club cast, reading/playing motion, both room/camera workflows and simulated graphics loss. No new endurance run or physical GPU reset.','installed_over_owner_copy':False,'published':False}
 report.update(source_scripts_verified=len(scripts),public_docs_verified=len(docs))
 Path(str(installer)+'.validation.json').write_text(json.dumps(report,indent=2)+'\n');(ROOT/'test-output/v184-validation.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps({k:v for k,v in report.items() if k!='checks'},indent=2))

if __name__=='__main__':verify() if '--verify' in sys.argv else run()
