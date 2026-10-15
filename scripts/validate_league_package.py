"""Real packaged league and abrupt final recovery; disposable data only."""
from contextlib import closing
import json,time
from rc_acceptance import Candidate,ROOT

def main():
    folder=ROOT/'test-output'/('league-package-'+time.strftime('%Y%m%d-%H%M%S'))
    c=Candidate(ROOT/'release/EngineArena/EngineArena.exe',folder)
    evidence={'scope':'Short packaged real-engine workflow check, depth handicaps and 160-ply cap; not a strength test.',
              'passed':False,'folder':str(folder),'children':[]}
    output=ROOT/'test-output/league-package.json'
    try:
        c.launch();paths=[ROOT/'validation-engines/stockfish/stockfish/stockfish-windows-x86-64-universal.exe',ROOT/'validation-engines/berserk-14-avx2.exe'];ids=[]
        for i in range(6):
            p=c.api('profiles',{'name':('Stockfish' if (i//2)%2==0 else 'Berserk')+f' league check {i+1}',
                'path':str(paths[(i//2)%2]),'threads':1,'hash':16,'time_control':{'kind':'depth','depth':[8,1,3,1,2,1][i]},'discover':True})
            ids.append(p['id'])
        book=folder/'openings.pgn';book.write_text('1. e4 e5 *\n\n1. d4 d5 *\n\n1. c4 e5 *\n\n1. Nf3 d5 *\n\n1. e4 c5 *\n\n1. d4 Nf6 *\n\n1. e4 e6 *\n\n1. e4 c6 *\n',encoding='utf-8')
        t=c.tournament('Packaged league template',ids,{'format':'round_robin','cycles':1,'max_plies':160,'concurrency':2,'cpu_budget':2,'memory_budget_mb':4096,'tolerance':1,'opening_policy':'pair','opening_order':'shuffle','seed':173},opening_file=str(book),book_depth=2)
        d={'kind':'league','groups':[[0,1],[2,3],[4,5]],'movement':[1,1],'seasons':2,'initial_cycles':1,
            'execution_mode':'parallel','resources':{'cpu_budget':2,'memory_budget_mb':4096,'concurrency':2,'gpu_limits':{}},
            'season_openings':'advance','championship':{'enabled':True,'games':4,'tiebreak_games':2,'controls':[]}}
        e=c.api('events',{'source_tid':t['id'],'name':'Packaged season championship','definition':d});eid=e['id']
        assert e['regular_games']==20
        c.api('events/'+eid,{'action':'run','revision':e['revision']});deadline=time.monotonic()+300
        overlap=False;killed=False;last_print=0
        while time.monotonic()<deadline:
            status=c.api('status');assert not status['error'],status['error']
            used=status['scheduling']['used'];assert used['threads']<=2 and used['memory_mb']<=4096 and status['active_games']<=2
            overlap|=len({g['tid'] for g in status['live']})>1
            e=c.api('events/'+eid+'?export=1')
            if time.monotonic()-last_print>15:
                print(f"League: {e['official_games']} / {e['scheduled_games']}, {status['active_games']} active",flush=True);last_print=time.monotonic()
            finals=[x for x in e['children'] if x['role']=='championship' and x['state']=='running']
            if finals and not killed and status['active_games'] and finals[0]['official_games']>=1:
                c.kill()
                with closing(c.db()) as db:
                    committed=[dict(r) for r in db.execute('SELECT id,official,opening FROM games WHERE official IS NOT NULL')]
                    interrupted=[dict(r) for r in db.execute('SELECT id,gid FROM attempts WHERE ended IS NULL')]
                assert interrupted
                c.launch();e=c.api('events/'+eid)
                assert e['state']=='paused' and c.api('status')['active_games']==0
                with closing(c.db()) as db:
                    for g in committed:
                        now=db.execute('SELECT official,opening FROM games WHERE id=?',(g['id'],)).fetchone()
                        assert now['official']==g['official'] and now['opening']==g['opening']
                    for a in interrupted:assert db.execute('SELECT reason FROM attempts WHERE id=?',(a['id'],)).fetchone()[0]=='interrupted'
                evidence['recovery']={'committed_games_preserved':len(committed),'interrupted_attempts_retained':len(interrupted)}
                c.api('events/'+eid,{'action':'run','revision':e['revision']});killed=True
            if e['state']=='completed':break
            time.sleep(.1)
        assert e['state']=='completed' and killed and overlap,e
        e=c.api('events/'+eid+'?export=1');assert len(e['decisions'])==2 and e['official_games']==e['scheduled_games']
        for child in e['children']:
            tid=child['tid'];s=c.api('tournaments/'+tid)
            with closing(c.db()) as db:games=list(db.execute('SELECT g.white,g.black,a.result FROM games g JOIN attempts a ON a.id=g.official WHERE g.tid=? AND g.invalid=0',(tid,)))
            assert len(games)==s['official_games']==s['total']==s['complete_pairs']*2
            for row in s['standings']:
                w=dr=l=0
                for g in games:
                    if row['slot'] not in (g['white'],g['black']):continue
                    if g['result']=='1/2-1/2':dr+=1
                    elif (g['result']=='1-0')==(g['white']==row['slot']):w+=1
                    else:l+=1
                assert (row['wins'],row['draws'],row['losses'])==(w,dr,l)
            html=c.api('tournaments/'+tid+'/report')['html'];assert s['name'] in html
            (folder/(tid+'.html')).write_text(html,encoding='utf-8')
            evidence['children'].append({'name':s['name'],'games':s['official_games'],'pgn':c.pgn(tid,s['official_games'])})
        with closing(c.db()) as db:
            assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
            failures=[dict(r) for r in db.execute("SELECT reason,count(*) n FROM attempts WHERE reason IN ('crash','timeout','hang','illegal_move','startup_timeout','protocol_error','readiness_timeout') GROUP BY reason")]
            assert not failures,failures
        evidence.update(passed=True,official_games=e['official_games'],parallel_divisions=overlap,seasons=e['decisions'],failures=[])
        print(json.dumps({'passed':True,'games':e['official_games'],'recovery':evidence['recovery'],'parallel':overlap}),flush=True)
    finally:
        output.write_text(json.dumps(evidence,indent=2),encoding='utf-8');c.stop()

if __name__=='__main__':main()
