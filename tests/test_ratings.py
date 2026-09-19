import asyncio
import contextlib
import csv
import io
import math
import pytest
from aiohttp.test_utils import TestClient,TestServer
from arena.ratings import fit_pool,estimate,pool_report,SCALE
from arena.server import create_app
from arena.store import Store


def test_pool_transitive_ratings_and_anchor_invariance():
    observations=[(0,1,[10,0,5]),(0,2,[12,0,3]),(1,2,[10,0,5])]
    first=fit_pool(3,observations,0);second=fit_pool(3,observations,2)
    assert first['status']==second['status']=='ok'
    for slot,weight in enumerate((1,2,4)):
        a=estimate(first,slot,0,2000);b=estimate(second,slot,2,2000+SCALE*math.log(4))
        assert a['rating']==pytest.approx(2000+SCALE*math.log(weight),abs=1e-7)
        assert a['rating']==pytest.approx(b['rating'],abs=1e-7)


def test_pair_histogram_sandwich_matches_analytic_delta_method():
    bins=[8,11,26,15,10];count=sum(bins);p=sum(i*c/4 for i,c in enumerate(bins))/count
    fit=fit_pool(2,[(0,1,bins)],0);value=estimate(fit,1,0,2500)
    variance=sum(c*(i/4-p)**2 for i,c in enumerate(bins))/(count-1)
    se=SCALE*math.sqrt(variance/count)/(p*(1-p))
    assert value['delta']==pytest.approx(-SCALE*math.log(p/(1-p)),abs=1e-7)
    assert value['ci95']==pytest.approx([value['rating']-1.959963984540054*se,value['rating']+1.959963984540054*se],abs=1e-7)
    assert value['los']<50


def test_pool_disconnection_separation_and_degenerate_uncertainty():
    separated=fit_pool(4,[(0,1,[0,0,10]),(2,3,[4,2,4])],0)
    assert estimate(separated,1,0,0)['status']=='no_finite_fit'
    assert estimate(separated,2,0,0)['status']=='disconnected'
    cyclic=fit_pool(3,[(0,1,[0,0,10]),(1,2,[0,0,10]),(2,0,[0,0,10])],0)
    assert cyclic['status']=='ok' and estimate(cyclic,2,0,0)['rating']==0
    draws=fit_pool(2,[(0,1,[0,0,10,0,0])],0)
    assert estimate(draws,1,0,0)['status']=='uncertainty_unavailable'
    assert estimate(draws,1,0,0)['ci95'] is None


def test_ten_thousand_ratings_use_sparse_comparisons():
    fit=fit_pool(10000,[(0,i,[2,0,6,0,2]) for i in range(1,10000)],0)
    assert fit['status']=='ok' and len(fit['hessian'])==9999 and len(fit['members'])==10000
    value=estimate(fit,9999,0,2400)
    assert value['rating']==2400 and value['status']=='estimated' and value['ci95'][0]<2400<value['ci95'][1]


def test_pool_official_replacement_pair_accounting_and_restart(tmp_path):
    s=Store(tmp_path);t=s.create_tournament('Pool',[{'name':'Alpha'},{'name':'Beta'}],{'cycles':2});tid=t['id']
    s.set_state(tid,'running');s.fill_queue(tid,4);games=[]
    for result in ('1-0','0-1','1/2-1/2'):
        g=s.claim(tid);s.finish(g['aid'],result,'fixture');games.append(g)
    partial=pool_report(s.path,tid);assert partial['samples']==1 and partial['status']=='no_finite_fit'
    g=s.claim(tid);s.finish(g['aid'],'1-0','fixture');games.append(g)
    s.save_rating_anchor(tid,1,2600);original=pool_report(s.path,tid)
    assert original['samples']==2 and original['anchor']['rating']==2600 and original['items'][0]['rating']>2600
    s.set_state(tid,'paused');s.requeue(tid,[games[0]['id']],mode='diagnostic');s.set_state(tid,'running')
    g=s.claim(tid);s.finish(g['aid'],'0-1','fixture')
    diagnostic=pool_report(s.path,tid);assert diagnostic['revision']==original['revision']
    s.set_state(tid,'paused');s.requeue(tid,[games[0]['id']],mode='replacement');s.set_state(tid,'running')
    g=s.claim(tid);s.finish(g['aid'],'0-1','fixture')
    replaced=pool_report(s.path,tid)
    assert replaced['samples']==2 and replaced['items'][0]['rating']<2600 and replaced['revision']>original['revision']
    assert len(s.game_detail(g['id'])['attempts'])==3
    assert len(list(csv.DictReader(io.StringIO(pool_report(s.path,tid,export='csv')))))==2
    s.close();s=Store(tmp_path);reopened=pool_report(s.path,tid)
    assert reopened['items']==replaced['items'] and reopened['anchor']==replaced['anchor'];s.close()


def test_pool_paging_anchor_validation_and_background_api(tmp_path):
    async def run():
        app=await create_app(tmp_path,'pool');runner=app['runner'];db=app['db'];runner.scheduler.cancel()
        with contextlib.suppress(asyncio.CancelledError):await runner.scheduler
        async with TestClient(TestServer(app),headers={'X-Arena-Token':'pool'}) as client:
            t=await db.call('create_tournament','Pool API',[{'name':f'Engine {i:03}'} for i in range(101)],{'format':'round_robin','cycles':1});tid=t['id']
            for payload in ({'slot':101,'rating':0},{'slot':True,'rating':0},{'slot':0,'rating':'3000'},{'slot':0,'rating':True}):
                r=await client.post(f'/api/tournaments/{tid}/ratings',json=payload);assert r.status==400
            r=await client.post(f'/api/tournaments/{tid}/ratings',json={'slot':100,'rating':3000});assert r.status==200
            r=await client.get(f'/api/tournaments/{tid}/ratings?offset=100');result=await r.json()
            assert r.status==200 and result['total']==101 and len(result['items'])==1 and result['items'][0]['rating']==3000
            r=await client.get(f'/api/tournaments/{tid}/ratings?q=Engine%20050');result=await r.json();assert result['total']==1 and result['items'][0]['slot']==50
            r=await client.get(f'/api/tournaments/{tid}/ratings?export=json');result=await r.json();assert len(result['items'])==101
    asyncio.run(run())
