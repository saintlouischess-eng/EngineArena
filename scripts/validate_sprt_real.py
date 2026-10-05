"""Isolated real-engine SPRT lifecycle checks, not a strength measurement."""
import asyncio,io,json,sqlite3,sys,time
from pathlib import Path
import chess.pgn
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from arena.runner import Database,Runner
from arena.tournament_report import render

async def main():
    source=Path.home()/'AppData/Local/EngineArena/Data/arena.sqlite3'
    with sqlite3.connect(source.as_uri()+'?mode=ro',uri=True) as con:
        installed=[json.loads(r[0]) for r in con.execute('SELECT body FROM profiles')]
    names=['Stockfish 18','Reckless 0.10.0-dev-7300f044'];profiles=[]
    for name in names:
        p=next(v for v in installed if v['name']==name)
        profiles.append({'name':name,'path':p['path'],'args':p.get('args',[]),'cwd':p.get('cwd',''),'threads':1,'hash':16,'options':{'Threads':1,'Hash':16}})
    folder=ROOT/'test-output'/('sprt-real-'+time.strftime('%Y%m%d-%H%M%S'));db=await Database().open(folder);runner=Runner(db);results=[]
    try:
        await runner.start()
        for paired,candidate,elo0,elo1,expect in [(True,1,0,200,'H0'),(False,0,-200,0,'H1'),(True,1,-5,5,'inconclusive')]:
            t=await db.call('create_tournament','SPRT '+expect,profiles,{'format':'sprt','cycles':4 if expect=='inconclusive' else 100,'paired':paired,'sprt_candidate':candidate,'concurrency':4,'cpu_budget':4,'max_plies':12,'use_engine_books':False,'time_control':{'kind':'nodes','nodes':1000},'sprt':{'elo0':elo0,'elo1':elo1,'alpha':.05,'beta':.05}})
            tid=t['id'];await db.call('set_state',tid,'running');deadline=time.monotonic()+90
            while time.monotonic()<deadline:
                assert not runner.error,runner.error
                snap=await db.call('snapshot',tid)
                if snap['state'] in ('paused','completed') and snap['sprt_status']['status']==expect and not runner.live:break
                await asyncio.sleep(.05)
            else:raise AssertionError(snap)
            before=snap['official_games'];evidence=snap['sprt'];cursor=snap['cursor']
            if expect in ('H0','H1'):
                g=await db.call('one','SELECT id FROM games WHERE tid=? AND official IS NOT NULL',(tid,))
                await db.call('requeue',tid,[g['id']],mode='diagnostic');await db.call('set_state',tid,'running')
                deadline=time.monotonic()+30
                while time.monotonic()<deadline:
                    snap=await db.call('snapshot',tid)
                    if snap['state']=='paused' and not runner.live:break
                    await asyncio.sleep(.05)
                assert snap['state']=='paused' and snap['sprt']==evidence and snap['official_games']==before and snap['cursor']==cursor
                assert (await db.call('one',"SELECT count(*) n FROM attempts a JOIN games g ON g.id=a.gid WHERE g.tid=? AND a.mode='diagnostic' AND a.ended IS NOT NULL",(tid,)))['n']==1
            html=await asyncio.to_thread(render,folder/'arena.sqlite3',tid,95,True,True);assert names[candidate] in html
            (folder/(expect+'.html')).write_text(html,encoding='utf-8')
            results.append({'paired':paired,'candidate':names[candidate],'decision':expect,'official_games':before,'samples':evidence.get('samples',0),'diagnostic':expect!='inconclusive'})
        await db.call('export_pending');attempts=await db.call('rows',"SELECT id,reason FROM attempts WHERE ended IS NOT NULL")
        assert all(a['reason']=='max_plies_adjudication' for a in attempts),attempts
        stream=io.StringIO((folder/'games.pgn').read_text(encoding='utf-8'));ids=[]
        while g:=chess.pgn.read_game(stream):
            assert not g.errors;list(g.mainline_moves());ids.append(g.headers['AttemptId'])
        assert len(ids)==len(attempts)==len(set(ids))
        result={'folder':str(folder),'engines':names,'cases':results,'completed_attempts':len(ids),'unique_legal_pgn':True,'scope':'12-ply capped node-only lifecycle checks with wide H0/H1 bounds, not a strength measurement or calibration simulation.'}
        (ROOT/'test-output/sprt-real.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result),flush=True)
    finally:await runner.close()

if __name__=='__main__':asyncio.run(main())
