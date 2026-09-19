import asyncio
from pathlib import Path
import sys
import time
from arena.experiments import parse_suite
from arena.runner import Database,Runner
from arena.store import Store

def profile():return {'name':'Fixture','path':sys.executable,'args':[str(Path(__file__).parent/'fault_engine.py')],'threads':1,'hash':1}

def test_epd_best_and_avoid_moves_parse(tmp_path):
    p=tmp_path/'suite.epd';p.write_text('rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - bm e4 d4; am a3; id "opening";')
    cases=parse_suite(p);assert cases[0]['bm']==['e2e4','d2d4'];assert cases[0]['am']==['a2a3'];assert cases[0]['id']=='opening'

def test_suite_and_benchmarks_are_durable(tmp_path):
    async def run():
        epd=tmp_path/'suite.epd';epd.write_text('rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - am a3; id "avoid";')
        db=await Database().open(tmp_path/'data');runner=Runner(db)
        try:
            await runner.start()
            for kind in ('suite','benchmark'):
                job=await db.call('experiment_create',kind,kind,[profile()],{'time_control':{'kind':'nodes','nodes':100},'thread_counts':[1,2],'repeats':2},str(epd))
                await db.call('experiment_state',job['id'],'running');deadline=time.monotonic()+20
                while time.monotonic()<deadline:
                    result=await db.call('experiment_get',job['id'])
                    if result['state']=='completed':break
                    if runner.error:raise AssertionError(runner.error)
                    await asyncio.sleep(.05)
                assert result['state']=='completed';assert result['completed']==(1 if kind=='suite' else 4)
                assert all(r['reported_nodes']==100 and r['measured_nps']>0 for r in result['results'])
                if kind=='suite':assert result['accuracy_pct'] in (0,100)
                else:assert {r['case']['threads'] for r in result['results']}=={1,2}
        finally:await runner.close()
    asyncio.run(run())

def test_interrupted_experiment_restarts_only_unfinished_case(tmp_path):
    s=Store(tmp_path);j=s.experiment_create('Recover benchmark','benchmark',[profile()],{'time_control':{'kind':'nodes'},'thread_counts':[1],'repeats':2})
    s.experiment_state(j['id'],'running');a=s.experiment_claim(j['id']);s.experiment_finish(a,{'official':True,'reason':'completed'});b=s.experiment_claim(j['id']);s.close()
    s=Store(tmp_path)
    try:
        recovered=s.experiment_get(j['id']);assert recovered['state']=='paused';assert recovered['cursor']==1;assert recovered['results'][-1]['reason']=='interrupted'
        s.experiment_state(j['id'],'running');replay=s.experiment_claim(j['id']);assert replay['number']==b['number'];assert replay['id']!=b['id']
    finally:s.close()
