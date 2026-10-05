"""Exercise every format, events, queue and experiments through the packaged API.

Only explicit test-output data and freely supplied validation engines are used.
Short capped games and decisive openings test lifecycle, not engine strength.
"""
import argparse
from contextlib import closing
import hashlib
import json
from pathlib import Path
import time
import chess
from rc_acceptance import Candidate, ROOT
from arena.models import FORMATS


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--data',type=Path,required=True)
    parser.add_argument('--exe',type=Path,default=ROOT/'release/EngineArena/EngineArena.exe')
    parser.add_argument('--parallel',action='store_true',help='Run the format matrix concurrently under shared budgets')
    args=parser.parse_args();folder=args.data.resolve()
    assert folder.is_relative_to(ROOT/'test-output') and not folder.exists()
    folder.mkdir();c=Candidate(args.exe,folder)
    evidence={'scope':'Packaged API, 8-ply node-only lifecycle games; decisive event finals. Not endurance or strength testing.',
              'tournaments':[],'events':[],'experiments':[]}
    def until(path,predicate,seconds=180):
        end=time.monotonic()+seconds
        while time.monotonic()<end:
            value=c.api(path);assert not c.api('status')['error']
            if predicate(value):return value
            time.sleep(.1)
        raise AssertionError(value)
    def audit(tid):
        s=c.api('tournaments/'+tid)
        with closing(c.db()) as db:
            games=list(db.execute('SELECT g.white,g.black,a.result FROM games g JOIN attempts a ON a.id=g.official WHERE g.tid=? AND g.invalid=0',(tid,)))
        assert len(games)==s['official_games']==s['total']
        for row in s['standings']:
            w=d=l=0
            for g in games:
                if row['slot'] not in (g['white'],g['black']):continue
                if g['result']=='1/2-1/2':d+=1
                elif (g['result']=='1-0')==(g['white']==row['slot']):w+=1
                else:l+=1
            assert (row['wins'],row['draws'],row['losses'],row['games'])==(w,d,l,w+d+l)
        if s['settings']['paired']:assert s['complete_pairs']*2==len(games)
        html=c.api('tournaments/'+tid+'/report')['html'];assert s['name'] in html
        (folder/(tid+'.html')).write_text(html,encoding='utf-8')
        evidence['tournaments'].append({'name':s['name'],'format':s['settings']['format'],'paired':s['settings']['paired'],
            'games':len(games),'pairs':s['complete_pairs'],'pgn':c.pgn(tid,len(games))})
        print(s['name'],len(games),'passed',flush=True)
    try:
        c.launch();ids=[]
        paths=[ROOT/'validation-engines/stockfish/stockfish/stockfish-windows-x86-64-universal.exe',ROOT/'validation-engines/berserk-14-avx2.exe']
        for i in range(6):ids.append(c.api('profiles',{'name':f'Validation profile {i+1}','path':str(paths[i%2]),'threads':1,'hash':16,'discover':True})['id'])
        settings={'cycles':2,'rounds':3,'concurrency':4,'cpu_budget':4,'max_plies':8,'use_engine_books':False,'tolerance':1,
            'time_control':{'kind':'nodes','nodes':1000},'knockout_tiebreak':'playoff','playoff_limit':1,'playoff_fallback':'seed','playoff_cycles':1,
            'sprt':{'elo0':-5,'elo1':5,'alpha':.05,'beta':.05}}
        queued=[]
        for paired in (True,False):
            for fmt in FORMATS:
                field=ids[:2] if fmt in ('match','sprt') else ids[:5]
                config=settings|{'format':fmt,'paired':paired,'candidates':2,'custom_matchups':[{'a':0,'b':1,'count':2},{'a':1,'b':2,'count':1},{'a':3,'b':4,'count':1}]}
                t=c.tournament(fmt+(' paired' if paired else ' unpaired'),field,config);queued.append(t['id'])
        c.api('tournament-queue',{'action':'add','ids':queued})
        q=c.api('tournament-queue')
        if args.parallel:
            c.api('tournament-queue',{'action':'configure','revision':q['revision'],'execution_mode':'parallel',
                  'resources':{'cpu_budget':4,'memory_budget_mb':8192,'concurrency':4,'gpu_limits':{}}})
            q=c.api('tournament-queue');evidence['execution_mode']='parallel'
        c.api('tournament-queue',{'action':'run','revision':q['revision']})
        q=until('tournament-queue',lambda q:q['mode']=='completed',600)
        assert q['completed']==len(queued);evidence['queue_completed']=q['completed']
        for tid in queued:audit(tid)
        base=c.tournament('Event source',ids,settings|{'format':'round_robin','cycles':1,'paired':True})
        epd=folder/'mate.epd';board=chess.Board('7k/5K2/6Q1/8/8/8/8/8 w - - 0 1');answers=[]
        for move in board.legal_moves:
            child=board.copy();child.push(move)
            if child.is_checkmate():answers.append(move)
        epd.write_text(board.epd(bm=answers,id='mate in one'),encoding='utf-8')
        decisive=c.tournament('Decisive source',ids,settings|{'format':'round_robin','cycles':1,'paired':False},opening_file=str(epd))
        definitions=[{'kind':'multistage','groups':[[0,1,2],[3,4,5]],'advance':2,'initial_format':a,'final_format':b,'initial_cycles':1,'initial_rounds':2,'final_cycles':1}
            for a in ('round_robin','swiss') for b in ('round_robin','knockout')]
        definitions.append({'kind':'league','groups':[[0,1],[2,3],[4,5]],'movement':[1,1],'seasons':2,'initial_cycles':1})
        for n,d in enumerate(definitions):
            e=c.api('events',{'name':f'Packaged event {n+1}','source_tid':decisive['id'] if d.get('final_format')=='knockout' else base['id'],'definition':d})
            c.api('events/'+e['id'],{'action':'run','revision':e['revision']});e=until('events/'+e['id']+'?export=1',lambda e:e['state']=='completed')
            evidence['events'].append({'definition':d,'games':e['official_games'],'decisions':len(e['decisions'])})
            for child in e['children']:
                if child['valid']:audit(child['tid'])
        for tc in ({'kind':'nodes','nodes':1000},{'kind':'depth','depth':4},{'kind':'movetime','seconds':.05}):
            for kind in ('suite','benchmark'):
                j=c.api('experiments',{'name':kind+' '+tc['kind'],'kind':kind,'profiles':ids[:2],'settings':{'time_control':tc,'thread_counts':[1,2],'repeats':2,'tolerance':1},'path':str(epd)})
                c.api('experiments/'+j['id']+'/action',{'action':'start'});j=until('experiments/'+j['id']+'?all=1',lambda j:j['state']=='completed')
                assert j['failures']==0 and j['completed']==j['total']
                for r in j['results']:
                    assert chess.Move.from_uci(r['move']) in chess.Board(r['case']['fen']).legal_moves
                    assert r['measured_nps']==r['reported_nodes']/r['elapsed_seconds']
                    if kind=='benchmark':assert r['effective_threads']==r['case']['threads']
                evidence['experiments'].append({'kind':kind,'control':tc,'cases':j['completed'],'accuracy_pct':j['accuracy_pct']})
        with closing(c.db()) as db:
            failures=list(db.execute("SELECT reason,count(*) FROM attempts WHERE reason IN ('timeout','crash','hang','illegal_move','protocol_error','startup_timeout','readiness_timeout') GROUP BY reason"))
            assert not failures,failures
            assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        saved=c.api('tournaments');q=c.api('tournament-queue');c.stop()
        digest=hashlib.sha256((folder/'games.pgn').read_bytes()).hexdigest();c.launch()
        assert c.api('tournaments')==saved and c.api('tournament-queue')==q
        assert hashlib.sha256((folder/'games.pgn').read_bytes()).hexdigest()==digest
        evidence['restart_retained_results_queue_pgn']=True;evidence['passed']=True
    except BaseException as exc:evidence['failure']=repr(exc);raise
    finally:
        c.stop();folder.with_suffix('.json').write_text(json.dumps(evidence,indent=2),encoding='utf-8')


if __name__=='__main__':main()
