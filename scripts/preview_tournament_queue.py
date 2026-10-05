"""Disposable, real UCI fixture tournaments for queue browser acceptance."""
import asyncio
import json
from pathlib import Path
import sys
import time
from aiohttp import web
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from arena.server import create_app

async def main():
    folder=ROOT/'test-output'/('queue-ui-'+time.strftime('%Y%m%d-%H%M%S'))
    app=await create_app(folder,'queue-review');app['stop']=asyncio.Event();db=app['db']
    profiles=[{'name':n,'path':sys.executable,'args':[str(ROOT/'tests/fault_engine.py'),'--wait','.06'],'threads':1,'hash':1} for n in ['Test A','Test B']]
    ids=[]
    for name in ['Opening comparison','Time-control comparison','Long-name tournament for queue layout verification']:
        t=await db.call('create_tournament',name,profiles,{'cycles':3,'concurrency':2,'max_plies':10,'time_control':{'kind':'nodes','nodes':100}})
        ids.append(t['id'])
    server=web.AppRunner(app);await server.setup();site=web.TCPSite(server,'127.0.0.1',0);await site.start();port=site._server.sockets[0].getsockname()[1]
    ready={'url':f'http://127.0.0.1:{port}/?token=queue-review','ids':ids,'folder':str(folder)}
    (ROOT/'test-output/tournament-queue-ready.json').write_text(json.dumps(ready),encoding='utf-8');print(json.dumps(ready),flush=True)
    try:await app['stop'].wait()
    finally:await server.cleanup()

if __name__=='__main__':asyncio.run(main())
