"""Isolated workflow review. No production folders or engine processes."""
import asyncio,json,random,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import chess
from aiohttp import web
from arena.server import create_app
from arena.models import Clock,TimeControl
from arena.crown_marks import CrownMarks

async def main():
    folder=ROOT/'test-output'/('workflow-'+str(time.time_ns()));app=await create_app(folder,'workflow-review');app['stop']=asyncio.Event();db=app['db'];r=app['runner']
    r.scheduler.cancel();await asyncio.gather(r.scheduler,return_exceptions=True)
    profiles=[]
    for i,name in enumerate(['Stockfish development · review','Stockfish release · review','GPU profile · review']):
        profiles.append(await db.call('save_profile',{'name':name,'path':sys.executable,'args':[str(ROOT/'tests/fault_engine.py')],'threads':1,'hash':64,**({'gpu_group':'gpu0'} if i==2 else {})}))
    done=await db.call('create_tournament','Completed match · workflow fixture',profiles[:2],{'cycles':1,'concurrency':1},backup=False)
    await db.call('set_state',done['id'],'running');await db.call('fill_queue',done['id'],2)
    for result,reason in [('1-0','timeout'),('1/2-1/2','adjudication')]:
        g=await db.call('claim',done['id']);await db.call('finish',g['aid'],result,reason)
    await db.call('execute',"UPDATE tournaments SET state='completed' WHERE id=?",(done['id'],))
    t=await db.call('create_tournament','Live scoresheet · workflow fixture',profiles[:2],{'cycles':10,'concurrency':1},backup=False)
    await db.call('set_state',t['id'],'running');await db.call('fill_queue',t['id'],2);g=await db.call('claim',t['id'])
    board=chess.Board();marks=CrownMarks(board);rng=random.Random(251);clocks={s:Clock(TimeControl.parse({'kind':'fischer','seconds':180,'increment':2})).snapshot() for s in ('white','black')}
    for ply in range(1,81):
        if board.is_game_over():break
        move=rng.choice(list(board.legal_moves));san=board.san(move);marks.advance(board,move);board.push(move);side='white' if ply%2 else 'black';clocks[side]['remaining']-=.6
        info={'depth':22+ply%4,'seldepth':32,'cp':42-ply,'nodes':1234567+ply*1000,'nps':2470000,'time':530}
        await db.call('move',g['aid'],ply,move.uci(),san,board.fen(),.6,clocks,info)
    live={'tid':t['id'],'tournament_name':t['name'],'game':g['id'],'number':0,'fen':board.fen(),'crown_squares':marks.snapshot(),'white':profiles[0],'black':profiles[1],'status':'Thinking','ply':ply,'san':san,'last_move':move.uci(),'clock_active':'white','clocks':clocks,'search_started':time.monotonic(),'info':info,'info_side':side,'searches':{}}
    r.live[g['aid']]=live
    await db.call('execute','INSERT OR REPLACE INTO preferences VALUES(?,?)',('ui',json.dumps({'theme':'dark','split':45,'panels':{'standings':{'visible':False},'games':{'visible':False},'live':{'visible':False},'search':{'visible':False},'focus':{'column':'left','height':740},'moves':{'column':'right','height':600}},'focus3d':False})))
    async def finish(request):
        r.live.clear();await db.call('finish',g['aid'],'1/2-1/2','adjudication');return web.json_response({'ok':True})
    app.router.add_post('/fixture/finish',finish)
    async def step(request):
        move=next(iter(board.legal_moves));san=board.san(move);marks.advance(board,move);board.push(move);live['ply']+=1
        await db.call('move',g['aid'],live['ply'],move.uci(),san,board.fen(),.6,clocks,info)
        live.update(fen=board.fen(),san=san,last_move=move.uci(),crown_squares=marks.snapshot())
        return web.json_response({'ply':live['ply']})
    app.router.add_post('/fixture/step',step)
    server=web.AppRunner(app);await server.setup();site=web.TCPSite(server,'127.0.0.1',0);await site.start();port=site._server.sockets[0].getsockname()[1]
    ready={'url':f'http://127.0.0.1:{port}/?token=workflow-review','tid':t['id'],'completed':done['id'],'gid':g['id'],'folder':str(folder),'profiles':[p['id'] for p in profiles]}
    (ROOT/'test-output/workflow-ready.json').write_text(json.dumps(ready),encoding='utf-8');print(json.dumps(ready),flush=True)
    try:await app['stop'].wait()
    finally:r.live.clear();await server.cleanup()

if __name__=='__main__':asyncio.run(main())
