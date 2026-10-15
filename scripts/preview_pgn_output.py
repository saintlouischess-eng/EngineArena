"""Isolated UI fixture for automatic PGN output; no production files or engines."""
import asyncio,contextlib,json,sys,time
from pathlib import Path
from aiohttp import web
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from arena.store import Store
from arena.server import create_app
from test_pgn_readable import make_game
from test_core import profile
import chess

async def main():
    base=ROOT/'test-output'/('pgn-output-ui-'+str(time.time_ns()));folder=base/'data'
    with contextlib.closing(Store(folder)) as store:
        for n in ['Fixture A','Fixture B']:store.save_profile(profile(n))
        one,g=make_game(store,{'fen':chess.STARTING_FEN});store.set_state(one['id'],'paused')
        two,g2=make_game(store,{'fen':chess.STARTING_FEN});store.set_state(two['id'],'paused')
    app=await create_app(folder,'pgn-output-review');app['stop']=asyncio.Event()
    runner=web.AppRunner(app);await runner.setup();site=web.TCPSite(runner,'127.0.0.1',0);await site.start()
    ready={'url':f'http://127.0.0.1:{site._server.sockets[0].getsockname()[1]}/?token=pgn-output-review','one':one['id'],'two':two['id'],'folder':str(folder),'output':str(base/'daily-list.pgn')}
    (ROOT/'test-output/pgn-output-ready.json').write_text(json.dumps(ready));print('Disposable PGN fixture ready.',flush=True)
    try:await app['stop'].wait()
    finally:await runner.cleanup()

if __name__=='__main__':asyncio.run(main())
