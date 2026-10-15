"""Private 1.4 season acceptance; isolated native windows and disposable data only."""
from contextlib import closing
import json,shutil,sqlite3,time
from rc_acceptance import Candidate,ROOT


def main():
    stamp=time.strftime('%Y%m%d-%H%M%S');out=ROOT/'test-output/insights-package.json'
    evidence={'passed':False,'scope':'Short capped workflow checks with handicapped CPU engines, not strength estimates','cases':[]}
    folder=ROOT/'test-output'/('insights-upgrade-'+stamp);folder.mkdir()
    shutil.copy2(ROOT/'test-output/manager-overview-performance.sqlite3',folder/'arena.sqlite3')
    with sqlite3.connect(folder/'arena.sqlite3') as db:
        before=list(db.execute('SELECT id,official,opening FROM games WHERE official IS NOT NULL ORDER BY id'))
    c=Candidate(ROOT/'release/EngineArena/EngineArena.exe',folder)
    try:
        c.launch();assert c.api('status')['active_games']==0
        q=c.api('tournament-queue?scope=events');assert q['filtered_total']==8
        with closing(c.db()) as db:
            assert [tuple(r) for r in db.execute('SELECT id,official,opening FROM games WHERE official IS NOT NULL ORDER BY id')]==before
            assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
            assert all(json.loads(r['body'])['definition']['kind']=='league' for r in db.execute('SELECT body FROM events'))
        evidence['upgrade']={'results_preserved':len(before),'legacy_divisions':8,'no_games_started':True}
    finally:c.stop()
    c=Candidate(ROOT/'release/EngineArena/EngineArena.exe',ROOT/'test-output'/('insights-package-'+stamp))
    evidence['folder']=str(c.folder)
    try:
        c.launch();paths=[ROOT/'validation-engines/stockfish/stockfish/stockfish-windows-x86-64-universal.exe',ROOT/'validation-engines/berserk-14-avx2.exe'];ids=[]
        for i in range(4):
            p=c.api('profiles',{'name':('Stockfish' if i%2==0 else 'Berserk')+f' season check {i+1}',
                'path':str(paths[i%2]),'threads':1,'hash':16,'time_control':{'kind':'nodes','nodes':[200000,500,20000,100][i]},'discover':True})
            ids.append(p['id'])
        upgraded=c.api('profiles',{'name':'Stockfish season check 1 revised','path':str(paths[0]),'threads':1,'hash':16,
                                  'time_control':{'kind':'nodes','nodes':220000},'discover':True})
        book=c.folder/'openings.pgn';book.write_text('1. e4 e5 *\n\n1. d4 d5 *\n\n1. c4 e5 *\n\n1. Nf3 d5 *\n\n1. e4 c5 *\n\n1. d4 Nf6 *\n\n1. e4 e6 *\n\n1. e4 c6 *\n',encoding='utf-8')
        t=c.tournament('Packaged season source',ids,{'format':'round_robin','cycles':1,'max_plies':180,'concurrency':2,'cpu_budget':2,
            'memory_budget_mb':4096,'tolerance':1,'opening_policy':'pair','opening_order':'shuffle','seed':173},opening_file=str(book),book_depth=2)
        eventids=[];recovered=False;overlap=False
        for mode in ('divisions','progressive'):
            d={'kind':'season','mode':mode,'sizes':[2,2],'movement':[1],'seasons':2 if mode=='divisions' else 1,'cycles':1,
                'qualifier':{'enabled':True,'format':'round_robin','rounds':3,'cycles':1},'tie_policy':'standings',
                'review_policy':'season','update_policy':'season','resources':{'cpu_budget':2,'memory_budget_mb':4096,'concurrency':2,'gpu_limits':{}},
                'championship':{'enabled':True,'games':4,'tiebreak_games':2,'controls':[],'play_all':True}}
            e=c.api('events',{'source_tid':t['id'],'name':'Packaged '+mode,'definition':d});eid=e['id'];eventids.append(eid)
            e=c.api('events/'+eid,{'action':'review','revision':e['revision'],'approve':True});c.api('events/'+eid,{'action':'run','revision':e['revision']})
            deadline=time.monotonic()+420;last=0;didupgrade=False;before_upgrade=[]
            while time.monotonic()<deadline:
                status=c.api('status');e=c.api('events/'+eid+'?export=1');assert not status['error'],status['error']
                assert status['active_games']<=2 and status['scheduling']['used']['threads']<=2
                overlap|=len({g['tid'] for g in status['live']})>1
                if time.monotonic()-last>15:
                    print(f"{mode}: {e['state']}, {e['official_games']}/{e['scheduled_games']}, {status['active_games']} active",flush=True);last=time.monotonic()
                if mode=='divisions' and not recovered and e['official_games']>=2 and status['active_games']:
                    c.kill()
                    with closing(c.db()) as db:
                        saved=[dict(r) for r in db.execute('SELECT id,official,opening FROM games WHERE official IS NOT NULL')]
                        unfinished=[r['id'] for r in db.execute('SELECT id FROM attempts WHERE ended IS NULL')]
                    assert unfinished;c.launch();e=c.api('events/'+eid)
                    assert e['state']=='paused' and not c.api('status')['active_games']
                    with closing(c.db()) as db:
                        for g in saved:assert dict(db.execute('SELECT id,official,opening FROM games WHERE id=?',(g['id'],)).fetchone())==g
                        for aid in unfinished:assert db.execute('SELECT reason FROM attempts WHERE id=?',(aid,)).fetchone()[0]=='interrupted'
                    evidence['recovery']={'results_preserved':len(saved),'unfinished_attempts_archived':len(unfinished)};recovered=True
                    c.api('events/'+eid,{'action':'run','revision':e['revision']});continue
                if e['state']=='paused':
                    assert e['season_state']['review'],e['note'];replacements=[]
                    if mode=='divisions' and e['season_state']['season']==2 and not didupgrade:
                        with closing(c.db()) as db:before_upgrade=[tuple(r) for r in db.execute('SELECT tid,slot,profile FROM participants ORDER BY tid,slot')]
                        replacements=[{'slot':0,'profile_id':upgraded['id']}];didupgrade=True
                    e=c.api('events/'+eid,{'action':'review','revision':e['revision'],'approve':True,'replacements':replacements})
                    if before_upgrade:
                        with closing(c.db()) as db:
                            for tid,slot,profile in before_upgrade:assert db.execute('SELECT profile FROM participants WHERE tid=? AND slot=?',(tid,slot)).fetchone()[0]==profile
                    c.api('events/'+eid,{'action':'run','revision':e['revision']})
                if e['state']=='completed':break
                time.sleep(.1)
            assert e['state']=='completed',e
            e=c.api('events/'+eid+'?export=1');assert e['official_games']==e['scheduled_games']
            overview=c.api('events/'+eid+'?view=insights&export=1')
            entrants=c.api('events/'+eid+'?view=careers')['items']
            assert overview['complete'] and overview['all_official']==e['official_games']
            assert sum(p['games'] for p in entrants)==e['official_games']*2
            assert len(overview['champions'])==d['seasons']
            assert not overview['failures']
            for entrant in entrants:
                career=c.api('events/'+eid+'?view=careers&identity='+entrant['identity'])
                assert sum(r['games'] for r in career['rivals'])==career['games']
                assert sum(h['games'] for h in career['history'])==career['games']
            (c.folder/(eid+'-insights.json')).write_text(json.dumps(overview,indent=2),encoding='utf-8')

            if mode=='divisions':assert didupgrade and e['updates']
            case={'insights_reconciled':True,'mode':mode,'games':e['official_games'],'seasons':e['season_state']['history'],'children':[]}
            for child in e['children']:
                tid=child['tid'];s=c.api('tournaments/'+tid)
                assert s['official_games']==s['total']==s['complete_pairs']*2
                with closing(c.db()) as db:
                    games=list(db.execute('SELECT g.white,g.black,a.result FROM games g JOIN attempts a ON a.id=g.official WHERE g.tid=? AND g.invalid=0',(tid,)))
                    for row in s['standings']:
                        wins=draws=losses=0
                        for g in games:
                            if row['slot'] not in (g['white'],g['black']):continue
                            if g['result']=='1/2-1/2':draws+=1
                            elif (g['result']=='1-0')==(g['white']==row['slot']):wins+=1
                            else:losses+=1
                        assert (row['wins'],row['draws'],row['losses'])==(wins,draws,losses)
                html=c.api('tournaments/'+tid+'/report')['html'];assert s['name'] in html
                (c.folder/(tid+'.html')).write_text(html,encoding='utf-8')
                case['children'].append({'name':s['name'],'games':s['total'],'pgn':c.pgn(tid,s['total'])})
            evidence['cases'].append(case);print(f"Passed {mode}: {e['official_games']} games, reports and all four PGN presets",flush=True)
        assert recovered and overlap
        with closing(c.db()) as db:
            failures=[dict(r) for r in db.execute("SELECT reason,count(*) n FROM attempts WHERE reason IN ('crash','timeout','hang','illegal_move','startup_timeout','protocol_error','readiness_timeout') GROUP BY reason")]
            assert not failures,failures
        preview=c.api('events',{'action':'delete_preview','ids':eventids})
        deleted=c.api('events',{'action':'delete','ids':eventids,'expected':preview['events'],'confirmed':True})
        assert deleted['recovered_bytes']>0
        with closing(c.db()) as db:
            assert not db.execute('SELECT 1 FROM events').fetchone()
            assert not db.execute('SELECT 1 FROM event_children').fetchone()
            assert db.execute('SELECT count(*) FROM profiles').fetchone()[0]==5
            assert db.execute('SELECT count(*) FROM tournaments').fetchone()[0]==1
            assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        for backup in c.folder.glob('backups/*.sqlite3'):
            with sqlite3.connect(backup) as db:
                assert not db.execute('SELECT 1 FROM events').fetchone()
                assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        evidence.update(passed=True,parallel_divisions=overlap,failures=failures,deletion={'events':len(eventids),'stages':len(preview['stages']),'recovered_bytes':deleted['recovered_bytes']})
    finally:
        c.stop();out.write_text(json.dumps(evidence,indent=2),encoding='utf-8')
    print(json.dumps({'passed':True,'games':sum(v['games'] for v in evidence['cases']),'recovery':evidence['recovery'],'deletion':evidence['deletion']}),flush=True)

if __name__=='__main__':main()
