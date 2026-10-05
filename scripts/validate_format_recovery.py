"""Kill the development desktop during each format and each experiment kind."""
import json,sys,time
from contextlib import closing
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
from rc_acceptance import Candidate
from arena.models import FORMATS


def main():
    folder=ROOT/'test-output'/('format-recovery-'+time.strftime('%Y%m%d-%H%M%S'));folder.mkdir()
    c=Candidate(ROOT/'build/development/EngineArena.exe',folder);checks=[]
    def until(read,predicate,seconds=90):
        end=time.monotonic()+seconds
        while time.monotonic()<end:
            value=read()
            if predicate(value):return value
            time.sleep(.05)
        raise AssertionError(value)
    try:
        c.launch();profiles=[];gate=folder/'kill-gate';waiting=folder/'kill-gate.waiting'
        def block():
            gate.write_text('block search');until(waiting.exists,bool)
        def unblock():
            gate.unlink(missing_ok=True);waiting.unlink(missing_ok=True)
        for n in range(5):profiles.append(c.api('profiles',{'name':f'Recovery fixture {n+1}','path':sys.executable,'args':[str(ROOT/'tests/fault_engine.py'),'--mode','recover_gate','--marker',str(gate),'--wait','.12'],'threads':1,'hash':1,'discover':False})['id'])
        for fmt in FORMATS:
            field=profiles[:2] if fmt in ('match','sprt') else profiles
            settings={'format':fmt,'paired':fmt not in ('knockout','double_elimination'),'cycles':2,'rounds':2,'max_plies':4,'concurrency':1,'time_control':{'kind':'nodes','nodes':100},'candidates':2,'knockout_tiebreak':'seed','custom_matchups':[{'a':0,'b':1,'count':2},{'a':2,'b':3,'count':1}],'sprt':{'elo0':-5,'elo1':5,'alpha':.05,'beta':.05}}
            t=c.tournament('Forced recovery '+fmt,field,settings);tid=t['id'];c.action(tid,'start')
            # First pair/game is committed while later games remain in flight.
            before=until(lambda:c.api('tournaments/'+tid),lambda s:s['official_games']>0 and s['counts'].get('running',0)>0)
            block()
            with closing(c.db()) as con:committed={r['official'] for r in con.execute('SELECT official FROM games WHERE tid=? AND official IS NOT NULL',(tid,))}
            c.kill();unblock();c.launch();recovered=c.api('tournaments/'+tid)
            assert recovered['state']=='paused' and recovered['official_games']>=before['official_games'],recovered
            with closing(c.db()) as con:
                retained={r['official'] for r in con.execute('SELECT official FROM games WHERE tid=? AND official IS NOT NULL',(tid,))}
                assert committed<=retained
                archived=con.execute("SELECT count(*) n FROM attempts a JOIN games g ON g.id=a.gid WHERE g.tid=? AND a.reason='interrupted'",(tid,)).fetchone()['n'];assert archived>0
            c.action(tid,'start');finished,_=c.wait(tid,timeout=90);c.pgn(tid,finished['official_games'])
            checks.append({'format':fmt,'retained':len(committed),'interrupted':archived,'completed':finished['official_games']});print(json.dumps(checks[-1]),flush=True)
        epd=folder/'recover.epd';epd.write_text('\n'.join('rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - am a3; id "case '+str(i)+'";' for i in range(6)))
        for kind in ('suite','benchmark'):
            j=c.api('experiments',{'name':'Recovery '+kind,'kind':kind,'profiles':profiles[:1],'settings':{'time_control':{'kind':'nodes','nodes':100},'thread_counts':[1,2],'repeats':3},'path':str(epd)});eid=j['id'];c.api('experiments/'+eid+'/action',{'action':'start'})
            before=until(lambda:c.api('experiments/'+eid),lambda x:x['completed']>0 and x['active']==1);kept={r['attempt_id'] for r in before['results'] if r['official']}
            block();c.kill();unblock();c.launch();recovered=c.api('experiments/'+eid);assert recovered['state']=='paused' and recovered['completed']>=before['completed'];assert any(r.get('reason')=='interrupted' and not r['official'] for r in recovered['results'])
            c.api('experiments/'+eid+'/action',{'action':'start'});done=until(lambda:c.api('experiments/'+eid+'?all=1'),lambda x:x['state']=='completed')
            official=[r for r in done['results'] if r['official']];assert len(official)==6 and len({r['number'] for r in official})==6 and kept<={r['attempt_id'] for r in official}
            checks.append({'experiment':kind,'retained':len(kept),'completed':6,'archived':len(done['results'])-6});print(json.dumps(checks[-1]),flush=True)
        with closing(c.db()) as con:assert con.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        (ROOT/'test-output/format-recovery.json').write_text(json.dumps({'folder':str(folder),'checks':checks,'desktop_kills':12,'engine_orphans':0},indent=2),encoding='utf-8')
    finally:c.stop()


if __name__=='__main__':main()
