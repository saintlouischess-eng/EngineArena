"""Real-engine lifecycle matrix. Disposable data; short games, not strength tests."""
import asyncio,io,json,sqlite3,sys,time
from pathlib import Path
import chess,chess.pgn
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from arena.runner import Database,Runner
from arena.tournament_report import render
from arena.models import FORMATS


async def main():
    source=Path.home()/'AppData/Local/EngineArena/Data/arena.sqlite3'
    with sqlite3.connect(source.as_uri()+'?mode=ro',uri=True) as con:installed=[json.loads(r[0]) for r in con.execute('SELECT body FROM profiles')]
    names=['Stockfish 18','Reckless 0.10.0-dev-7300f044','PlentyChess 8.0.0','Cinder 0.6.1','Alexandria-9.0.0','Integral v8'];profiles=[]
    for name in names:
        p=next(v for v in installed if v['name']==name)
        profiles.append({'name':name,'path':p['path'],'args':p.get('args',[]),'cwd':p.get('cwd',''),'threads':1,'hash':16,'options':{'Threads':1,'Hash':16}})
    folder=ROOT/'test-output'/('all-formats-real-'+time.strftime('%Y%m%d-%H%M%S'));db=await Database().open(folder);runner=Runner(db);results=[];experiments=[];events=[]
    settings={'cycles':2,'rounds':3,'concurrency':4,'cpu_budget':4,'max_plies':8,'use_engine_books':False,'time_control':{'kind':'nodes','nodes':1000},'knockout_tiebreak':'playoff','playoff_limit':1,'playoff_fallback':'seed','playoff_cycles':1,'sprt':{'elo0':-5,'elo1':5,'alpha':.05,'beta':.05}}
    async def wait(tid=None,eid=None,xid=None):
        end=time.monotonic()+180
        while time.monotonic()<end:
            assert not runner.error,runner.error
            obj=await db.call('event_call','detail',eid) if eid else await db.call('experiment_get',xid,0,50) if xid else await db.call('snapshot',tid)
            if obj['state']=='completed':return obj
            await asyncio.sleep(.05)
        raise AssertionError(obj)
    async def audit(tid):
        snap=await db.call('snapshot',tid);games=await db.call('rows','SELECT g.white,g.black,a.result FROM games g JOIN attempts a ON a.id=g.official WHERE g.tid=? AND g.invalid=0',(tid,))
        assert snap['official_games']==snap['total']==len(games)
        for row in snap['standings']:
            # Verify each engine's game denominator directly from committed games.
            relevant=[g for g in games if row['slot'] in (g['white'],g['black'])]
            assert row['games']==len(relevant),(snap['name'],row,relevant)
            assert row['wins']+row['draws']+row['losses']==len(relevant)
        if snap['settings']['paired']:assert snap['complete_pairs']*2==len(games)
        if snap['settings']['format'] in ('knockout','double_elimination'):assert snap['knockout']['champion']
        html=await asyncio.to_thread(render,folder/'arena.sqlite3',tid,95,True,True)
        assert snap['name'] in html and any(p['name'] in html for p in profiles)
        (folder/(tid+'.html')).write_text(html,encoding='utf-8')
        return {'name':snap['name'],'format':snap['settings']['format'],'paired':snap['settings']['paired'],'games':len(games),'complete_pairs':snap['complete_pairs'],'report':tid+'.html'}
    try:
        await runner.start()
        for paired in (True,False):
            for fmt in FORMATS:
                field=profiles[:2] if fmt in ('match','sprt') else profiles[:5]
                config=settings|{'format':fmt,'paired':paired,'candidates':2,'custom_matchups':[{'a':0,'b':1,'count':2},{'a':1,'b':2,'count':1},{'a':3,'b':4,'count':1}]}
                t=await db.call('create_tournament',fmt+(' paired' if paired else ' unpaired'),field,config)
                await db.call('set_state',t['id'],'running');await wait(tid=t['id']);results.append(await audit(t['id']))
                print(json.dumps(results[-1]),flush=True)
        base=await db.call('create_tournament','Event source',profiles,settings|{'format':'round_robin','cycles':1,'paired':True})
        decisive=await db.call('create_tournament','Decisive event source',profiles,settings|{'format':'round_robin','cycles':1,'paired':False},[{'fen':'7k/5K2/6Q1/8/8/8/8/8 w - - 0 1','name':'Mate in one acceptance position'}])
        for initial in ('round_robin','swiss'):
            for final in ('round_robin','knockout'):
                d={'kind':'multistage','groups':[[0,1,2],[3,4,5]],'advance':2,'initial_format':initial,'final_format':final,'initial_cycles':1,'initial_rounds':2,'final_cycles':1}
                source=decisive if final=='knockout' else base
                e=await db.call('event_call','create',initial+' to '+final,source['id'],d);await db.call('event_call','command',e['id'],'run',e['revision']);e=await wait(eid=e['id'])
                events.append({'name':e['name'],'games':e['official_games'],'decisions':len(e['decisions'])});print(json.dumps(events[-1]),flush=True)
        d={'kind':'league','groups':[[0,1],[2,3],[4,5]],'movement':[1,1],'seasons':2,'initial_cycles':1}
        e=await db.call('event_call','create','Two-season league',base['id'],d);await db.call('event_call','command',e['id'],'run',e['revision']);e=await wait(eid=e['id']);events.append({'name':e['name'],'games':e['official_games'],'decisions':len(e['decisions'])})
        mate=chess.Board('7k/5K2/6Q1/8/8/8/8/8 w - - 0 1');answers=[]
        for move in mate.legal_moves:
            child=mate.copy();child.push(move)
            if child.is_checkmate():answers.append(move)
        epd=folder/'known-answers.epd';epd.write_text(mate.epd(bm=answers,id='mate in one')+'\n'+chess.Board().epd(am=[chess.Move.from_uci('a2a3')],id='avoid a3'),encoding='utf-8')
        for tc in ({'kind':'nodes','nodes':1000},{'kind':'depth','depth':4},{'kind':'movetime','seconds':.05}):
            for kind in ('suite','benchmark'):
                j=await db.call('experiment_create',kind+' '+tc['kind'],kind,profiles[:2],{'time_control':tc,'thread_counts':[1,2],'repeats':2},str(epd));await db.call('experiment_state',j['id'],'running');await wait(xid=j['id'])
                j=await db.call('experiment_get',j['id']);assert j['failures']==0,j
                assert j['completed']==j['total']==(4 if kind=='suite' else 8)
                for r in j['results']:
                    board=chess.Board(r['case']['fen']);assert chess.Move.from_uci(r['move']) in board.legal_moves
                    assert r['measured_nps']==r['reported_nodes']/r['elapsed_seconds']
                    if kind=='benchmark':assert r['effective_threads']==r['case']['threads']
                (folder/(j['id']+'.json')).write_text(json.dumps(j,indent=2),encoding='utf-8')
                experiments.append({'kind':kind,'limit':tc,'cases':j['completed'],'accuracy_pct':j['accuracy_pct'],'failures':j['failures']});print(json.dumps(experiments[-1]),flush=True)
        for t in await db.call('rows',"SELECT id FROM tournaments WHERE state='completed' AND id IN (SELECT tid FROM event_children)"):results.append(await audit(t['id']))
        await db.call('export_pending');failures=await db.call('rows',"SELECT reason,count(*) n FROM attempts WHERE result<>'*' AND reason IN ('timeout','crash','hang','illegal_move','protocol_error','startup_timeout','readiness_timeout') GROUP BY reason");assert not failures,failures
        ids=[];stream=io.StringIO((folder/'games.pgn').read_text(encoding='utf-8'))
        while g:=chess.pgn.read_game(stream):
            assert not g.errors;list(g.mainline_moves());ids.append(g.headers['AttemptId'])
        assert len(ids)==len(set(ids))==sum(r['games'] for r in results)
        assert (await db.call('one','PRAGMA integrity_check'))['integrity_check']=='ok'
        evidence={'folder':str(folder),'engines':names,'tournaments':results,'events':events,'experiments':experiments,'legal_unique_pgn_games':len(ids),'scope':'Eight-ply, 1000-node lifecycle acceptance. Standalone KO ties use one playoff then the explicitly selected seed fallback; KO event finals use continuous play from decisive mate-in-one openings. Regression tests separately cover continuous tie playoffs, corrections, and recovery. Not a strength comparison or extended endurance test.'}
        (ROOT/'test-output/all-formats-real.json').write_text(json.dumps(evidence,indent=2),encoding='utf-8');print('PASS: '+str(len(ids))+' legal games',flush=True)
    finally:await runner.close()


if __name__=='__main__':asyncio.run(main())
