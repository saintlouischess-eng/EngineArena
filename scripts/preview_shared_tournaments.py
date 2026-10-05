"""Isolated manager UI fixture. Never opens an installed workspace."""
import argparse,asyncio,json,sys,time
from pathlib import Path
from aiohttp import web
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from arena.server import create_app

async def main():
    folder=ROOT/'test-output'/('manager-ui-'+time.strftime('%Y%m%d-%H%M%S'))
    app=await create_app(folder,'manager-review');app['stop']=asyncio.Event();db=app['db'];ids=[]
    for i,name in enumerate(['GPU comparison','CPU reference','Increment comparison','Opening-book experiment','Long tournament name for laptop layout and readability']):
        profiles=[{'name':f'Fixture {i}-{side}','path':sys.executable,'args':[str(ROOT/'tests/fault_engine.py'),'--wait','.08'],
            'threads':1,'hash':1,'extra_memory_mb':0,'gpu_group':'gpu0' if i==0 and side==0 else ''} for side in range(2)]
        t=await db.call('create_tournament',name,profiles,{'cycles':15,'concurrency':2,'max_plies':12,'time_control':{'kind':'nodes','nodes':100}},backup=False);ids.append(t['id'])
    server=web.AppRunner(app);await server.setup();site=web.TCPSite(server,'127.0.0.1',0);await site.start()
    ready={'url':f'http://127.0.0.1:{site._server.sockets[0].getsockname()[1]}/?token=manager-review','ids':ids,'folder':str(folder)}
    (ROOT/'test-output/manager-ui-ready.json').write_text(json.dumps(ready),encoding='utf-8');print(json.dumps(ready),flush=True)
    try:await app['stop'].wait()
    finally:await server.cleanup()

def packaged():
    from rc_acceptance import Candidate
    folder=ROOT/'test-output'/('manager-ui-packaged-'+time.strftime('%Y%m%d-%H%M%S'))
    c=Candidate(ROOT/'release/EngineArena/EngineArena.exe',folder)
    try:
        c.launch();ids=[]
        for i,name in enumerate(['GPU comparison','CPU reference','Increment comparison','Opening-book experiment','Long tournament name for laptop layout and readability']):
            profiles=[c.api('profiles',{'name':f'Fixture {i}-{side}','path':sys.executable,'args':[str(ROOT/'tests/fault_engine.py'),'--wait','.08'],
                'threads':1,'hash':1,'extra_memory_mb':0,'gpu_group':'gpu0' if i==0 and side==0 else '', 'discover':True})['id'] for side in range(2)]
            t=c.tournament(name,profiles,{'cycles':15,'concurrency':2,'max_plies':12,'time_control':{'kind':'nodes','nodes':100}});ids.append(t['id'])
        ready={'url':f"http://127.0.0.1:{c.info['port']}/?token={c.info['token']}",'ids':ids,'folder':str(folder),'packaged':True}
        (ROOT/'test-output/manager-ui-ready.json').write_text(json.dumps(ready),encoding='utf-8');print(json.dumps(ready),flush=True)
        while c.process.poll() is None:
            time.sleep(.5)
            try:c.api('status')
            except OSError:break
    finally:c.stop()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--packaged',action='store_true');args=parser.parse_args()
    if args.packaged:packaged()
    else:asyncio.run(main())
