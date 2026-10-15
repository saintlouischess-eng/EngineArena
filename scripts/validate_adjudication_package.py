"""Private adjudication update: native startup, GUI workflow and real UCI peers.

Uses only a new disposable workspace. --verify validates the completed installer.
"""
from contextlib import closing
import json,subprocess,sys,time
from rc_acceptance import Candidate,ROOT
from arena import __version__
from validate_cameo_color_package import digest,verify


def run():
 tag='v'+__version__.replace('.','');folder=ROOT/'test-output'/('adjudication-package-'+str(time.time_ns()));folder.mkdir()
 c=Candidate(ROOT/'release/EngineArena/EngineArena.exe',folder);report={'passed':False,'version':__version__,'scope':'Isolated packaged adjudication controls and UCI games; no production data access'}
 try:
  c.launch();assert c.api('status')['active_games']==0
  profiles=[]
  for name in ['Adjudication peer A','Adjudication peer B']:
   profiles.append(c.api('profiles',{'name':name,'path':sys.executable,'args':[str(ROOT/'tests/fault_engine.py'),'--white-scores','0'],'threads':1,'hash':16,'discover':True})['id'])
  legacy=c.tournament('Existing custom window',profiles,{'resign_plies':15})
  ready=ROOT/f'test-output/{tag}-adjudication-ready.json'
  ready.write_text(json.dumps({'url':f"http://127.0.0.1:{c.info['port']}/?token={c.info['token']}",'rr':legacy['id'],'folder':str(folder)}))
  subprocess.run(['node','scripts/validate_adjudication_ui.cjs',str(ready),f'test-output/{tag}-packaged-ui'],cwd=ROOT,check=True)
  report['ui']=json.loads((ROOT/f'test-output/{tag}-packaged-ui/result.json').read_text());assert report['ui']['passed']
  c.api('preferences',{'language':'en'})
  t=c.tournament('Packaged adjudication game',profiles,{'cycles':1,'concurrency':1,'paired':True,'draw_cp':20,'draw_plies':3,'draw_after':5,'max_plies':12})
  c.action(t['id'],'start');snapshot,timing=c.wait(t['id'],timeout=30)
  assert snapshot['official_games']==2 and snapshot['complete_pairs']==1
  with closing(c.db()) as db:
   attempts=[dict(row) for row in db.execute('SELECT a.result,a.reason,(SELECT count(*) FROM moves m WHERE m.aid=a.id) plies FROM attempts a JOIN games g ON g.id=a.gid WHERE g.tid=?',(t['id'],))]
   assert len(attempts)==2 and all(a=={'result':'1/2-1/2','reason':'draw_adjudication','plies':5} for a in attempts),attempts
  report['pgn']=c.pgn(t['id'],2);report['attempts']=attempts;report['timing']=timing
  html=c.api(f"tournaments/{t['id']}/report")['html'];assert 'after 5 played plies from the starting position' in html
  before={tid:c.api(f'tournaments/{tid}')['settings'] for tid in [legacy['id'],t['id'],report['ui']['tid']]}
  c.stop();c.launch()
  for tid,settings in before.items():assert c.api(f'tournaments/{tid}')['settings']==settings
  assert c.api(f"tournaments/{t['id']}")['official_games']==2 and c.api('status')['active_games']==0
  with closing(c.db()) as db:assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
  report.update(passed=True,settings_preserved_after_restart=True,worker_sha256=digest(ROOT/'release/EngineArena/worker/ArenaWorker.exe'))
 finally:
  c.stop();report['startup_seconds']=c.timings;(ROOT/f'test-output/{tag}-package.json').write_text(json.dumps(report,indent=2))
 print('Packaged adjudication: GUI, 2 games, all PGN presets, report, restart and integrity passed.')


if __name__=='__main__':verify() if '--verify' in sys.argv else run()
