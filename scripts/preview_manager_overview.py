"""Disposable manager fixture, separate from the owner's running league."""
import asyncio,contextlib,json,sys,time
from pathlib import Path
from aiohttp import web
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from arena.store import Store
from arena.server import create_app
from test_core import profile

async def main():
    folder=ROOT/'test-output'/('manager-overview-'+time.strftime('%Y%m%d-%H%M%S'))
    with contextlib.closing(Store(folder)) as s:
        profiles=[profile(f'League engine {i+1}',wait=.12) for i in range(16)]
        source=s.create_tournament('League conditions — template',profiles,{'format':'round_robin','cycles':4,'max_plies':80,
            'time_control':{'kind':'nodes','nodes':100},'concurrency':2,'cpu_budget':2,'memory_budget_mb':1024},backup=False)
        event=s.event_call('create','Eight-division league',source['id'],{'kind':'league',
            'groups':[list(range(i,i+2)) for i in range(0,16,2)],'movement':[1]*7,'seasons':2,'initial_cycles':4,
            'execution_mode':'parallel','resources':{'cpu_budget':2,'concurrency':2,'memory_budget_mb':1024,'gpu_limits':{}},
            'championship':{'enabled':True,'games':4,'tiebreak_games':2,'controls':[]}})
        queued=s.create_tournament('Independent waiting comparison',profiles[:2],{'cycles':1},backup=False)
        s.queue_call('add',[queued['id']])
        s.queue_call('configure',s.queue_call('summary')['revision'],'parallel',{'cpu_budget':4,'concurrency':4,'memory_budget_mb':4096,'gpu_limits':{}})
    app=await create_app(folder,'manager-overview-test');app['stop']=asyncio.Event()
    db=app['db'];e=await db.call('event_call','detail',event['id'])
    await db.call('event_call','command',e['id'],'run',e['revision'])
    server=web.AppRunner(app);await server.setup();site=web.TCPSite(server,'127.0.0.1',0);await site.start()
    ready={'url':f'http://127.0.0.1:{site._server.sockets[0].getsockname()[1]}/?token=manager-overview-test',
           'event':event['id'],'queued':queued['id'],'folder':str(folder)}
    (ROOT/'test-output/manager-overview-ready.json').write_text(json.dumps(ready),encoding='utf-8');print(json.dumps(ready),flush=True)
    try:await app['stop'].wait()
    finally:await server.cleanup()

if __name__=='__main__':asyncio.run(main())
