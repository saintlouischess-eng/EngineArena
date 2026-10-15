"""Isolated simulated-season fixture; never opens the installed workspace."""
import asyncio, contextlib, json, sys, time
from pathlib import Path
from aiohttp import web
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from arena.store import Store
from arena.server import create_app
from test_seasons import create,drive

async def main():
    folder=ROOT/'test-output'/('admission-ui-'+time.strftime('%Y%m%d-%H%M%S'))
    with contextlib.closing(Store(folder)) as s:
        completed=drive(s,create(s,n=12,sizes=[4,4],admission={'policy':'challenge','places':2})['id'])
        legacy=create(s,n=8)
        source=s.create_tournament('300 candidate engines',[{'name':f'Candidate {i+1:03}'} for i in range(300)],
            {'format':'round_robin','cycles':1,'cpu_budget':4,'memory_budget_mb':8192,'concurrency':2,'tolerance':1},backup=False)
    app=await create_app(folder,'admission-fixture');app['stop']=asyncio.Event()
    server=web.AppRunner(app);await server.setup();site=web.TCPSite(server,'127.0.0.1',0);await site.start()
    ready={'url':f'http://127.0.0.1:{site._server.sockets[0].getsockname()[1]}/?token=admission-fixture',
           'source':source['id'],'completed':completed['id'],'legacy':legacy['id'],'folder':str(folder)}
    (ROOT/'test-output/admission-ready.json').write_text(json.dumps(ready),encoding='utf-8')
    print('Admission fixture ready',flush=True)
    try:await app['stop'].wait()
    finally:await server.cleanup()

if __name__=='__main__':asyncio.run(main())
