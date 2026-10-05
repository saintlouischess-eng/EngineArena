"""Short real-engine acceptance runs in a disposable workspace."""
import asyncio,io,json,sqlite3,sys,time
from pathlib import Path
import chess,chess.pgn
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from arena.runner import Database,Runner
from arena.tournament_report import render


async def main():
    source=Path.home()/'AppData/Local/EngineArena/Data/arena.sqlite3'
    with sqlite3.connect(source.as_uri()+'?mode=ro',uri=True) as con:
        installed=[json.loads(r[0]) for r in con.execute('SELECT body FROM profiles')]
    names=['Stockfish 18','Reckless 0.10.0-dev-7300f044','PlentyChess 8.0.0','Cinder 0.6.1','Alexandria-9.0.0','Integral v8']
    profiles=[]
    for name in names:
        p=next(v for v in installed if v['name']==name)
        profiles.append({'name':name,'path':p['path'],'args':p.get('args',[]),'cwd':p.get('cwd',''),'threads':1,'hash':16,'options':{'Threads':1,'Hash':16}})
    folder=ROOT/'test-output'/('events-real-'+time.strftime('%Y%m%d-%H%M%S'));db=await Database().open(folder);runner=Runner(db);results=[]
    settings={'format':'round_robin','cycles':1,'paired':True,'concurrency':3,'cpu_budget':3,'max_plies':12,'use_engine_books':False,'time_control':{'kind':'nodes','nodes':1000}}
    try:
        base=await db.call('create_tournament','Real source conditions',profiles,settings)
        custom=await db.call('create_tournament','Real custom matchups',profiles,settings|{'format':'custom','custom_matchups':[{'a':0,'b':1,'count':1},{'a':2,'b':3,'count':1},{'a':4,'b':5,'count':1}]})
        await db.call('set_state',custom['id'],'running');await runner.start()
        async def wait(tid=None,eid=None):
            end=time.monotonic()+150
            while time.monotonic()<end:
                assert not runner.error,runner.error
                obj=await db.call('event_call','detail',eid) if eid else await db.call('tournament',tid)
                if obj['state']=='completed':return obj
                await asyncio.sleep(.05)
            raise AssertionError(obj)
        await wait(tid=custom['id']);results.append({'name':'custom','games':6})
        definitions=[{'kind':'multistage','groups':[[0,1,2],[3,4,5]],'advance':2,'initial_format':'round_robin','final_format':'round_robin','initial_cycles':1,'final_cycles':1},
                     {'kind':'league','groups':[[0,1],[2,3],[4,5]],'movement':[1,1],'seasons':2,'initial_cycles':1}]
        for definition in definitions:
            e=await db.call('event_call','create','Real '+definition['kind'],base['id'],definition)
            await db.call('event_call','command',e['id'],'run',e['revision']);e=await wait(eid=e['id'])
            results.append({'name':definition['kind'],'games':e['official_games'],'decisions':len(e['decisions'])})
        mate=await db.call('create_tournament','Real decisive KO source',profiles,settings|{'paired':False},[{'fen':'7k/5K2/6Q1/8/8/8/8/8 w - - 0 1','name':'Mate in one acceptance position'}])
        e=await db.call('event_call','create','Real group to KO',mate['id'],definitions[0]|{'final_format':'knockout'})
        await db.call('event_call','command',e['id'],'run',e['revision']);e=await wait(eid=e['id']);results.append({'name':'groups_to_KO','games':e['official_games']})
        await db.call('export_pending')
        failures=await db.call('rows',"SELECT reason,count(*) n FROM attempts WHERE result<>'*' AND reason IN ('timeout','crash','hang','illegal_move','protocol_error','startup_timeout','readiness_timeout') GROUP BY reason")
        assert not failures,failures
        games=[];stream=io.StringIO((folder/'games.pgn').read_text(encoding='utf-8'));ids=[]
        while g:=chess.pgn.read_game(stream):
            assert not g.errors;list(g.mainline_moves());games.append(g);ids.append(g.headers['AttemptId'])
        assert len(games)==51 and len(set(ids))==51
        tourneys=await db.call('rows',"SELECT id,name FROM tournaments WHERE state='completed'")
        for t in tourneys:
            html=await asyncio.to_thread(render,folder/'arena.sqlite3',t['id'],95,True,True)
            assert '<h2' in html
            (folder/(t['id']+'.html')).write_text(html,encoding='utf-8')
        assert (await db.call('one','PRAGMA integrity_check'))['integrity_check']=='ok'
        evidence={'folder':str(folder),'engines':names,'results':results,'completed_games':51,'unique_legal_pgn':True,'engine_failures':failures,'reports':len(tourneys),'scope':'Node-only, 12-ply capped games plus mate-in-one KO checks; not a strength measurement or long stress test.'}
        (ROOT/'test-output/events-real.json').write_text(json.dumps(evidence,indent=2),encoding='utf-8');print(json.dumps(evidence),flush=True)
    finally:await runner.close()


if __name__=='__main__':asyncio.run(main())
