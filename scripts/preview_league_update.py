"""Disposable 64-participant builder and completed league UI fixture."""
import asyncio,contextlib,json,sys,time
from pathlib import Path
from aiohttp import web
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from arena.store import Store
from arena.server import create_app
from test_league_update import create,drive

async def main():
    folder=ROOT/'test-output'/('league-ui-'+time.strftime('%Y%m%d-%H%M%S'))
    with contextlib.closing(Store(folder)) as s:
        completed=drive(s,create(s)['id'],ties=2)
        from test_seasons import create as season_create,drive as season_drive
        season=season_drive(s,season_create(s,n=5)['id'])
        source=s.create_tournament('64-engine league conditions',[{'name':f'Engine {i+1:02}'} for i in range(64)],
            {'format':'round_robin','cycles':1,'cpu_budget':28,'memory_budget_mb':81920,'concurrency':28,'tolerance':1},backup=False)
    app=await create_app(folder,'league-review');app['stop']=asyncio.Event()
    server=web.AppRunner(app);await server.setup();site=web.TCPSite(server,'127.0.0.1',0);await site.start()
    ready={'url':f'http://127.0.0.1:{site._server.sockets[0].getsockname()[1]}/?token=league-review','source':source['id'],'completed':completed['id'],'season':season['id'],'folder':str(folder)}
    (ROOT/'test-output/league-ready.json').write_text(json.dumps(ready),encoding='utf-8');print(json.dumps(ready),flush=True)
    try:await app['stop'].wait()
    finally:await server.cleanup()

if __name__=='__main__':asyncio.run(main())
