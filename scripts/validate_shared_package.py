"""1.1.0 shared scheduler acceptance, using only disposable test-output data."""
from contextlib import closing
import hashlib
import json
from pathlib import Path
import time
from rc_acceptance import Candidate, ROOT
from arena.log_storage import read as read_logs


def main():
    exe=ROOT/'release/EngineArena/EngineArena.exe'
    output=ROOT/'test-output/manager-packaged.json'
    report={'scope':'Short local packaged acceptance; not endurance testing','passed':False}
    old=json.loads((ROOT/'test-output/manager-upgrade-before.json').read_text())
    c=Candidate(exe,ROOT/'test-output/manager-upgrade')
    try:
        c.launch();s=c.api('tournaments/'+old['tid']);q=c.api('tournament-queue')
        assert s['official_games']==old['official'] and s['standings']==old['standings']
        assert q['execution_mode']=='sequential' and q['mode']=='paused'
        assert [x['tid'] for x in q['items']]==old['queue_order']
        assert c.api('tournaments/'+old['waiting'])['can_edit']
        assert hashlib.sha256((c.folder/'games.pgn').read_bytes()).hexdigest()==old['pgn_sha256']
        assert c.api('status')['active_games']==0
        report['upgrade_1_0_1']={'results':old['official'],'exact_pgn':True,'standings_queue_retained':True,'default_sequential':True}
    finally:c.stop()
    folder=ROOT/'test-output/manager-packaged'
    assert not folder.exists(),'Preserve previous acceptance evidence; choose a new folder'
    c=Candidate(exe,folder);samples=[]
    def queue(action,**kw):
        q=c.api('tournament-queue');return c.api('tournament-queue',{'action':action,'revision':q['revision'],**kw})
    def until(predicate,seconds=300):
        end=time.monotonic()+seconds
        while time.monotonic()<end:
            status=c.api('status');assert not status['error'],status['error']
            live=status['live'];used=status['scheduling']['used'];samples.append({'tournaments':len({g['tid'] for g in live}),'games':len(live),'cpu':used['threads'],'gpu':used['gpu'].get('gpu0',0)})
            assert len(live)<=4 and used['threads']<=4 and used['gpu'].get('gpu0',0)<=1
            if predicate(status):return status
            time.sleep(.1)
        raise AssertionError('Acceptance deadline exceeded: '+str(c.api('tournament-queue')))
    try:
        c.launch();profiles=[]
        for name,path in [('Stockfish',ROOT/'validation-engines/stockfish/stockfish/stockfish-windows-x86-64-universal.exe'),('Berserk',ROOT/'validation-engines/berserk-14-avx2.exe')]:
            profiles.append(c.api('profiles',{'name':name,'path':str(path),'threads':1,'hash':16,'discover':True}))
        gpu=json.loads((ROOT/'test-output/rc-gpu-profile.json').read_text());gpu.pop('id',None)
        gpu.update(name='Lc0 shared GPU validation',gpu_group='gpu0',threads=1,hash=32,extra_memory_mb=2048,discover=False)
        gpu['options']=gpu.get('options',{})|{'NNCacheSize':100000,'Threads':1}
        gpu=c.api('profiles',gpu)
        limits={'cpu_budget':4,'memory_budget_mb':8192,'concurrency':4,'gpu_limits':{'gpu0':1}}
        queue('configure',execution_mode='parallel',resources=limits)
        master=folder/'master.pgn';master.write_text('1. e4 e5 2. Nf3 Nc6 *\n\n1. d4 d5 2. c4 e6 *')
        ids=[]
        for n,field,nodes,cycles in [('CPU A',profiles,50000,5),('CPU B',profiles[::-1],50000,5),('GPU A',[gpu,profiles[0]],2000,2),('GPU B',[gpu,profiles[1]],2000,2)]:
            t=c.tournament(n,[p['id'] for p in field],{'cycles':cycles,'concurrency':2,'cpu_budget':4,'gpu_limits':{'gpu0':1},'max_plies':24,'time_control':{'kind':'nodes','nodes':nodes}},opening_file=str(master),book_depth=4)
            ids.append(t['id'])
        queue('add',ids=ids);queue('set_limits',ids=[ids[3]],priority=4,concurrency=1);queue('run')
        until(lambda s:len({g['tid'] for g in s['live']})>=2 and any(g['ply']>5 for g in s['live']) and sum(c.api('tournaments/'+tid)['official_games'] for tid in ids)>=2)
        c.kill()
        with closing(c.db()) as db:
            committed=[tuple(r) for r in db.execute('SELECT id,official FROM games WHERE official IS NOT NULL ORDER BY id')]
            interrupted=[dict(r) for r in db.execute('SELECT g.id,g.tid,g.opening,a.id aid FROM games g JOIN attempts a ON a.gid=g.id WHERE a.ended IS NULL')]
            for row in interrupted:row['moves']=[tuple(r) for r in db.execute('SELECT ply,uci,fen,clocks FROM moves WHERE aid=? ORDER BY ply',(row['aid'],))]
        assert committed and len({g['tid'] for g in interrupted})>=2
        c.launch();q=c.api('tournament-queue');assert q['mode']=='paused' and q['execution_mode']=='parallel' and q['resources']==limits
        assert c.api('status')['active_games']==0
        with closing(c.db()) as db:
            assert [tuple(r) for r in db.execute('SELECT id,official FROM games WHERE official IS NOT NULL ORDER BY id')]==committed
            for row in interrupted:
                assert db.execute('SELECT reason FROM attempts WHERE id=?',(row['aid'],)).fetchone()[0]=='interrupted'
                assert db.execute('SELECT opening FROM games WHERE id=?',(row['id'],)).fetchone()[0]==row['opening']
                assert [tuple(r) for r in db.execute('SELECT ply,uci,fen,clocks FROM moves WHERE aid=? ORDER BY ply',(row['aid'],))]==row['moves']
        queue('run');until(lambda s:c.api('tournament-queue')['mode']=='completed',600)
        report['forced_termination']={'committed_retained':len(committed),'interrupted_preserved':len(interrupted),'affected_tournaments':len({g['tid'] for g in interrupted}),'saved_moves':sum(len(g['moves']) for g in interrupted),'restarted_from_recorded_openings':True}
        report['tournaments']=[]
        with closing(c.db()) as db:
            commands=[]
            for aid, in db.execute('SELECT id FROM attempts'):
                commands.extend(r['line'].split('> ',1)[1] for r in read_logs(db,aid,100000,False) if '> go ' in r['line'])
            assert commands and set(commands)<={'go nodes 50000','go nodes 2000'}
            failures=[tuple(r) for r in db.execute("SELECT reason,count(*) FROM attempts WHERE reason NOT IN ('max_plies_adjudication','interrupted') GROUP BY reason")]
            assert not failures,failures
            for tid in ids:
                s=c.api('tournaments/'+tid);assert s['official_games']==s['total'] and s['complete_pairs']*2==s['total']
                assert sum(r['games'] for r in s['standings'])==s['total']*2
                html=c.api('tournaments/'+tid+'/report')['html'];assert 'Shared tournament scheduling' in html
                (folder/(tid+'.html')).write_text(html,encoding='utf-8')
                report['tournaments'].append({'name':s['name'],'games':s['total'],'pairs':s['complete_pairs'],'pgn':c.pgn(tid,s['total'])})
            assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        assert max(s['tournaments'] for s in samples)>=3
        assert any(s['gpu']==1 and s['games']>1 for s in samples)
        report['resource_sharing']={'peak_tournaments':max(s['tournaments'] for s in samples),'peak_games':max(s['games'] for s in samples),'peak_cpu_reservation':max(s['cpu'] for s in samples),'peak_lc0_instances':max(s['gpu'] for s in samples),'cpu_gpu_overlap':True}
        report['pure_node_commands']=len(commands);report['startup_seconds']=c.timings;report['passed']=True
    except BaseException as exc:report['failure']=repr(exc);raise
    finally:
        c.stop();output.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2),flush=True)


if __name__=='__main__':main()
