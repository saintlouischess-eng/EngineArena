"""Extension/UI/recovery acceptance on an isolated source or packaged workspace."""
from contextlib import closing
import json,os,subprocess,sys,time
from pathlib import Path
from rc_acceptance import Candidate,ROOT
sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from arena import __version__
from arena.store import Store
from test_core import profile
from test_tournament_extend import finish


class Source(Candidate):
 def stop(self):
  if not self.process:return
  if self.process.poll() is None:
   self.api('shutdown',{});self.process.wait(90)
  self.process=None
 def launch(self):
  started=time.perf_counter();old=self.ready.read_bytes() if self.ready.exists() else None
  self.process=subprocess.Popen([sys.executable,str(ROOT/'worker.py'),'--data',str(self.folder),'--ready',str(self.ready)],cwd=ROOT,creationflags=subprocess.CREATE_NO_WINDOW,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
  for _ in range(900):
   if self.process.poll() is not None:raise RuntimeError('Source worker exited')
   if self.ready.exists() and self.ready.read_bytes()!=old:
    self.info=json.loads(self.ready.read_text());self.api('status');self.timings.append(time.perf_counter()-started);return
   time.sleep(.1)
  raise TimeoutError('Source fixture startup')


def run():
 mode='source' if '--source' in sys.argv else 'package';tag='v'+__version__.replace('.','')
 folder=ROOT/'test-output'/('extension-'+mode+'-'+str(time.time_ns()));folder.mkdir()
 with closing(Store(folder)) as s:
  profiles=[profile('old-a')|{'name':'A original','hash':1,'options':{'Hash':1}},profile('old-b')|{'name':'B original','hash':2,'options':{'Hash':2}}]
  for p in profiles:s.save_profile(p)
  for i in range(1,81):s.save_profile(profile(f'new-{i:03}')|{'name':f'Candidate {i:03}','hash':i+2,'options':{'Hash':i+2}})
  t=s.create_tournament('Completed round robin',profiles,{'format':'round_robin','cycles':1,'paired':True,'max_plies':8,'concurrency':2,'cpu_budget':2,'time_control':{'kind':'nodes','nodes':1000}},backup=False)
  finish(s,t['id']);tid=t['id'];old=s.rows('SELECT * FROM games ORDER BY id');old_attempts=s.rows('SELECT * FROM attempts ORDER BY id');gid=old[0]['id']
 c=(Source if mode=='source' else Candidate)(ROOT/'release/EngineArena/EngineArena.exe',folder)
 result={'passed':False,'version':__version__,'mode':mode,'folder':str(folder)}
 ready=ROOT/f'test-output/{tag}-extension-{mode}-ready.json';out=f'test-output/{tag}-extension-{mode}-ui'
 try:
  c.launch();ready.write_text(json.dumps({'url':f"http://127.0.0.1:{c.info['port']}/?token={c.info['token']}",'rr':tid,'gid':gid,'folder':str(folder)}),encoding='utf-8')
  subprocess.run(['node','scripts/validate_extension_ui.cjs',str(ready),out],cwd=ROOT,check=True,timeout=300)
  result['ui']=json.loads((ROOT/out/'result.json').read_text())
  with closing(c.db()) as db:
   for g in old:assert dict(db.execute('SELECT * FROM games WHERE id=?',(g['id'],)).fetchone())==g
   for a in old_attempts:assert dict(db.execute('SELECT * FROM attempts WHERE id=?',(a['id'],)).fetchone())==a
  c.action(tid,'start');snap,timing=c.wait(tid,timeout=90);assert snap['official_games']==12 and snap['complete_pairs']==6
  result['pgn']=c.pgn(tid,12);html=c.api(f'tournaments/{tid}/report')['html'];assert 'Round-robin extensions' in html
  with closing(c.db()) as db:assert db.execute('SELECT count(*) FROM rc_games').fetchone()[0]==12
  # A second extension is durably paused. Force termination after committing it.
  body={'profiles':['new-001']};p=c.api(f'tournaments/{tid}/extend',body|{'preview':True});assert p['additional_games']==8
  c.api(f'tournaments/{tid}/extend',body|{'expected':p['expected']});c.kill();c.launch()
  snap=c.api('tournaments/'+tid);assert snap['state']=='paused' and snap['total']==20 and snap['official_games']==12
  c.action(tid,'start');snap,_=c.wait(tid,timeout=90);assert snap['official_games']==20 and snap['complete_pairs']==10
  result['recovery_pgn']=c.pgn(tid,20)
  with closing(c.db()) as db:
   assert db.execute('SELECT count(*) FROM rc_games').fetchone()[0]==20
   for g in old:assert dict(db.execute('SELECT * FROM games WHERE id=?',(g['id'],)).fetchone())==g
   assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
  # The actual worker applies both move-count rules, independent of the display.
  for claims,start,reason in [(True,99,'fifty_moves'),(False,149,'seventyfive_moves')]:
   d=c.tournament('Draw counter boundary',['old-a','old-b'],{'cycles':1,'paired':False,'max_plies':0,'claim_draws':claims},openings=[{'fen':f'1k6/8/8/8/8/8/8/R6K w - - {start} 80','name':'Rule boundary'}])
   c.action(d['id'],'start');done,_=c.wait(d['id'],timeout=60)
   with closing(c.db()) as db:
    row=db.execute('SELECT a.reason FROM games g JOIN attempts a ON a.id=g.official WHERE g.tid=?',(d['id'],)).fetchone();assert row[0]==reason,row[0]
  c.stop();c.launch();assert c.api('tournaments/'+tid)['official_games']==20;c.stop()
  result.update(passed=True,retained_games=2,extended_games=20,restart=True,forced_termination=True,draw_rules=True,timing=timing,startups=c.timings)
  if mode=='package':
   from validate_cameo_color_package import digest
   result['worker_sha256']=digest(ROOT/'release/EngineArena/worker/ArenaWorker.exe')
 finally:
  c.stop();ready.unlink(missing_ok=True);(ROOT/f'test-output/{tag}-extension-{mode}.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps(result),flush=True)


if __name__=='__main__':run()
