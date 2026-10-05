"""Packaged 1.2 acceptance using real CPU engines and disposable data only."""
from contextlib import closing
import hashlib,json,time
from rc_acceptance import Candidate,ROOT


def main():
    folder=ROOT/'test-output'/('workflow-packaged-'+str(time.time_ns()));c=Candidate(ROOT/'release/EngineArena/EngineArena.exe',folder)
    evidence={'scope':'Short packaged real-engine/recovery check; not endurance or clean-machine setup','passed':False,'folder':str(folder)}
    try:
        c.launch()
        files=[ROOT/'validation-engines/stockfish/stockfish/stockfish-windows-x86-64-universal.exe',ROOT/'validation-engines/berserk-14-avx2.exe']
        source=[{'name':'Cute imported Stockfish','command':str(files[0]),'protocol':'uci','options':[{'name':'Threads','value':1},{'name':'Hash','value':16}]},
                {'app':{'name':'Banksia imported Berserk','command':str(files[1]),'protocol':'uci'},'options':[{'name':'Threads','value':1},{'name':'Hash','value':16}]}]
        body={'source':source,'preview':True}
        preview=c.api('profiles/import-preview',body);assert preview['ready']==2
        result=c.api('profiles/import-preview',body|{'preview':False,'selected':[0,1]});assert result['count']==2
        assert c.api('profiles/import-preview',body|{'preview':False,'selected':[0,1]})['count']==0
        profiles=c.api('profiles')['items']
        # Exercise the imported launch settings through UCI discovery separately.
        for p in profiles:
            discovered=c.api('profiles/discover',p);assert discovered['identity']['name'];assert discovered['options']['Threads']==1
        master=folder/'opening-suite.pgn';master.write_text('1. e4 e5 2. Nf3 Nc6 *\n\n1. d4 d5 2. c4 e6 *\n',encoding='utf-8')
        t=c.tournament('1.2 real node-only acceptance',[p['id'] for p in profiles],{'cycles':3,'concurrency':1,'max_plies':40,'time_control':{'kind':'nodes','nodes':30000}},common_control=True,opening_file=str(master),book_depth=4)
        tid=t['id'];c.action(tid,'start');deadline=time.monotonic()+90;latencies=[];sheets=0
        while time.monotonic()<deadline:
            s=c.api('status');snap=c.api('tournaments/'+tid)
            if s['live']:
                g=s['live'][0];start=time.perf_counter();data=c.api(f"games/{g['game']}/moves?after={max(0,g['ply']-4)}&limit=4");latencies.append((time.perf_counter()-start)*1000);sheets+=1
                assert len(data['items'])<=4
                for m in data['items']:assert all(k['control']['kind']=='nodes' and k['remaining'] is None for k in m['clocks'].values())
                if snap['official_games']>=1 and g['ply']>=2:break
            time.sleep(.05)
        else:raise AssertionError('No committed result plus active game before crash test')
        c.kill()
        with closing(c.db()) as db:
            committed=[tuple(r) for r in db.execute('SELECT id,official FROM games WHERE tid=? AND official IS NOT NULL ORDER BY id',(tid,))]
            unfinished=[r[0] for r in db.execute('SELECT a.id FROM attempts a JOIN games g ON g.id=a.gid WHERE g.tid=? AND a.ended IS NULL',(tid,))]
        assert committed and unfinished
        c.launch();snap=c.api('tournaments/'+tid);assert snap['state']=='paused' and snap['official_games']==len(committed)
        with closing(c.db()) as db:
            assert [tuple(r) for r in db.execute('SELECT id,official FROM games WHERE tid=? AND official IS NOT NULL ORDER BY id',(tid,))]==committed
            assert all(db.execute('SELECT reason FROM attempts WHERE id=?',(aid,)).fetchone()[0]=='interrupted' for aid in unfinished)
        c.action(tid,'start');final,performance=c.wait(tid,120);assert final['official_games']==6 and final['complete_pairs']==3
        complete=c.api(f'tournaments/{tid}/completion');assert complete['state']=='completed' and complete['last_game']
        sheet=c.api(f"games/{complete['last_game']}/moves");assert sheet['attempt']['official'] and sheet['attempt']['ended'];assert len(sheet['opening_moves'])==4
        report=c.api(f'tournaments/{tid}/report?technical=0')['html'];assert '1.2 real node-only acceptance' in report and 'opening-suite.pgn' in report
        (folder/'report.html').write_text(report,encoding='utf-8')
        evidence.update(passed=True,tournament=tid,official_games=6,opening_pairs=3,imported_profiles=2,duplicate_profiles_skipped=True,
            recovered_committed=len(committed),preserved_interrupted=len(unfinished),pgn=c.pgn(tid,6),scoresheet_requests=sheets,
            scoresheet_max_ms=max(latencies),scoresheet_p95_ms=sorted(latencies)[int(.95*(len(latencies)-1))],performance=performance,
            startup_seconds=c.timings,worker_sha256=hashlib.sha256((ROOT/'release/EngineArena/worker/ArenaWorker.exe').read_bytes()).hexdigest())
        (ROOT/'test-output/workflow-package-ready.json').write_text(json.dumps({'folder':str(folder),'tid':tid,'gid':complete['last_game']}),encoding='utf-8')
    finally:
        c.stop();(ROOT/'test-output/workflow-packaged-result.json').write_text(json.dumps(evidence,indent=2),encoding='utf-8')
    print(json.dumps(evidence,indent=2),flush=True)

if __name__=='__main__':main()
