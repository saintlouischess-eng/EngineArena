"""Kill only the isolated history-live app during a rotating backup and play."""
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess
import time
import urllib.error

import psutil
from history_live_validation import ROOT,DATA,READY,CURRENT,api


def official_signature(db,tid):
    digest=hashlib.sha256();count=0
    for row in db.execute('SELECT id,official FROM games WHERE tid=? AND official IS NOT NULL AND invalid=0 ORDER BY number',(tid,)):
        digest.update(json.dumps(row).encode());count+=1
    return count,digest.hexdigest()


def run():
    tid=json.loads(CURRENT.read_text())['tournament'];info=json.loads(READY.read_text())
    assert api('status')['active_games']==0
    before=api('tournaments/'+tid)
    with sqlite3.connect(DATA/'arena.sqlite3') as db:official_before=official_signature(db,tid)
    games=api(f'tournaments/{tid}/games?offset=50000&limit=1000')['items']
    assert len(games)==1000
    api('tournaments/'+tid+'/action',{'action':'requeue','ids':[g['id'] for g in games],'mode':'diagnostic'})
    api('tournaments/'+tid+'/action',{'action':'start'})
    started=time.monotonic();backup=DATA/'backups/backup.tmp'
    while time.monotonic()-started<120:
        status=api('status')
        if backup.exists() and backup.stat().st_size>8192 and len(status['live'])>=24 and any(g['ply']>=5 for g in status['live']):break
        time.sleep(.05)
    else:raise AssertionError('Did not observe active games and a backup together')
    worker=psutil.Process(info['pid']);parent=next(p for p in worker.parents() if Path(p.exe()).name=='EngineArena.exe')
    args=parent.cmdline();assert '--data' in args
    selected=Path(args[args.index('--data')+1]);selected=selected if selected.is_absolute() else Path(parent.cwd())/selected
    assert selected.resolve()==DATA.resolve(),'Refuse to stop a non-validation instance'
    descendants=[(p.pid,p.create_time()) for p in parent.children(recursive=True)]
    partial_size=backup.stat().st_size;kill_time=time.monotonic();parent.kill();parent.wait(15);time.sleep(.3)
    survivors=[]
    for pid,created in descendants:
        try:
            process=psutil.Process(pid)
            if process.create_time()==created and process.is_running():survivors.append(pid)
        except psutil.NoSuchProcess:pass
    assert not survivors,survivors
    with sqlite3.connect(DATA/'arena.sqlite3') as db:
        assert official_signature(db,tid)==official_before
        running=[]
        for gid,opening,aid in db.execute('SELECT g.id,g.opening,a.id FROM games g JOIN attempts a ON a.gid=g.id WHERE g.tid=? AND a.ended IS NULL',(tid,)):
            rows=db.execute('SELECT ply,uci,fen,clocks FROM moves WHERE aid=? ORDER BY ply',(aid,)).fetchall()
            running.append({'id':gid,'opening':json.loads(opening),'aid':aid,'moves':len(rows),
                            'move_hash':hashlib.sha256(json.dumps(rows).encode()).hexdigest()})
    assert len(running)>=24 and sum(g['moves'] for g in running)>0
    print(json.dumps({'killed_during_backup':True,'partial_backup_bytes':partial_size,'unfinished':len(running),'official_preserved':official_before[0]}),flush=True)
    exe=ROOT/'test-output/native-build/EngineArena.exe'
    subprocess.Popen([str(exe),'--data',str(DATA)],creationflags=subprocess.CREATE_NO_WINDOW)
    deadline=time.monotonic()+120
    while time.monotonic()<deadline:
        try:
            current=json.loads(READY.read_text())
            if current['pid']!=info['pid']:
                after=api('tournaments/'+tid);break
        except (OSError,ValueError,urllib.error.URLError):pass
        time.sleep(.1)
    else:raise AssertionError('Large-history application did not recover')
    recovery_seconds=time.monotonic()-kill_time
    assert after['state']=='paused' and after['official_games']==before['official_games']
    assert after['complete_pairs']==before['complete_pairs'] and after['standings']==before['standings']
    with sqlite3.connect(DATA/'arena.sqlite3') as db:
        assert official_signature(db,tid)==official_before
        for g in running:
            row=db.execute('SELECT state,opening FROM games WHERE id=?',(g['id'],)).fetchone()
            assert row[0]=='pending' and json.loads(row[1])==g['opening']
            assert db.execute('SELECT reason FROM attempts WHERE id=?',(g['aid'],)).fetchone()[0]=='interrupted'
            rows=db.execute('SELECT ply,uci,fen,clocks FROM moves WHERE aid=? ORDER BY ply',(g['aid'],)).fetchall()
            assert hashlib.sha256(json.dumps(rows).encode()).hexdigest()==g['move_hash']
    api('tournaments/'+tid+'/action',{'action':'start'});deadline=time.monotonic()+30
    while time.monotonic()<deadline:
        live=api('status')['live']
        if len(live)>=len(running) and any(g['ply']>=5 for g in live):break
        time.sleep(.1)
    assert len(live)>=len(running)
    api('tournaments/'+tid+'/action',{'action':'cancel'})
    assert api('tournaments/'+tid)['standings']==before['standings']
    ids=set();duplicates=0
    for name in ('games.pgn','interrupted.pgn'):
        with (DATA/name).open(encoding='utf-8') as stream:
            for line in stream:
                if line.startswith('[AttemptId "'):
                    aid=line.split('"')[1];duplicates+=aid in ids;ids.add(aid)
    assert not duplicates
    report={'forced_application_termination':True,'during_verified_backup':True,'partial_backup_bytes':partial_size,
        'retained_official_games':official_before[0],'official_signature':official_before[1],'retained_pairs':before['complete_pairs'],
        'interrupted_games':len(running),'preserved_moves':sum(g['moves'] for g in running),'moves_clocks_openings_hashes_match':True,
        'standings_unchanged':True,'resumed_live_games':len(live),'recovery_seconds':recovery_seconds,'orphan_processes':survivors,
        'all_pgn_attempts':len(ids),'pgn_duplicates':duplicates,'database_bytes':(DATA/'arena.sqlite3').stat().st_size}
    (ROOT/'test-output/history-recovery-report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)


if __name__=='__main__':run()
