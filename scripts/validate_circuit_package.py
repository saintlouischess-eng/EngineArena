"""Custom competition acceptance against the packaged native app, isolated data only."""
from contextlib import closing
import json,subprocess,sys,time
from rc_acceptance import Candidate,ROOT
from arena import __version__
from arena.store import Store
from validate_cameo_color_package import digest,verify


def run():
 tag='v'+__version__.replace('.','');folder=ROOT/'test-output'/('circuit-package-'+str(time.time_ns()));folder.mkdir()
 sys.path.insert(0,str(ROOT/'tests'))
 from test_rating_families import seed
 with closing(Store(folder)) as fixture:seed(fixture)
 c=Candidate(ROOT/'release/EngineArena/EngineArena.exe',folder)
 proof={'passed':False,'version':__version__,'scope':'Disposable custom competition, UCI adjudication, forced recovery and UI; no production or physical GPU test'}
 try:
  c.launch();profiles=[]
  for i in range(4):
   profiles.append(c.api('profiles',{'name':f'Circuit peer {i+1}','path':sys.executable,'args':[str(ROOT/'tests/fault_engine.py'),'--white-scores','0','--wait','0.06'],'threads':1,'hash':16,'discover':True})['id'])
  t=c.tournament('Custom competition source',profiles,{'format':'round_robin','cycles':1,'concurrency':2,'cpu_budget':2,'paired':True,'draw_cp':20,'draw_plies':3,'draw_after':5,'max_plies':16})
  ready=ROOT/f'test-output/{tag}-circuit-ready.json'
  ready.write_text(json.dumps({'url':f"http://127.0.0.1:{c.info['port']}/?token={c.info['token']}",'rr':t['id'],'folder':str(folder)}))
  subprocess.run(['node','scripts/validate_circuits_ui.cjs',str(ready),f'test-output/{tag}-packaged-ui'],cwd=ROOT,check=True)
  proof['ui']=json.loads((ROOT/f'test-output/{tag}-packaged-ui/result.json').read_text());assert proof['ui']['passed']
  subprocess.run(['node','scripts/validate_rating_families_ui.cjs',str(ready),f'test-output/{tag}-rating-ui'],cwd=ROOT,check=True)
  proof['ratings_ui']=json.loads((ROOT/f'test-output/{tag}-rating-ui/result.json').read_text());assert proof['ratings_ui']['passed']
  c.api('preferences',{'language':'en'})
  stages=[{'id':'qualifier','name':'Qualification','format':'round_robin','groups':1,'pairs':1,'advance':2,'ties':'standings','time_control':{'kind':'nodes','nodes':555},'adjudication':{'draw_cp':20,'draw_plies':3,'draw_after':5}},
          {'id':'final','name':'Final','format':'round_robin','groups':1,'pairs':1,'advance':1,'ties':'standings','time_control':{'kind':'fischer','seconds':180,'increment':.05},'adjudication':{'draw_cp':20,'draw_plies':7,'draw_after':9}}]
  e=c.api('events',{'name':'Packaged custom championship','source_tid':t['id'],'definition':{'kind':'circuit','seasons':2,'review_policy':'automatic','stages':stages,'resources':{'concurrency':2,'cpu_budget':2,'memory_budget_mb':2048,'gpu_limits':{}}}})
  eid=e['id'];assert e['regular_games']==28
  e=c.api('events/'+eid,{'action':'circuit_approve','revision':e['revision']});c.api('events/'+eid,{'action':'run','revision':e['revision']})
  recovered=False;deadline=time.monotonic()+100
  while time.monotonic()<deadline:
   e=c.api('events/'+eid+'?export=1');status=c.api('status');assert not status['error'],status['error']
   if not recovered and e['official_games']>=2 and status['active_games']:
    c.kill()
    with closing(c.db()) as db:
     saved=[dict(r) for r in db.execute('SELECT id,official,opening FROM games WHERE official IS NOT NULL')]
     unfinished=[r['id'] for r in db.execute('SELECT id FROM attempts WHERE ended IS NULL')]
    assert unfinished;c.launch();e=c.api('events/'+eid);assert e['state']=='paused' and c.api('status')['active_games']==0
    with closing(c.db()) as db:
     for g in saved:assert dict(db.execute('SELECT id,official,opening FROM games WHERE id=?',(g['id'],)).fetchone())==g
     for aid in unfinished:assert db.execute('SELECT reason FROM attempts WHERE id=?',(aid,)).fetchone()[0]=='interrupted'
    proof['recovery']={'committed_games_preserved':len(saved),'unfinished_archived':len(unfinished)};recovered=True
    c.api('events/'+eid,{'action':'run','revision':e['revision']});continue
   if e['state']=='completed':break
   assert e['state']=='running',e
   time.sleep(.1)
  assert recovered and e['state']=='completed' and e['official_games']==e['scheduled_games']==28,e
  proof['stages']=[]
  for child in e['children']:
   s=c.api('tournaments/'+child['tid']);minimum=s['settings']['draw_after'];assert minimum in (5,9)
   with closing(c.db()) as db:
    rows=[dict(r) for r in db.execute('SELECT a.reason,a.result,(SELECT count(*) FROM moves m WHERE m.aid=a.id) plies FROM games g JOIN attempts a ON a.id=g.official WHERE g.tid=?',(child['tid'],))]
    assert len(rows)==s['total'] and all(r=={'reason':'draw_adjudication','result':'1/2-1/2','plies':minimum} for r in rows),rows
   assert s['complete_pairs']*2==s['official_games']
   pgn=c.pgn(child['tid'],s['official_games']);html=c.api(f"tournaments/{child['tid']}/report")['html']
   assert f'after {minimum} played plies from the starting position' in html
   proof['stages'].append({'games':s['official_games'],'draw_after':minimum,'time_control':s['settings']['time_control'],'pgn':pgn})
  overview=c.api('events/'+eid+'?view=insights&export=1');assert overview['complete'] and overview['all_official']==28 and len(overview['champions'])==2
  for p in e['roster']:
   career=c.api('events/'+eid+'?view=careers&identity='+p['identity']);assert career['games']>=12
  ready.write_text(json.dumps({'url':f"http://127.0.0.1:{c.info['port']}/?token={c.info['token']}",'rr':t['id'],'eid':eid,'folder':str(folder)}))
  subprocess.run(['node','scripts/validate_circuit_reports.cjs',str(ready),f'test-output/{tag}-circuit-reports'],cwd=ROOT,check=True)
  with closing(c.db()) as db:assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
  c.stop();c.launch();after=c.api('events/'+eid+'?export=1');assert after['decisions']==e['decisions'] and after['official_games']==28
  proof.update(passed=True,event_id=eid,folder=str(folder),worker_sha256=digest(ROOT/'release/EngineArena/worker/ArenaWorker.exe'))
 finally:
  c.stop();proof['startup_seconds']=c.timings;(ROOT/f'test-output/{tag}-package.json').write_text(json.dumps(proof,indent=2))
 print('Native custom competition: 28 games, different stage adjudication, forced recovery, PGN, reports and UI passed.')


if __name__=='__main__':verify() if '--verify' in sys.argv else run()
