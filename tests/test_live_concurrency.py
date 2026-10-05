import asyncio
import contextlib
import json
import os
import subprocess
import sys
import time

import pytest
from aiohttp.test_utils import TestClient,TestServer
from arena.resources import usage
from arena.runner import Database,Runner
from arena.server import create_app
from arena.store import Store
from arena.tournament_report import render
from test_core import profile


def test_saved_limit_audit_and_report_survive_abrupt_exit(tmp_path):
    script='''from arena.store import Store
import os,sys,json
s=Store(sys.argv[1]);t=s.create_tournament('Changing load',[{'name':'A'},{'name':'B'}],{'concurrency':1})
s.set_concurrency(t['id'],4);s.set_concurrency(t['id'],4);s.set_concurrency(t['id'],2)
print(t['id'],flush=True);os._exit(0)
'''
    tid=subprocess.check_output([sys.executable,'-c',script,str(tmp_path)],text=True).strip()
    with contextlib.closing(Store(tmp_path)) as s:
        assert s.tournament(tid)['settings']['concurrency']==2
        changes=[json.loads(r['body']) for r in s.rows("SELECT body FROM audit WHERE action='concurrency_changed' ORDER BY id")]
        assert [(v['before'],v['after']) for v in changes]==[(1,4),(4,2)]
        html=render(s.path,tid,technical=False)
        assert 'Concurrency changes' in html and 'Current simultaneous-game limit' in html
        assert 'Performance samples can span different loads' in html


def test_live_limit_increase_decrease_preserves_attempts_and_gpu_budget(tmp_path):
    async def run():
        db=await Database().open(tmp_path);r=Runner(db)
        try:
            field=[profile(str(i),wait=.07)|{'gpu_group':'gpu0' if i==0 else '', 'extra_memory_mb':0} for i in range(4)]
            settings={'format':'round_robin','cycles':2,'concurrency':1,'cpu_budget':4,'memory_budget_mb':1000,'gpu_limits':{'gpu0':1},'max_plies':12,'time_control':{'kind':'nodes','nodes':100}}
            t=await db.call('create_tournament','Live adjustment',field,settings);tid=t['id']
            await db.call('set_state',tid,'running');await r.start()
            async def until(check,timeout=20):
                deadline=time.monotonic()+timeout
                while time.monotonic()<deadline:
                    assert not r.error
                    used=usage(r.live.values());assert used['threads']<=4 and used['gpu'].get('gpu0',0)<=1
                    if check():return
                    await asyncio.sleep(.01)
                raise AssertionError('Live concurrency did not settle')
            await until(lambda:len(r.live)==1)
            original=next(iter(r.live));await r.set_concurrency(tid,4)
            await until(lambda:len(r.live)==4)
            result=await r.set_concurrency(tid,1);active=set(r.live)
            assert result['active']==4 and len(active)==4
            deadline=time.monotonic()+20
            while len(r.live)>1 and time.monotonic()<deadline:
                assert set(r.live)<=active  # no replacement starts above the lower limit
                await asyncio.sleep(.01)
            assert len(r.live)<=1
            rows=await db.call('rows','SELECT id,reason FROM attempts WHERE id IN ('+','.join('?' for _ in active)+')',tuple(active))
            assert all(row['reason'] in (None,'max_plies_adjudication') for row in rows)
            assert original in {v['id'] for v in await db.call('rows','SELECT id FROM attempts')}
            await r.set_concurrency(tid,8)  # game limit never overrides CPU or GPU admission
            deadline=time.monotonic()+30
            while time.monotonic()<deadline:
                used=usage(r.live.values());assert len(r.live)<=4 and used['gpu'].get('gpu0',0)<=1
                snap=await db.call('snapshot',tid)
                if snap['state']=='completed':break
                await asyncio.sleep(.02)
            assert snap['state']=='completed' and snap['official_games']==24 and snap['complete_pairs']==12
            assert {a['reason'] for a in await db.call('rows','SELECT reason FROM attempts')}=={'max_plies_adjudication'}
            assert (await db.call('tournament',tid))['settings']['gpu_limits']=={'gpu0':1}
        finally:await r.close()
    asyncio.run(run())


def test_api_validation_and_paused_limit_does_not_start_games(tmp_path):
    async def run():
        app=await create_app(tmp_path,'limit');db=app['db'];r=app['runner']
        async with TestClient(TestServer(app),headers={'X-Arena-Token':'limit'}) as client:
            t=await db.call('create_tournament','Paused',[profile('A'),profile('B')],{'concurrency':1});url=f"/api/tournaments/{t['id']}/concurrency"
            for value in [0,-1,True,1.5,'2',None]:
                response=await client.post(url,json={'concurrency':value});assert response.status==400
            response=await client.post(url,json={'concurrency':3});assert response.status==200
            await asyncio.sleep(.2);assert not r.live
            assert (await db.call('tournament',t['id']))['settings']['concurrency']==3
            await db.call('execute',"UPDATE tournaments SET state='completed' WHERE id=?",(t['id'],))
            assert (await client.post(url,json={'concurrency':2})).status==400
    asyncio.run(run())
