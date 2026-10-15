"""Private material-only update: native startup, shipped assets, source and installer.

All runtime checks use a disposable workspace. No production data or physical
GPU test. Run before packaging, then --verify after building the installer.
"""
from contextlib import closing
from datetime import datetime, timezone
import hashlib,json,sqlite3,sys,time,urllib.request
from pathlib import Path
from rc_acceptance import Candidate,ROOT
from arena import __version__
TAG='v'+__version__.replace('.','')
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def digest(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def run():
 previous=read(ROOT/'test-output/workflow-ready.json');source=Path(previous['folder']).resolve()
 assert source.is_relative_to(ROOT/'test-output') and source.name.startswith('workflow-')
 folder=ROOT/'test-output'/('workflow-cameo-'+str(time.time_ns()));folder.mkdir()
 with closing(sqlite3.connect((source/'arena.sqlite3').as_uri()+'?mode=ro',uri=True)) as src,closing(sqlite3.connect(folder/'arena.sqlite3')) as dst:
  src.backup(dst)
  row=dst.execute("SELECT body FROM preferences WHERE name='ui'").fetchone();prefs=json.loads(row[0]) if row else {}
  prefs.update(focus3d=False,player3d=False,scene3d={'environment':'studio','live':False})
  dst.execute('INSERT OR REPLACE INTO preferences VALUES(?,?)',('ui',json.dumps(prefs)));dst.commit()
 c=Candidate(ROOT/'release/EngineArena/EngineArena.exe',folder)
 proof={'passed':False,'version':__version__,'scope':'Material correction, native disposable workspace; no production access or graphics-endurance claim'}
 with closing(c.db()) as db:before=[tuple(r) for r in db.execute('SELECT id,official,opening FROM games WHERE official IS NOT NULL ORDER BY id')]
 try:
  c.launch();status=c.api('status');assert status['active_games']==0 and not status['error']
  proof['served_models_sha256']={}
  for name in ['magnus','hikaru','levy']:
   url=f"http://127.0.0.1:{c.info['port']}/assets/club-{name}.glb"
   req=urllib.request.Request(url,headers={'X-Arena-Token':c.info['token']})
   with urllib.request.urlopen(req,timeout=30) as response:asset=response.read()
   proof['served_models_sha256'][name]=hashlib.sha256(asset).hexdigest()
   assert proof['served_models_sha256'][name]==digest(ROOT/f'ui/club-{name}.glb')
  proof['visual_review']=read(ROOT/f'test-output/{TAG}-magnus/review.json');assert proof['visual_review']['passed']
  proof['shirt_review']=read(ROOT/f'test-output/{TAG}-shirts/review.json');assert proof['shirt_review']['passed']
  proof['asset_comparison']=read(ROOT/f'test-output/{TAG}-shirts/asset-comparison.json')
  assert proof['asset_comparison']['only_requested_cast_changed'] and all(proof['asset_comparison']['geometry_skin_animation_unchanged'].values())
  with closing(c.db()) as db:
   assert before==[tuple(r) for r in db.execute('SELECT id,official,opening FROM games WHERE official IS NOT NULL ORDER BY id')]
   assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
  proof.update(passed=True,committed_results_preserved=len(before),worker_sha256=digest(ROOT/'release/EngineArena/worker/ArenaWorker.exe'))
 finally:
  c.stop();proof['startup_timings']=c.timings;(ROOT/f'test-output/{TAG}-package.json').write_text(json.dumps(proof,indent=2))
 print('Native candidate and corrected asset checks passed.')
def verify():
 payload=ROOT/'build/installer-payload';manifest=read(payload/'package-manifest.json')
 for item in manifest:
  target=(payload/item['path']).resolve();assert target.is_relative_to(payload.resolve())
  assert target.stat().st_size==item['bytes'] and digest(target)==item['sha256'],item['path']
 sources=[p for folder in ['ui','locales'] for p in (ROOT/folder).rglob('*') if p.is_file()]
 for source in sources:
  relative=source.relative_to(ROOT)
  assert all(digest(source)==digest(base/'worker/_internal'/relative) for base in [payload,ROOT/'release/EngineArena'])
  assert digest(source)==digest(payload/'Source'/relative)
 scripts=(ROOT/'installer/source-scripts.txt').read_text().splitlines()
 for name in scripts:assert digest(ROOT/'scripts'/name)==digest(payload/'Source/scripts'/name),name
 docs=(ROOT/'installer/public-docs.txt').read_text().splitlines()
 for name in docs:assert digest(ROOT/'docs'/name)==digest(payload/'docs'/name)==digest(payload/'Source/docs'/name),name
 for name in ['prototypes/live-club/cast/manifest.json','prototypes/live-club/art/README.md','vendor/MakeHuman/club-cast/derived.json']:
  assert digest(ROOT/name)==digest(payload/'Source'/name),name
 for source in (ROOT/'prototypes/live-club/art').glob('*-shirt.*'):
  assert digest(source)==digest(payload/'Source'/source.relative_to(ROOT))
 proof=read(ROOT/f'test-output/{TAG}-package.json');assert proof['passed'] and proof['version']==__version__
 assert proof['worker_sha256']==digest(payload/'worker/ArenaWorker.exe')==digest(ROOT/'release/EngineArena/worker/ArenaWorker.exe')
 installer=ROOT/f'release/EngineArenaSetup-{__version__}-win-x64.exe'
 report={'version':__version__,'installer':installer.name,'bytes':installer.stat().st_size,'sha256':digest(installer),'created_utc':datetime.now(timezone.utc).isoformat(),'payload_files_verified':len(manifest),'ui_catalog_files_verified':len(sources),'source_scripts_verified':len(scripts),'public_docs_verified':len(docs),'checks':proof,'installed_over_owner_copy':False,'published':False}
 Path(str(installer)+'.validation.json').write_text(json.dumps(report,indent=2)+'\n');(ROOT/f'test-output/{TAG}-validation.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps({k:v for k,v in report.items() if k!='checks'},indent=2))
if __name__=='__main__':verify() if '--verify' in sys.argv else run()
