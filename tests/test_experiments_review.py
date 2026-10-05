import asyncio
import contextlib
import json
import sqlite3
from pathlib import Path
import sys

import pytest
from aiohttp.test_utils import TestClient,TestServer
from arena.experiments import parse_suite,execute
from arena.runner import Database
from arena.server import create_app
from arena.store import Store


def profile(mode='normal'):
    return {'name':'Review engine','path':sys.executable,'args':[str(Path(__file__).parent/'fault_engine.py'),'--mode',mode],'threads':1,'hash':1}


def settings(**changes):return {'time_control':{'kind':'nodes','nodes':100},'thread_counts':[1,2],'repeats':2}|changes


def test_atomic_attempt_completion_and_paged_totals(tmp_path):
    with contextlib.closing(Store(tmp_path)) as s:
        job=s.experiment_create('Review','benchmark',[profile()],settings(repeats=30));eid=job['id']
        s.experiment_state(eid,'running')
        first=None
        for n in range(60):
            case=s.experiment_claim(eid);assert case['number']==n
            assert s.experiment_claim(eid) is None
            if first is None:first=case
            assert s.experiment_finish(case,{'official':True,'reason':'completed','effective_threads':case['case']['threads'],'measured_nps':100+n,'elapsed_seconds':1,'log':['x'*4096]})
            assert not s.experiment_finish(case,{'official':False,'reason':'interrupted'})
        s.experiment_state(eid,'running');job=s.experiment_get(eid,0,50)
        assert job['state']=='completed' and job['completed']==60 and job['failures']==0
        assert len(job['results'])==50 and 'log' not in job['results'][0] and 'cases' not in job
        assert len(s.experiment_get(eid,50,50)['results'])==10
        assert len(s.experiment_get(eid)['results'])==60 and s.experiment_get(eid)['results'][0]['log']
        assert [r['samples'] for r in job['benchmark_summary']]==[30,30]
        assert job['benchmark_summary'][0]['mean_nps']==114.5
        with pytest.raises(ValueError):s.experiment_finish(first|{'eid':'other'},{'official':True})
        with pytest.raises(ValueError):s.experiment_state('missing','running')


def test_huge_benchmark_schedule_stays_compact_and_legacy_cases_work(tmp_path):
    with contextlib.closing(Store(tmp_path)) as s:
        job=s.experiment_create('Large','benchmark',[profile()],settings(repeats=1000000))
        assert job['total']==2000000 and len(json.dumps(job['cases']))<250
        s.execute('UPDATE experiments SET cursor=1999999,state=? WHERE id=?',('running',job['id']))
        case=s.experiment_claim(job['id']);assert case['case']['threads']==2 and case['case']['repeat']==1000000
        s.experiment_finish(case,{'official':True,'reason':'completed'})
        legacy=s.experiment_create('Legacy','benchmark',[profile()],settings(thread_counts=[1],repeats=1))
        s.execute('UPDATE experiments SET cases=? WHERE id=?',(json.dumps([case['case']]),legacy['id']))
        s.experiment_state(legacy['id'],'running');assert s.experiment_claim(legacy['id'])['case']==case['case']


@pytest.mark.parametrize('changes',[{'thread_counts':[True]},{'thread_counts':[1,1]},{'repeats':True},{'repeats':0},{'hang_timeout':float('nan')},{'startup_timeout':0},{'tolerance':float('inf')},{'fen':'7k/5Q2/6K1/8/8/8/8/8 b - - 0 1'}])
def test_experiment_settings_reject_invalid_cases(tmp_path,changes):
    with contextlib.closing(Store(tmp_path)) as s:
        with pytest.raises(ValueError):s.experiment_create('Bad','benchmark',[profile()],settings(**changes))


def test_epd_error_context_and_contradictory_answers(tmp_path):
    p=tmp_path/'cases.epd'
    for source in ('not a position','rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - bm e4; am e4;'):
        p.write_text('# source\n'+source)
        with pytest.raises(ValueError,match='line 2'):parse_suite(p)


def test_suite_final_correct_sequence_failures_and_unknown_threads(tmp_path):
    async def run():
        db=await Database().open(tmp_path/'data')
        try:
            epd=tmp_path/'suite.epd';epd.write_text('rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - bm Nh3;')
            j=await db.call('experiment_create','Stable','suite',[profile('search_changes'),profile('crash')],settings(),str(epd))
            await db.call('experiment_state',j['id'],'running')
            for _ in range(2):await execute(db,await db.call('experiment_claim',j['id']))
            got=await db.call('experiment_get',j['id']);a,b=got['results']
            assert got['state']=='completed' and got['accuracy_pct']==50 and got['failures']==1
            assert a['correct'] and a['first_correct_pv_seconds']<a['time_to_solve_seconds']<=a['elapsed_seconds']
            assert b['reason']=='crash' and not b['correct']
            j=await db.call('experiment_create','Unsupported','benchmark',[profile('no_threads')],settings(thread_counts=[2],repeats=1))
            await db.call('experiment_state',j['id'],'running');await execute(db,await db.call('experiment_claim',j['id']))
            got=await db.call('experiment_get',j['id']);assert got['failures']==1 and got['benchmark_summary']==[]
            assert got['results'][0]['reason']=='protocol_error' and got['results'][0]['effective_threads'] is None
        finally:await db.close()
    asyncio.run(run())


def test_experiment_api_paging_export_and_invalid_state(tmp_path):
    async def run():
        app=await create_app(tmp_path,'review');runner=app['runner'];db=app['db'];runner.scheduler.cancel()
        with contextlib.suppress(asyncio.CancelledError):await runner.scheduler
        async with TestClient(TestServer(app),headers={'X-Arena-Token':'review'}) as client:
            j=await db.call('experiment_create','Pages','benchmark',[profile()],settings(thread_counts=[1],repeats=52))
            await db.call('experiment_state',j['id'],'running')
            for _ in range(52):
                c=await db.call('experiment_claim',j['id']);await db.call('experiment_finish',c,{'official':True,'reason':'completed','log':['kept']})
            for query,count in (('',50),('?offset=50',2),('?all=1',52)):
                response=await client.get('/api/experiments/'+j['id']+query);body=await response.json()
                assert response.status==200 and body['completed']==52 and len(body['results'])==count
                assert ('log' in body['results'][0])==(query=='?all=1')
            assert (await client.get('/api/experiments/'+j['id']+'?offset=-1')).status==400
            assert (await client.post('/api/experiments/missing/action',json={'action':'start'})).status==400
    asyncio.run(run())


def test_legacy_experiment_results_migrate_without_losing_attempts(tmp_path):
    s=Store(tmp_path);j=s.experiment_create('Old saved benchmark','benchmark',[profile()],settings())
    s.experiment_state(j['id'],'running');c=s.experiment_claim(j['id']);s.experiment_finish(c,{'official':True,'reason':'completed','measured_nps':500,'elapsed_seconds':.2,'log':['original evidence']});s.close()
    # Reconstruct the previous on-disk schema, retaining its original body.
    with sqlite3.connect(tmp_path/'arena.sqlite3') as con:
        con.execute('DROP INDEX experiment_summary');con.execute('ALTER TABLE experiment_attempts DROP COLUMN summary')
    with contextlib.closing(Store(tmp_path)) as s:
        got=s.experiment_get(j['id']);assert got['completed']==1 and got['cursor']==1 and got['state']=='paused'
        assert got['results'][0]['attempt_id']==c['id'] and got['results'][0]['log']==['original evidence']
        assert got['benchmark_summary'][0]['mean_nps']==500
        assert got['benchmark_summary'][0]['threads'] is None  # Do not invent old runtime evidence.
        s.experiment_state(j['id'],'running');assert s.experiment_claim(j['id'])['number']==1
