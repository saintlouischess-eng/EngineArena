"""Packaged workflow and recovery using synthetic UCI peers, isolated data only."""
from contextlib import closing
import json,os,sqlite3,subprocess,sys,time
from pathlib import Path
from rc_acceptance import Candidate,ROOT


def main():
    ready=json.loads((ROOT/'test-output/admission-ready.json').read_text())
    source=Path(ready['folder']).resolve();assert source.is_relative_to(ROOT/'test-output')
    folder=ROOT/'test-output'/('admission-package-'+str(time.time_ns()));folder.mkdir()
    with closing(sqlite3.connect((source/'arena.sqlite3').as_uri()+'?mode=ro',uri=True)) as src,closing(sqlite3.connect(folder/'arena.sqlite3')) as dst:src.backup(dst)
    c=Candidate(ROOT/'release/EngineArena/EngineArena.exe',folder)
    proof={'passed':False,'scope':'Synthetic UCI peers and disposable data; owner Season 2 not accessed.','cases':[]}
    with closing(c.db()) as db:before=[tuple(r) for r in db.execute('SELECT id,official,opening FROM games WHERE official IS NOT NULL ORDER BY id')]
    try:
        c.launch();assert c.api('status')['active_games']==0
        with closing(c.db()) as db:assert before==[tuple(r) for r in db.execute('SELECT id,official,opening FROM games WHERE official IS NOT NULL ORDER BY id')]
        packaged=ready|{'folder':str(folder),'url':f"http://127.0.0.1:{c.info['port']}/?token={c.info['token']}"}
        path=ROOT/'test-output/admission-package-ready.json';path.write_text(json.dumps(packaged))
        result=subprocess.run(['node','scripts/validate_admission.cjs'],cwd=ROOT,env=os.environ|{'ADMISSION_READY':str(path)},capture_output=True,text=True,encoding='utf-8',timeout=180,creationflags=subprocess.CREATE_NO_WINDOW)
        assert result.returncode==0,result.stdout+result.stderr
        print(result.stdout,flush=True)
        proof['ui']=json.loads((ROOT/'test-output/admission-ui-review/acceptance.json').read_text())
        ids=[]
        for i in range(6):
            p=c.api('profiles',{'name':f'Simulation {i+1}','path':sys.executable,'args':[str(ROOT/'tests/fault_engine.py'),'--mode','strict_nodes','--wait','.02'],
                 'threads':1,'hash':16,'discover':True})
            ids.append(p['id'])
        t=c.tournament('Synthetic admission source',ids,{'format':'round_robin','cycles':1,'max_plies':8,'concurrency':2,'cpu_budget':2,'time_control':{'kind':'nodes','nodes':100}})
        recovered=False
        for policy,mode in [('full','divisions'),('challenge','progressive')]:
            definition={'kind':'season','sizes':[2,2],'movement':[1],'seasons':2,'cycles':1,'mode':mode,
                'admission':{'policy':policy,'places':2},'qualifier':{'enabled':True,'format':'round_robin','rounds':3,'cycles':1},
                'tie_policy':'standings','review_policy':'automatic','championship':{'enabled':False,'games':2,'tiebreak_games':2},
                'resources':{'cpu_budget':2,'memory_budget_mb':4096,'concurrency':2,'gpu_limits':{}}}
            e=c.api('events',{'source_tid':t['id'],'name':'Packaged simulated '+policy,'definition':definition})
            eid=e['id'];e=c.api('events/'+eid,{'action':'review','revision':e['revision'],'approve':True})
            c.api('events/'+eid,{'action':'run','revision':e['revision']});deadline=time.monotonic()+240;last=0
            while time.monotonic()<deadline:
                e=c.api('events/'+eid+'?export=1');status=c.api('status')
                assert not status['error'],status['error'];assert status['active_games']<=2
                assert status['scheduling']['used']['threads']<=2
                if not recovered and e['official_games']>=2 and status['active_games']:
                    c.kill()
                    with closing(c.db()) as db:
                        committed=[tuple(r) for r in db.execute('SELECT id,official,opening FROM games WHERE official IS NOT NULL ORDER BY id')]
                        unfinished=[r['id'] for r in db.execute('SELECT id FROM attempts WHERE ended IS NULL')]
                    assert unfinished;c.launch()
                    with closing(c.db()) as db:
                        assert committed==[tuple(r) for r in db.execute('SELECT id,official,opening FROM games WHERE official IS NOT NULL ORDER BY id')]
                        assert all(db.execute('SELECT reason FROM attempts WHERE id=?',(aid,)).fetchone()[0]=='interrupted' for aid in unfinished)
                    e=c.api('events/'+eid);assert e['state']=='paused'
                    proof['recovery']={'committed_results_preserved':len(committed),'interrupted_attempts_preserved':len(unfinished)}
                    c.api('events/'+eid,{'action':'run','revision':e['revision']});recovered=True
                if e['state']=='completed':break
                if time.monotonic()-last>15:print(policy,e['official_games'],'/',e['scheduled_games'],flush=True);last=time.monotonic()
                time.sleep(.15)
            assert e['state']=='completed',e['note']
            assert e['official_games']==e['scheduled_games']
            assert all(len({v for g in h['groups'] for v in g})==4 for h in e['season_state']['history'])
            assert len(e['season_state']['candidates'])==6
            view=c.api('events/'+eid+'?view=insights&export=1')
            qualifier=next(s for s in view['stages'] if s['role']=='qualification')
            assert {'Qualified','Not qualified'} <= {p['outcome'] for p in qualifier['entries']}
            proof['cases'].append({'policy':policy,'mode':mode,'games':e['official_games'],'field':4,'candidates':6,
                'admission_decisions':[v['admission'] for v in e['decisions'] if 'admission' in v],
                'pgn':c.pgn(qualifier['tid'],qualifier['official'])})
        with closing(c.db()) as db:
            assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
            assert not db.execute("SELECT 1 FROM attempts WHERE reason IN ('timeout','crash','hang','illegal_move','protocol_error')").fetchone()
        proof.update(passed=True,version='1.8.0',folder=str(folder),startup_seconds=c.timings)
    finally:
        c.stop();(ROOT/'test-output/v180-package.json').write_text(json.dumps(proof,indent=2))
    print('Packaged simulated admission, legal PGNs, field sizes, resource limits and forced recovery passed.',flush=True)


if __name__=='__main__':main()
