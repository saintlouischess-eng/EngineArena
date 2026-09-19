"""Isolated synthetic display fixture; no engine executables are launched."""
import asyncio
import contextlib
import json
from pathlib import Path
import secrets
import sys
import time
from aiohttp import web
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from arena.server import create_app

async def main():
    folder=ROOT/'test-output'/('results-ui-'+time.strftime('%Y%m%d-%H%M%S'));folder.mkdir()
    token=secrets.token_urlsafe(32);app=await create_app(folder,token);db=app['db'];runner=app['runner'];runner.scheduler.cancel()
    with contextlib.suppress(asyncio.CancelledError):await runner.scheduler
    profiles=[]
    for i in range(120):profiles.append(await db.call('save_profile',{'name':f'Engine {120-i:03}'+(' (clone)' if i%10==0 else ''),'path':sys.executable,'threads':1,'hash':16}))
    t=await db.call('create_tournament','Results controls · synthetic display fixture',profiles,{'format':'round_robin','cycles':1,'paired':False,'concurrency':2})
    for i in range(119):
        await db.call('execute','UPDATE aggregates SET w=?,d=30,l=20 WHERE tid=? AND a=? AND b=-1',(i,t['id'],i))
        await db.call('execute','UPDATE rankings SET score=?,wins=? WHERE tid=? AND slot=?',(i+15,i,t['id'],i))
    await db.call('execute',"INSERT OR REPLACE INTO preferences VALUES('ui',?)",(json.dumps({'fontSize':14,'split':75,'panels':{'search':{'visible':False},'focus':{'visible':False},'live':{'visible':False}}}),))
    app['stop']=asyncio.Event();server=web.AppRunner(app);await server.setup();site=web.TCPSite(server,'127.0.0.1',0);await site.start()
    port=site._server.sockets[0].getsockname()[1]
    info={'url':f'http://127.0.0.1:{port}/?token={token}','port':port,'token':token,'folder':str(folder),'tid':t['id']}
    (ROOT/'test-output/results-ui-ready.json').write_text(json.dumps(info));print(json.dumps(info),flush=True)
    await app['stop'].wait();await server.cleanup()

asyncio.run(main())
