"""Packaged scheduling, real UCI/PGN smoke and upgrade on disposable data only."""
from contextlib import closing
import json,shutil,sqlite3,time
from rc_acceptance import Candidate,ROOT


def main():
    stamp=time.strftime('%Y%m%d-%H%M%S');report={'passed':False,'scope':'Short capped real-engine workflow checks, not strength tests','cases':[]}
    output=ROOT/'test-output/schedule-packaged.json'
    # This is an earlier read-only SQLite snapshot already stored in test-output.
    folder=ROOT/'test-output'/('schedule-upgrade-'+stamp);folder.mkdir()
    shutil.copy2(ROOT/'test-output/manager-overview-performance.sqlite3',folder/'arena.sqlite3')
    with sqlite3.connect(folder/'arena.sqlite3') as db:
        before=list(db.execute('SELECT id,official,opening FROM games WHERE official IS NOT NULL ORDER BY id'))
    c=Candidate(ROOT/'release/EngineArena/EngineArena.exe',folder)
    try:
        c.launch();assert c.api('status')['active_games']==0
        q=c.api('tournament-queue?scope=events');assert q['filtered_total']==8
        with closing(c.db()) as db:
            assert [tuple(r) for r in db.execute('SELECT id,official,opening FROM games WHERE official IS NOT NULL ORDER BY id')]==before
            assert 'schedule_index' in [r['name'] for r in db.execute('PRAGMA table_info(games)')]
            assert db.execute('PRAGMA quick_check').fetchone()[0]=='ok'
        report['upgrade']={'results_preserved':len(before),'divisions_visible':8,'no_games_started':True}
    finally:c.stop()

    c=Candidate(ROOT/'release/EngineArena/EngineArena.exe',ROOT/'test-output'/('schedule-package-'+stamp))
    try:
        c.launch();paths=[ROOT/'validation-engines/stockfish/stockfish/stockfish-windows-x86-64-universal.exe',ROOT/'validation-engines/berserk-14-avx2.exe'];ids=[]
        for i in range(4):
            p=c.api('profiles',{'name':('Stockfish' if i%2==0 else 'Berserk')+f' schedule {i+1}',
                'path':str(paths[i%2]),'threads':1,'hash':16,'discover':True})
            ids.append(p['id'])
        for fmt,order in [('round_robin','balanced'),('round_robin','shuffle'),('round_robin','matchup'),('knockout','shuffle'),('swiss','balanced')]:
            t=c.tournament(fmt+' '+order,ids,{'format':fmt,'cycles':2,'rounds':2,'schedule_order':order,'schedule_seed':987,
                'opening_policy':'pair','time_control':{'kind':'nodes','nodes':2000},'cpu_budget':2,'concurrency':2,'memory_budget_mb':4096,
                'knockout_tiebreak':'seed','max_plies':32,'tolerance':1,'retry_limit':0})
            tid=t['id'];c.action(tid,'start');deadline=time.monotonic()+180;killed=False
            while time.monotonic()<deadline:
                status=c.api('status');snapshot=c.api('tournaments/'+tid)
                assert not status['error'] and status['active_games']<=2
                assert snapshot['state'] in ('running','completed'),snapshot.get('note')
                if fmt=='round_robin' and order=='shuffle' and not killed and snapshot['official_games']>=2 and status['active_games']:
                    c.kill()
                    with closing(c.db()) as db:
                        saved=[dict(r) for r in db.execute('SELECT id,official,opening,schedule_index FROM games WHERE official IS NOT NULL')]
                        interrupted=[r['id'] for r in db.execute('SELECT id FROM attempts WHERE ended IS NULL')]
                    assert interrupted;c.launch()
                    with closing(c.db()) as db:
                        for g in saved:
                            assert dict(db.execute('SELECT id,official,opening,schedule_index FROM games WHERE id=?',(g['id'],)).fetchone())==g
                        for aid in interrupted:assert db.execute('SELECT reason FROM attempts WHERE id=?',(aid,)).fetchone()[0]=='interrupted'
                    assert c.api('status')['active_games']==0;c.action(tid,'start');killed=True
                    report['forced_recovery']={'saved_results':len(saved),'unfinished_attempts_preserved':len(interrupted)}
                if snapshot['state']=='completed':break
                time.sleep(.1)
            assert snapshot['state']=='completed',snapshot['state']
            if fmt=='round_robin' and order=='shuffle':assert killed
            assert snapshot['official_games']==snapshot['total']==snapshot['complete_pairs']*2
            html=c.api('tournaments/'+tid+'/report')['html'];assert 'Game scheduling' in html
            expected={'balanced':'Balanced round order','shuffle':'Seeded shuffle','matchup':'Matchup order'}[order];assert expected in html
            pgn=c.pgn(tid,snapshot['total'])
            with closing(c.db()) as db:
                assert db.execute('SELECT count(DISTINCT schedule_index) FROM games WHERE tid=? AND invalid=0',(tid,)).fetchone()[0]==snapshot['total']
                failures=[dict(r) for r in db.execute("SELECT reason,count(*) n FROM attempts WHERE reason IN ('crash','timeout','hang','illegal_move','startup_timeout','protocol_error','readiness_timeout') GROUP BY reason")]
                assert not failures,failures
            report['cases'].append({'format':fmt,'order':order,'games':snapshot['total'],'pairs':snapshot['complete_pairs'],'pgn':pgn})
            print(f"Passed {fmt} / {order}: {snapshot['total']} games",flush=True)
        report['passed']=True
    finally:
        c.stop();output.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({'passed':True,'upgrade':report['upgrade'],'recovery':report['forced_recovery'],'games':sum(v['games'] for v in report['cases'])}),flush=True)


if __name__=='__main__':main()
