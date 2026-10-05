"""Isolated edit workflow fixture; never opens the user's data folder."""
import asyncio
import contextlib
import json
from pathlib import Path
import sys
import time
from aiohttp import web
import chess
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from arena.server import create_app

async def main():
    folder=ROOT/'test-output'/('tournament-edit-'+time.strftime('%Y%m%d-%H%M%S'))
    app=await create_app(folder,'edit-review');app['stop']=asyncio.Event();runner=app['runner'];db=app['db']
    runner.scheduler.cancel()
    with contextlib.suppress(asyncio.CancelledError):await runner.scheduler
    profiles=[{'id':str(i),'name':f'Test engine {i+1}','path':sys.executable,'args':[str(ROOT/'tests/fault_engine.py')],'threads':1,'hash':2} for i in range(5)]
    for p in profiles:await db.call('execute','INSERT INTO profiles VALUES(?,?,?)',(p['id'],p['name'],json.dumps(p)))
    book=[{'fen':chess.Board.from_chess960_pos(i).fen(),'name':f'Position {i}'} for i in range(12)]
    settings={'format':'round_robin','cycles':3,'concurrency':2,'chess960':True,'opening_order':'shuffle','seed':348,'opening_policy':'pair',
        'opening_source':{'name':'My opening book.pgn','depth':12},'time_control':{'kind':'fischer','seconds':180,'increment':.05},
        'cpu_budget':8,'gpu_limits':{'gpu0':1},'retry_limit':2,'annotations':False,'tolerance':.12,'resign_plies':15}
    rr=await db.call('create_tournament','Saved RR',profiles[:4],settings,book)
    ko=await db.call('create_tournament','Saved KO',profiles[:4],{'format':'knockout','ko_round_games':[6,10],
        'playoff_cycles':2,'playoff_controls':[{'kind':'fischer','seconds':30,'increment':.1},{'kind':'nodes','nodes':500}],
        'opening_policy':'round','cycles':3,'time_control':{'kind':'nodes','nodes':1000}})
    legacy=await db.call('create_tournament','Legacy KO',profiles[:4],{'format':'knockout','knockout_tiebreak':'seed','cycles':2})
    server=web.AppRunner(app);await server.setup();site=web.TCPSite(server,'127.0.0.1',0);await site.start();port=site._server.sockets[0].getsockname()[1]
    ready={'url':f'http://127.0.0.1:{port}/?token=edit-review','rr':rr['id'],'ko':ko['id'],'legacy':legacy['id'],'folder':str(folder)}
    (ROOT/'test-output/tournament-edit-ready.json').write_text(json.dumps(ready),encoding='utf-8');print(json.dumps(ready),flush=True)
    try:await app['stop'].wait()
    finally:await server.cleanup()

if __name__=='__main__':asyncio.run(main())
