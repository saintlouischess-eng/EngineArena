import asyncio
import contextlib
import csv
import io
import math
import pytest
from aiohttp.test_utils import TestClient,TestServer
from arena.ratings import fit_pool,estimate,pool_report,SCALE,STATUS_LABELS
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


@pytest.mark.parametrize('confidence',[80,95,99.9])
def test_separated_newcomers_preserve_core_ratings_and_uncertainty(confidence):
    core=[(0,1,[8,11,26,15,10]),(1,2,[10,3,7]),(2,0,[9,4,8])]
    baseline=fit_pool(3,core,0)
    # All-loss and all-win additions, a downstream group with finite internal
    # differences but no finite offset to the reference, and a disconnected pair.
    expanded=fit_pool(8,core+[(0,3,[0,0,10000]),(4,1,[0,0,5000]),
                            (3,5,[10,20,10]),(6,7,[4,2,4])],0)
    assert expanded['status']=='ok' and expanded['members']==[0,1,2]
    assert expanded['separated_members']==[3,4,5]
    assert expanded['fit_samples']==baseline['samples']
    assert expanded['samples']==baseline['samples']+15040
    for slot in (0,1,2):
        a=estimate(baseline,slot,0,3628,confidence)
        b=estimate(expanded,slot,0,3628,confidence)
        for key in ('rating','delta','ci','ci95','los'):
            assert b[key]==pytest.approx(a[key]) if a[key] is not None else b[key] is None
    for slot in (3,4,5):
        row=estimate(expanded,slot,0,3628,confidence)
        assert row['status']=='no_finite_fit' and row['rating'] is row['ci'] is row['los'] is None
    assert estimate(expanded,6,0,3628)['status']=='disconnected'


def test_separation_resolves_with_return_score_and_anchor_is_not_replaced():
    base=[(0,1,[5,10,8]),(1,2,[0,0,7])]
    limited=fit_pool(3,base,2)
    assert limited['status']=='no_finite_fit' and limited['members']==[2]
    assert estimate(limited,0,2,2500)['rating'] is None
    joined=fit_pool(3,base+[(1,2,[0,1,0])],2)
    assert joined['status']=='ok' and joined['members']==[0,1,2]
    assert all(estimate(joined,n,2,2500)['rating'] is not None for n in range(3))


def test_ten_thousand_separated_entries_do_not_block_finite_sparse_fit():
    fit=fit_pool(10000,[(0,1,[2,6,2])]+[(0,i,[0,0,1]) for i in range(2,10000)],0)
    assert fit['status']=='ok' and fit['members']==[0,1] and len(fit['hessian'])==1
    assert fit['fit_samples']==10 and len(fit['separated_members'])==9998
    assert estimate(fit,1,0,2400)['rating']==2400


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
            r=await client.get(f'/api/tournaments/{tid}/ratings?sort=name&direction=desc&offset=100');result=await r.json()
            assert result['items'][0]['slot']==0 and result['sort']=='name' and result['direction']=='desc'
            r=await client.get(f'/api/tournaments/{tid}/ratings?sort=invalid');assert r.status==400
    asyncio.run(run())


def test_global_rating_sort_pagination_nulls_ties_filter_and_export(tmp_path):
    s=Store(tmp_path)
    try:
        t=s.create_tournament('Sorted pool',[{'name':f'Engine {106-i:03}'} for i in range(107)],{'format':'round_robin','cycles':1,'paired':False});tid=t['id']
        with s.tx():
            for i in range(1,106):
                s.db.execute('INSERT INTO aggregates(tid,a,b,w,d,l) VALUES(?,?,?,?,?,?)',(tid,0,i,1+i%7,3,7))
        all_rows=pool_report(s.path,tid,export='json')['items']
        for key in ('slot','name','rating','delta','ci','los','samples','status'):
            def value(r):
                if key=='name':return r['name'].casefold()
                if key=='ci':return r['ci'][1]-r['ci'][0] if r['ci'] else None
                if key=='status':return STATUS_LABELS[r['status']].casefold()
                return r[key]
            valid=[r for r in all_rows if value(r) is not None];missing=[r for r in all_rows if value(r) is None]
            for direction in ('asc','desc'):
                expected=sorted(valid,key=value,reverse=direction=='desc')+missing
                pages=[pool_report(s.path,tid,offset=o,limit=50,sort=key,direction=direction)['items'] for o in (0,50,100)]
                assert [r['slot'] for page in pages for r in page]==[r['slot'] for r in expected]
        filtered=pool_report(s.path,tid,search='Engine 00',sort='name',direction='desc')
        assert filtered['total']==10 and [r['name'] for r in filtered['items']]==sorted([r['name'] for r in filtered['items']],reverse=True)
        exported=list(csv.DictReader(io.StringIO(pool_report(s.path,tid,export='csv',sort='rating',direction='desc'))))
        assert len(exported)==107 and int(exported[-1]['slot'])==106
        for key,direction in [('unknown','asc'),('rating','sideways')]:
            with pytest.raises(ValueError):pool_report(s.path,tid,sort=key,direction=direction)
    finally:s.close()
