import asyncio
import contextlib
from aiohttp.test_utils import TestClient,TestServer
from arena.server import create_app


def test_preview_and_audited_pairing_routes(tmp_path):
    async def run():
        app=await create_app(tmp_path,'fixture-token');runner=app['runner'];db=app['db']
        # Exercise HTTP routes with a deterministic completed round. No engines
        # launch in this API test; UCI execution is covered by other tests.
        runner.scheduler.cancel()
        with contextlib.suppress(asyncio.CancelledError):await runner.scheduler
        async with TestClient(TestServer(app),headers={'X-Arena-Token':'fixture-token'}) as client:
            response=await client.get('/assets/formats.js');assert response.status==200
            r=await client.post('/api/schedule-preview',json={'participants':10000,'settings':{'format':'round_robin','cycles':1}});v=await r.json()
            assert r.status==200 and v['scheduled_games']=='99990000' and not v['conditional']
            r=await client.post('/api/schedule-preview',json={'participants':2,'settings':{'format':'double_elimination','cycles':1,'knockout_tiebreak':'playoff','playoff_limit':2,'playoff_cycles':1}});v=await r.json()
            assert v=={'scheduled_games':'4','maximum_games':'18','conditional':True}
            r=await client.post('/api/schedule-preview',json={'participants':2,'settings':{'format':'ladder','ladder_distance':2}});assert r.status==400
            t=await db.call('create_tournament','Manual Swiss',[{'name':'One'},{'name':'Two'}],{'format':'swiss','cycles':1,'rounds':2})
            tid=t['id'];await db.call('set_state',tid,'running');await db.call('fill_queue',tid,8)
            while g:=await db.call('claim',tid):await db.call('finish',g['aid'],'1/2-1/2','fixture')
            await db.call('fill_queue',tid,8)
            r=await client.get(f'/api/tournaments/{tid}/pairings');v=await r.json()
            assert v['ready'] and v['state']=='paused' and v['next_kind']=='blocked' and len(v['matches'])==1
            assert [p['name'] for p in v['participants']]==['One','Two']
            body={'action':'manual_round','matches':[[1,0]],'byes':[],'signature':v['signature']}
            r=await client.post(f'/api/tournaments/{tid}/pairings',json=body);assert r.status==400 and 'rematches' in (await r.json())['error']
            r=await client.post(f'/api/tournaments/{tid}/pairings',json=body|{'allow_rematches':True,'signature':'stale'});assert r.status==400 and 'changed' in (await r.json())['error']
            r=await client.post(f'/api/tournaments/{tid}/pairings',json=body|{'allow_rematches':True});assert r.status==200 and (await r.json())['round']==1
            assert (await db.call('tournament',tid))['state']=='paused'
            r=await client.get(f'/api/tournaments/{tid}/pairings');v=await r.json();assert not v['ready'] and v['matches'][0]['a']==1
    asyncio.run(run())
