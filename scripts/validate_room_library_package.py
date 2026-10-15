"""Private room/library candidate acceptance; disposable data and software GPU.

No production access. --verify checks the final installer and source manifest.
"""
from contextlib import closing
import json,os,subprocess,sys,time
from rc_acceptance import Candidate,ROOT
from arena import __version__
from validate_cameo_color_package import digest,verify

def run():
 tag='v'+__version__.replace('.','');folder=ROOT/'test-output'/('room-library-package-'+str(time.time_ns()));folder.mkdir()
 c=Candidate(ROOT/'release/EngineArena/EngineArena.exe',folder)
 report={'passed':False,'version':__version__,'scope':'Disposable packaged library, camera and room controls; software GPU; no physical graphics-endurance claim'}
 try:
  c.launch();assert c.api('status')['active_games']==0
  profiles=[{'id':str(i),'name':f'Test engine {i+1}','path':sys.executable,'args':[str(ROOT/'tests/fault_engine.py')],'threads':1,'hash':2} for i in range(5)]
  c.api('profiles/import',{'profiles':profiles});legacy=c.tournament('Saved tournament',[str(i) for i in range(5)],{'format':'round_robin'})
  ready=ROOT/f'test-output/{tag}-room-library-ready.json'
  ready.write_text(json.dumps({'url':f"http://127.0.0.1:{c.info['port']}/?token={c.info['token']}",'rr':legacy['id'],'folder':str(folder),'gid':'camera-preview','profiles':[p['id'] for p in profiles]}),encoding='utf-8')
  checks=[('validate_camera_tilt.cjs','camera-tilt')] if '--camera-only' in sys.argv else [('validate_room_library.cjs','room-library'),('validate_camera_tilt.cjs','camera-tilt')]
  for script,name in checks:
   output=f'test-output/{tag}-{name}'
   subprocess.run(['node','scripts/'+script,str(ready),output],cwd=ROOT,check=True,timeout=1200)
   report[name]=json.loads((ROOT/output/'result.json').read_text());assert report[name]['passed']
  if '--camera-only' in sys.argv:
   output=f'test-output/{tag}-camera-input'
   env=dict(os.environ,ARENA_POLISH_READY=str(ready),ARENA_POLISH_OUT=output)
   subprocess.run(['node','scripts/validate_camera_polish.cjs'],cwd=ROOT,env=env,check=True,timeout=1200)
   report['camera-input']=json.loads((ROOT/output/'result.json').read_text());assert report['camera-input']['passed']
  # The native shell remains in its untouched 2D view. Browser preferences are
  # reset to 2D before restarting so no physical GPU test is initiated.
  c.api('preferences',{'language':'en','focus3d':False,'player3d':False,'scene3d':{'environment':'studio','live':False,'fps':30}})
  peers=[]
  for name in ['Candidate peer A','Candidate peer B']:
   peers.append(c.api('profiles',{'name':name,'path':sys.executable,'args':[str(ROOT/'tests/fault_engine.py'),'--white-scores','0'],'threads':1,'hash':16,'discover':True})['id'])
  t=c.tournament('Candidate game regression',peers,{'cycles':2,'concurrency':2,'cpu_budget':2,'paired':True,'draw_cp':20,'draw_plies':3,'draw_after':5,'max_plies':12,'tolerance':1})
  c.action(t['id'],'start');snapshot,timing=c.wait(t['id'],timeout=60)
  assert snapshot['official_games']==4 and snapshot['complete_pairs']==2
  with closing(c.db()) as db:
   attempts=[dict(row) for row in db.execute('SELECT a.result,a.reason,(SELECT count(*) FROM moves m WHERE m.aid=a.id) plies FROM attempts a JOIN games g ON g.id=a.gid WHERE g.tid=?',(t['id'],))]
   assert len(attempts)==4 and all(a=={'result':'1/2-1/2','reason':'draw_adjudication','plies':5} for a in attempts),attempts
  report['pgn']=c.pgn(t['id'],4);report['attempts']=attempts;report['timing']=timing
  html=c.api(f"tournaments/{t['id']}/report")['html'];assert 'after 5 played plies from the starting position' in html
  before=c.api(f"tournaments/{t['id']}")['settings'];c.stop();c.launch()
  snapshot=c.api(f"tournaments/{t['id']}");assert snapshot['settings']==before and snapshot['official_games']==4 and snapshot['complete_pairs']==2
  assert c.api('status')['active_games']==0
  with closing(c.db()) as db:assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
  report.update(passed=True,restart_preserves_results_settings=True,worker_sha256=digest(ROOT/'release/EngineArena/worker/ArenaWorker.exe'))
 finally:
  c.stop();report['startup_seconds']=c.timings;(ROOT/f'test-output/{tag}-package.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
 print('Packaged acceptance passed: requested UI checks, four UCI games, PGN, report and restart.')

if __name__=='__main__':verify() if '--verify' in sys.argv else run()
