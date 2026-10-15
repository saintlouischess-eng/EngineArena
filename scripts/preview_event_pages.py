"""Disposable large-event UI fixture; never runs engines or opens production data."""
import asyncio,contextlib,json,sys,time
from pathlib import Path
from aiohttp import web
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from arena.store import Store
from arena.server import create_app
from arena import events
from test_seasons import create,approve

async def main():
    folder=ROOT/'test-output'/('event-pages-'+str(time.time_ns()))
    with contextlib.closing(Store(folder)) as store:
        qualifier=create(store,n=64);approve(store,qualifier['id']);events.tick(store)
        store.execute("UPDATE tournaments SET state='paused' WHERE state='running'")
        store.execute("UPDATE events SET state='paused'")
        divisions=create(store,n=64,sizes=[16]*4,movement=[2]*3,qualifier={'enabled':False})
        approve(store,divisions['id']);events.tick(store)
        # Freeze synthetic stages before launching the HTTP worker.
        store.execute("UPDATE tournaments SET state='paused' WHERE state='running'")
        store.execute("UPDATE events SET state='paused'")
    app=await create_app(folder,'event-pages-review');app['stop']=asyncio.Event()
    runner=web.AppRunner(app);await runner.setup();site=web.TCPSite(runner,'127.0.0.1',0);await site.start()
    ready={'url':f'http://127.0.0.1:{site._server.sockets[0].getsockname()[1]}/?token=event-pages-review','qualifier':qualifier['id'],'divisions':divisions['id'],'folder':str(folder)}
    (ROOT/'test-output/event-pages-ready.json').write_text(json.dumps(ready));print('Disposable event pages ready.',flush=True)
    try:await app['stop'].wait()
    finally:await runner.cleanup()

if __name__=='__main__':asyncio.run(main())
