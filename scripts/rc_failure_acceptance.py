"""Packaged recovery tests using deliberately faulty external UCI peers."""
from contextlib import closing
import argparse
import ctypes
from ctypes import wintypes
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path
from rc_acceptance import Candidate, ROOT


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--data',type=Path,default=ROOT/'test-output/rc-failures');parser.add_argument('--output',type=Path,default=ROOT/'test-output/rc-failures.json')
    parser.add_argument('--exe',type=Path,default=ROOT/'release/EngineArena/EngineArena.exe');parser.add_argument('--parallel',action='store_true');args=parser.parse_args()
    folder=args.data.resolve();assert folder.is_relative_to(ROOT/'test-output') and not (folder/'arena.sqlite3').exists()
    c=Candidate(args.exe,folder);report={}
    try:
        c.launch()
        if args.parallel:
            q=c.api('tournament-queue');c.api('tournament-queue',{'action':'configure','revision':q['revision'],'execution_mode':'parallel',
                'resources':{'cpu_budget':4,'memory_budget_mb':8192,'concurrency':4,'gpu_limits':{}}});report['execution_mode']='parallel'
        def profile(name,mode='normal'):
            return c.api('profiles',{'name':name,'path':sys.executable,
                'args':[str(ROOT/'tests/fault_engine.py'),'--mode',mode,'--marker',str(folder/(mode+'.marker'))],
                'threads':1,'hash':1,'discover':True})['id']
        good=profile('Normal fixture');timeout=profile('Timeout once','timeout_once')
        settings={'cycles':1,'concurrency':1,'max_plies':10,'stop_timeout':.1,
                  'time_control':{'kind':'fischer','seconds':.3,'increment':.05},'tolerance':.02}
        t=c.tournament('RC time forfeit replacement',[timeout,good],settings)
        c.action(t['id'],'start');s,_=c.wait(t['id']);assert s['official_games']==2
        tf=next(x for x in s['standings'] if x['slot']==0);assert (tf['tf'],tf['tf_official'])==(1,1)
        with closing(c.db()) as db:
            lost=dict(db.execute("SELECT g.id,g.official FROM games g JOIN attempts a ON a.id=g.official WHERE g.tid=? AND a.reason='timeout'",(t['id'],)).fetchone())
        c.action(t['id'],'requeue',ids=[lost['id']],mode='replacement');c.action(t['id'],'start');s,_=c.wait(t['id'])
        tf=next(x for x in s['standings'] if x['slot']==0)
        assert s['official_games']==2 and s['complete_pairs']==1 and (tf['tf'],tf['tf_official'])==(1,0)
        with closing(c.db()) as db:
            assert db.execute('SELECT reason FROM attempts WHERE id=?',(lost['official'],)).fetchone()[0]=='timeout'
            assert db.execute('SELECT count(*) FROM attempts WHERE gid=?',(lost['id'],)).fetchone()[0]==2
        c.action(t['id'],'requeue',ids=[lost['id']],mode='diagnostic');c.action(t['id'],'start');diagnostic,_=c.wait(t['id'])
        assert diagnostic['standings']==s['standings'] and diagnostic['official_games']==2
        report['replacement']={'original_timeout_retained':True,'tf':1,'official_tf':0,'official_games':2,'pairs':1,'diagnostic_did_not_change_standings':True,'pgn':c.pgn(t['id'],2)}
        crashing=profile('Crash once','crash_once')
        t=c.tournament('RC automatic retry',[crashing,good],settings|{'retry_limit':1,'time_control':{'kind':'nodes','nodes':100}})
        c.action(t['id'],'start');s,_=c.wait(t['id'])
        with closing(c.db()) as db:
            attempts=[dict(r) for r in db.execute('SELECT a.* FROM attempts a JOIN games g ON g.id=a.gid WHERE g.tid=?',(t['id'],))]
            assert len(attempts)==3 and sum(a['reason']=='crash' for a in attempts)==1
        assert s['official_games']==2 and s['complete_pairs']==1
        report['automatic_retry']={'attempts':3,'official_games':2,'crash_preserved':True}
        # Deny write sharing for only this isolated automatic PGN. This exercises
        # an actual OS write failure without filling the user's drive.
        kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        kernel.CreateFileW.argtypes=[wintypes.LPCWSTR,wintypes.DWORD,wintypes.DWORD,ctypes.c_void_p,wintypes.DWORD,wintypes.DWORD,wintypes.HANDLE]
        kernel.CreateFileW.restype=wintypes.HANDLE
        kernel.CloseHandle.argtypes=[wintypes.HANDLE]
        handle=kernel.CreateFileW(str(folder/'games.pgn'),0x80000000,1,None,3,0,None)
        assert handle!=wintypes.HANDLE(-1).value,ctypes.get_last_error()
        try:
            # Creating a tournament does not rewrite already exported PGNs.
            t=c.tournament('RC write failure recovery',[good,good],settings|{'time_control':{'kind':'nodes','nodes':100}})
            c.action(t['id'],'start');deadline=time.monotonic()+30
            while True:
                status=c.api('status')
                if status['error']:break
                assert time.monotonic()<deadline;time.sleep(.05)
            committed=c.api('tournaments/'+t['id'])['official_games'];assert committed>=1
            assert 'PGN' in status['error'] or 'saving' in status['error'].lower()
            report['write_failure']={'visible_error':status['error'],'committed_before_retry':committed}
        finally:kernel.CloseHandle(handle)
        deadline=time.monotonic()+30
        while c.api('status')['active_games']:
            assert time.monotonic()<deadline;time.sleep(.1)
        c.api('retry-saving',{});assert not c.api('status')['error']
        c.action(t['id'],'start');s,_=c.wait(t['id']);assert s['official_games']==2
        report['write_failure']['recovered_pgn']=c.pgn(t['id'],2)
        with closing(c.db()) as db:assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        # Give the copy enough pages to observe a real incomplete backup. Only
        # the isolated test database receives this clearly labelled filler.
        c.stop()
        from arena.store import Store
        with closing(Store(folder)) as store:
            store.execute('CREATE TABLE rc_synthetic_backup_payload(data BLOB)')
            store.execute('INSERT INTO rc_synthetic_backup_payload VALUES(zeroblob(134217728))')
        c.launch();before=c.api('tournaments')
        c.api('storage',{'action':'optimize'})
        deadline=time.monotonic()+90;partial=folder/'backups/backup.tmp'
        while time.monotonic()<deadline:
            try:
                if partial.stat().st_size>1024*1024:
                    partial_size=partial.stat().st_size;c.kill();break
            except FileNotFoundError:pass
            time.sleep(.002)
        else:raise AssertionError('No partially written backup observed')
        c.launch();deadline=time.monotonic()+90
        while c.api('status')['maintenance']:
            assert time.monotonic()<deadline;time.sleep(.1)
        assert not c.api('status')['error'] and c.api('tournaments')==before
        with closing(c.db()) as db:assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        report['forced_backup_termination']={'partial_bytes':partial_size,'recovered':True,'results_retained':True}
        c.stop()
        with closing(Store(folder)) as store:
            store.execute('DROP TABLE rc_synthetic_backup_payload');store.optimize_storage()
            # Rotate the test-only filler out of older recovery copies as well.
            for _ in range(store.storage_settings['backup_copies']):store.backup()
        report['passed']=True
    except BaseException as exc:report['failure']=repr(exc);raise
    finally:
        c.stop();args.output.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2),flush=True)


if __name__=='__main__':main()
