"""Real engines and abrupt native-app recovery in an isolated candidate workspace.

No production workspace is opened. The optional GPU profile is supplied explicitly
as JSON; its executables/networks are read, never changed or redistributed.
"""
import argparse
from contextlib import closing
import hashlib
import io
import json
import os
from pathlib import Path
import statistics
import subprocess
import sys
import time
import urllib.request
import urllib.parse

import chess.pgn
import psutil

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from arena.log_storage import read as read_logs
from arena import __version__


class Candidate:
    def __init__(self,exe,folder):
        self.exe=exe.resolve();self.folder=folder.resolve();self.ready=self.folder/'worker-ready.json'
        assert self.folder.is_relative_to(ROOT/'test-output')
        self.process=None;self.info=None;self.timings=[]

    def launch(self):
        old=self.ready.read_bytes() if self.ready.exists() else None
        start=time.perf_counter()
        self.process=subprocess.Popen([str(self.exe),'--data',str(self.folder)],cwd=ROOT/'test-output',creationflags=subprocess.CREATE_NO_WINDOW)
        deadline=time.monotonic()+90
        while time.monotonic()<deadline:
            if self.process.poll() is not None:raise RuntimeError('Desktop exited during startup')
            try:
                raw=self.ready.read_bytes()
                if raw!=old:
                    self.info=json.loads(raw);status=self.api('status')
                    assert not status['error'],status['error']
                    self.timings.append(time.perf_counter()-start);return
            except (OSError,ValueError):pass
            time.sleep(.1)
        raise TimeoutError('Candidate did not become ready')

    def api(self,path,body=None,raw=False):
        request=urllib.request.Request(f"http://127.0.0.1:{self.info['port']}/api/{path}",
            data=None if body is None else json.dumps(body).encode(),
            headers={'X-Arena-Token':self.info['token'],'Content-Type':'application/json'})
        with urllib.request.urlopen(request,timeout=180) as response:
            return response.read() if raw else json.load(response)

    def db(self):
        import sqlite3
        db=sqlite3.connect((self.folder/'arena.sqlite3').as_uri()+'?mode=ro',uri=True)
        db.row_factory=sqlite3.Row;return db

    def action(self,tid,action,**kw):return self.api(f'tournaments/{tid}/action',{'action':action,**kw})

    def tournament(self,name,profiles,settings=None,**kw):
        config={'format':'match','cycles':2,'concurrency':2,'cpu_budget':8,'memory_budget_mb':8192,
                'time_control':{'kind':'nodes','nodes':50000},'startup_timeout':90,'readiness_timeout':90,
                'hang_timeout':90,'retry_limit':0,'max_plies':48}|(settings or {})
        return self.api('tournaments',{'name':name,'profiles':profiles,'settings':config,**kw})

    def wait(self,tid,timeout=600,hook=None):
        start=time.monotonic();last=0;latencies=[];peak=0
        while time.monotonic()-start<timeout:
            before=time.perf_counter();snapshot=self.api('tournaments/'+tid);latencies.append((time.perf_counter()-before)*1000)
            status=self.api('status');assert not status['error'],status['error'];peak=max(peak,status['active_games'])
            if hook:hook(snapshot,status)
            if snapshot['state']=='completed':
                return snapshot,{'seconds':time.monotonic()-start,'peak_games':peak,
                    'snapshot_p95_ms':sorted(latencies)[int(.95*(len(latencies)-1))]}
            if time.monotonic()-start-last>20:
                last=time.monotonic()-start;print(f"{snapshot['name']}: {snapshot['official_games']}/{snapshot['total']}, {status['active_games']} active",flush=True)
            time.sleep(.15)
        raise TimeoutError('Tournament did not finish: '+tid)

    def pgn(self,tid,count):
        result={}
        for preset in ('clean','annotated','testing','archive'):
            raw=self.api(f'export/{tid}/pgn?'+urllib.parse.urlencode({'preset':preset}),raw=True)
            stream=io.StringIO(raw.decode());games=[]
            while game:=chess.pgn.read_game(stream):
                assert not game.errors,game.errors
                board=game.board()
                for move in game.mainline_moves():assert move in board.legal_moves;board.push(move)
                games.append(game)
            assert len(games)==count,(preset,len(games),count)
            if preset in ('testing','archive'):
                assert len({g.headers['AttemptId'] for g in games})==count
            if preset=='clean':assert all(not node.comment for game in games for node in game.mainline())
            result[preset]={'games':len(games),'bytes':len(raw)}
        return result

    def kill(self):
        assert self.process and self.process.poll() is None
        parent=psutil.Process(self.process.pid)
        assert str(self.folder) in parent.cmdline()
        children=[(p.pid,p.create_time()) for p in parent.children(recursive=True)]
        parent.kill();parent.wait(15)
        deadline=time.monotonic()+15
        while time.monotonic()<deadline:
            alive=[]
            for pid,created in children:
                try:
                    p=psutil.Process(pid)
                    if p.create_time()==created and p.is_running():alive.append(pid)
                except psutil.NoSuchProcess:pass
            if not alive:break
            time.sleep(.1)
        assert not alive,('Orphan child processes',alive)
        self.process=None

    def stop(self):
        if not self.process:return
        if self.info:
            try:
                start=time.monotonic();self.api('shutdown',{})
                psutil.Process(self.info['pid']).wait(90)
                print(f'Worker clean shutdown: {time.monotonic()-start:.3f}s',flush=True)
            except (OSError,psutil.NoSuchProcess):pass
        if self.process.poll() is None:self.kill()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--exe',type=Path,default=ROOT/'release/EngineArena/EngineArena.exe')
    parser.add_argument('--data',type=Path,default=ROOT/'test-output/rc-integration');parser.add_argument('--gpu-profile',type=Path)
    parser.add_argument('--output',type=Path,default=ROOT/'test-output/rc-integration.json')
    args=parser.parse_args();c=Candidate(args.exe,args.data)
    assert not (c.folder/'arena.sqlite3').exists(),'Choose a new isolated workspace'
    c.folder.mkdir(parents=True,exist_ok=True);report={'version':__version__,'scope':'Packaged desktop on development host','checks':{}}
    target=args.output
    def save():target.write_text(json.dumps(report,indent=2),encoding='utf-8')
    try:
        c.launch();report['desktop_pid']=c.process.pid
        # Reopening the same native workspace must leave its worker and connection
        # record untouched. The duplicate displays an explanatory window only.
        ready_before=c.ready.read_bytes();worker_before=c.info['pid']
        duplicate=subprocess.Popen([str(c.exe),'--data',str(c.folder)],cwd=ROOT/'test-output',creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            time.sleep(2)
            assert duplicate.poll() is None
            assert c.ready.read_bytes()==ready_before
            assert not psutil.Process(duplicate.pid).children(recursive=True)
            assert c.api('status')['active_games']==0 and psutil.pid_exists(worker_before)
            report['checks']['duplicate_workspace']={'ready_record_unchanged':True,'additional_workers':0}
        finally:
            if duplicate.poll() is None:duplicate.kill();duplicate.wait(15)
        # A locator for browser and native workflow inspection; remains local.
        (ROOT/'test-output/rc-ready.json').write_text(json.dumps(c.info|{'folder':str(c.folder),'url':f"http://127.0.0.1:{c.info['port']}/?token={c.info['token']}"}))
        c.api('storage',{'action':'settings','settings':{'backup_copies':2,'backup_minutes':1}})
        c.api('preferences',{'language':'en','fontSize':16,'confidence':99,'boardCount':4})
        profiles=[]
        for name,path in [('Stockfish',ROOT/'validation-engines/stockfish/stockfish/stockfish-windows-x86-64-universal.exe'),('Berserk',ROOT/'validation-engines/berserk-14-avx2.exe')]:
            profiles.append(c.api('profiles',{'name':name+' RC','path':str(path),'threads':1,'hash':32,'discover':True}))
        books=[]
        for i,text in enumerate(['1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 *','1. d4 d5 2. c4 e6 *\n\n1. e4 c5 2. Nf3 d6 *']):
            source=c.folder/f'book-{i}.pgn';source.write_text(text)
            b=c.api('move-books',{'path':str(source)})
            books.append(b|{'policy':'best','max_plies':6})
            profiles[i]=c.api('profiles',profiles[i]|{'move_book':books[-1],'discover':False})
        ids=[p['id'] for p in profiles]
        t=c.tournament('RC own books · pure nodes',ids,{'cycles':4})
        c.action(t['id'],'start');s,m=c.wait(t['id']);assert s['official_games']==8 and s['complete_pairs']==4
        with closing(c.db()) as db:
            g=db.execute('SELECT official FROM games WHERE tid=? AND number=0',(t['id'],)).fetchone()
            moves=list(db.execute('SELECT uci,info FROM moves WHERE aid=? ORDER BY ply',(g[0],)))
            assert [x['uci'] for x in moves[:2]]==['e2e4','c7c5']
            assert json.loads(moves[0]['info'])['source']=='book'
            commands=[x['line'].split('> ',1)[1] for a in db.execute('SELECT a.id FROM attempts a JOIN games g ON g.id=a.gid WHERE g.tid=?',(t['id'],)) for x in read_logs(db,a[0],100000,False) if '> go ' in x['line']]
            assert commands and set(commands)=={'go nodes 50000'}
        report['checks']['own_books']=m|{'games':8,'node_commands':len(commands),'pgn':c.pgn(t['id'],8)};save()
        # Shared tournament book still works and can disable profile books.
        shared=c.folder/'shared-master.pgn';shared.write_text('1. e4 e5 2. Nf3 Nc6 *')
        t=c.tournament('RC shared master · fractional increment',ids,{'cycles':2,'time_control':{'kind':'fischer','seconds':5,'increment':.05},'use_engine_books':False},opening_file=str(shared),book_depth=4)
        c.action(t['id'],'start');s,m=c.wait(t['id']);assert s['official_games']==4
        with closing(c.db()) as db:
            reasons=[x[0] for x in db.execute('SELECT a.reason FROM attempts a JOIN games g ON g.id=a.gid WHERE g.tid=?',(t['id'],))]
            assert set(reasons)=={'max_plies_adjudication'},reasons
        report['checks']['shared_master_fractional_increment']=m|{'pgn':c.pgn(t['id'],4),'termination':'48-ply smoke-test cap'};save()
        # Force termination after some official results, preserving unfinished books.
        t=c.tournament('RC crash recovery and live concurrency',ids,{'cycles':24,'concurrency':1,'max_plies':32,'time_control':{'kind':'nodes','nodes':100000}})
        c.action(t['id'],'start');deadline=time.monotonic()+90
        while c.api('status')['active_games']<1:
            assert time.monotonic()<deadline;time.sleep(.1)
        c.api(f"tournaments/{t['id']}/concurrency",{'concurrency':4})
        while True:
            status=c.api('status');s=c.api('tournaments/'+t['id'])
            if s['official_games']>=2 and len(status['live'])==4 and any(g['ply']>5 for g in status['live']):break
            assert time.monotonic()<deadline;time.sleep(.1)
        c.api(f"tournaments/{t['id']}/concurrency",{'concurrency':1})
        # Fast games may finish naturally while the configuration request is in
        # flight. Check the actual contract: lowering never interrupts an attempt.
        with closing(c.db()) as db:
            assert not db.execute("SELECT 1 FROM attempts a JOIN games g ON g.id=a.gid WHERE g.tid=? AND a.reason='interrupted'",(t['id'],)).fetchone()
        deadline=time.monotonic()+60
        while not any(0<g['ply']<16 for g in c.api('status')['live']):
            assert time.monotonic()<deadline;time.sleep(.02)
        c.kill()
        with closing(c.db()) as db:
            official=[tuple(r) for r in db.execute('SELECT id,official FROM games WHERE tid=? AND official IS NOT NULL ORDER BY number',(t['id'],))]
            interrupted=[dict(r) for r in db.execute('SELECT g.id,g.opening,a.id aid FROM games g JOIN attempts a ON a.gid=g.id WHERE g.tid=? AND a.ended IS NULL',(t['id'],))]
            for row in interrupted:
                row['saved_moves']=[tuple(r) for r in db.execute('SELECT ply,uci,fen,clocks FROM moves WHERE aid=? ORDER BY ply',(row['aid'],))]
        assert official and interrupted
        c.launch();s=c.api('tournaments/'+t['id']);assert s['state']=='paused' and s['official_games']==len(official)
        with closing(c.db()) as db:
            for row in interrupted:
                assert db.execute('SELECT reason FROM attempts WHERE id=?',(row['aid'],)).fetchone()[0]=='interrupted'
                assert db.execute('SELECT opening FROM games WHERE id=?',(row['id'],)).fetchone()[0]==row['opening']
                assert [tuple(r) for r in db.execute('SELECT ply,uci,fen,clocks FROM moves WHERE aid=? ORDER BY ply',(row['aid'],))]==row['saved_moves']
        c.api(f"tournaments/{t['id']}/concurrency",{'concurrency':8});c.action(t['id'],'start');s,m=c.wait(t['id'])
        assert s['official_games']==48 and s['complete_pairs']==24
        report['checks']['forced_desktop_recovery']=m|{'committed_retained':len(official),'interrupted_preserved':len(interrupted),'saved_moves_preserved':sum(len(x['saved_moves']) for x in interrupted),'concurrency_changes':[1,4,1,8],'pgn':c.pgn(t['id'],48)};save()
        if args.gpu_profile:
            gpu=json.loads(args.gpu_profile.read_text());gpu.pop('id',None)
            gpu.update(name='Lc0 RC GPU',gpu_group='gpu0',threads=1,hash=32,extra_memory_mb=2048,discover=False)
            gpu['options']=gpu.get('options',{})|{'NNCacheSize':100000,'Threads':1}
            gpu=c.api('profiles',gpu)
            clone=profiles[0]|{'name':'Stockfish RC second profile','discover':False};clone.pop('id')
            third=c.api('profiles',clone)
            t=c.tournament('RC mixed GPU CPU round robin',[gpu['id'],*ids,third['id']],{'format':'round_robin','cycles':2,'concurrency':8,'cpu_budget':4,'gpu_limits':{'gpu0':1},'max_plies':24,'time_control':{'kind':'nodes','nodes':2000}})
            c.action(t['id'],'start');gpu_peak=0;cpu_overlap=False
            def check_gpu(s,status):
                nonlocal gpu_peak,cpu_overlap
                active=sum(int(g[side].get('gpu_group')=='gpu0') for g in status['live'] for side in ('white','black'))
                gpu_peak=max(gpu_peak,active);assert active<=1
                cpu_overlap |= active==1 and status['active_games']>1
            s,m=c.wait(t['id'],900,check_gpu)
            with closing(c.db()) as db:
                reasons=[x[0] for x in db.execute('SELECT a.reason FROM attempts a JOIN games g ON g.id=a.gid WHERE g.tid=?',(t['id'],))]
                assert set(reasons)=={'max_plies_adjudication'},reasons
            assert gpu_peak==1 and cpu_overlap
            report['checks']['real_gpu_cpu']=m|{'games':s['official_games'],'gpu_peak':gpu_peak,'cpu_games_overlap':cpu_overlap,'pgn':c.pgn(t['id'],s['official_games'])};save()
        # Background report from the frozen worker must be functional too.
        start=time.perf_counter();html=c.api(f"tournaments/{t['id']}/report?all_engines=1")['html']
        report['checks']['report']={'bytes':len(html.encode()),'seconds':time.perf_counter()-start};assert '<table' in html
        start=time.perf_counter();again=c.api(f"tournaments/{t['id']}/report?all_engines=1")['html'];assert html==again
        report['checks']['report']['cached_seconds']=time.perf_counter()-start
        before=c.api('tournaments');hashes={n:hashlib.sha256((c.folder/n).read_bytes()).hexdigest() for n in ('games.pgn','interrupted.pgn')}
        c.stop();c.launch();assert c.api('tournaments')==before
        assert c.api('preferences')['confidence']==99
        assert all(hashlib.sha256((c.folder/n).read_bytes()).hexdigest()==h for n,h in hashes.items())
        report['clean_restart_exact_pgn']=True;report['startup_seconds']=c.timings
        report['checks']['storage']=c.api('storage');report['passed']=True;save()
        print(json.dumps({k:v for k,v in report.items() if k!='checks'},indent=2),flush=True)
    except BaseException as exc:
        report['failure']=repr(exc);save();raise
    finally:c.stop()


if __name__=='__main__':main()
