"""Disposable 64-entry anchor picker fixture; never opens production data."""
import asyncio
import contextlib
import json
from pathlib import Path
import sys
import time
from aiohttp import web

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from arena.store import Store
from arena.server import create_app
from arena.rating_center_report import report
from test_rating_center import profile,finish


async def main():
    folder=ROOT/'test-output'/('anchor-ui-'+time.strftime('%Y%m%d-%H%M%S'))
    with contextlib.closing(Store(folder)) as s:
        ps=[profile(f'Engine {n:02}') for n in range(1,64)]+[profile('Stockfish dev')]
        t=s.create_tournament('Anchor pagination fixture',ps,{'format':'round_robin','cycles':1,'time_control':{'kind':'fischer','seconds':180,'increment':2}},backup=False)
        s.set_state(t['id'],'running');s.fill_queue(t['id'],200)
        finish(s,t['id'],(['1-0','1/2-1/2','0-1','1/2-1/2','1/2-1/2','1/2-1/2']*34)[:200]);s.execute("UPDATE tournaments SET state='paused' WHERE id=?",(t['id'],))
        r=report(s.path,{'category':'blitz','export':'json'})
        assert r['total']==64
        reference=next(x for x in r['items'] if x['name'].startswith('Stockfish'))
        s.rating_center_call('command',{'action':'anchor','category':'blitz','entry':reference['id'],'rating':3700})
    app=await create_app(folder,'anchor-review');app['stop']=asyncio.Event()
    server=web.AppRunner(app);await server.setup();site=web.TCPSite(server,'127.0.0.1',0);await site.start()
    ready={'url':f'http://127.0.0.1:{site._server.sockets[0].getsockname()[1]}/?token=anchor-review','anchor':reference['id'],'folder':str(folder)}
    (ROOT/'test-output/anchor-ready.json').write_text(json.dumps(ready),encoding='utf-8')
    print(json.dumps(ready),flush=True)
    try:await app['stop'].wait()
    finally:await server.cleanup()


if __name__=='__main__':asyncio.run(main())
