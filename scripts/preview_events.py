"""Disposable event UI fixture; never opens the user's tournament data."""
import asyncio,json,sys,time
from pathlib import Path
from aiohttp import web
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from arena.server import create_app


async def main():
    folder=ROOT/'test-output'/('events-ui-'+time.strftime('%Y%m%d-%H%M%S'))
    app=await create_app(folder,'event-review');app['stop']=asyncio.Event();db=app['db']
    profiles=[]
    for i in range(6):
        p=await db.call('save_profile',{'name':f'Engine {i+1}','path':sys.executable,'args':[str(ROOT/'tests/fault_engine.py'),'--wait','.04'],'threads':1,'hash':1})
        profiles.append(p)
    t=await db.call('create_tournament','Source conditions',profiles,{'format':'round_robin','cycles':1,'concurrency':2,'max_plies':4,'time_control':{'kind':'nodes','nodes':100}})
    server=web.AppRunner(app);await server.setup();site=web.TCPSite(server,'127.0.0.1',0);await site.start();port=site._server.sockets[0].getsockname()[1]
    ready={'url':f'http://127.0.0.1:{port}/?token=event-review','source':t['id'],'profiles':[p['id'] for p in profiles],'folder':str(folder)}
    (ROOT/'test-output/events-ready.json').write_text(json.dumps(ready),encoding='utf-8');print(json.dumps(ready),flush=True)
    try:await app['stop'].wait()
    finally:await server.cleanup()


if __name__=='__main__':asyncio.run(main())
