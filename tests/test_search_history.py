import asyncio
import json
import time

from aiohttp.test_utils import TestClient,TestServer
from arena.runner import Database,Runner
from arena.search_history import SearchHistory,white_info
from arena.server import create_app
from arena.store import DEFAULTS
from arena.uci import UciEngine
from test_core import profile


def test_best_move_history_keeps_last_stats_without_duplicate_entries_for_pv_refinements():
    h=SearchHistory()
    h.record({});assert h.revision==0
    h.record({'depth':1,'cp':10})
    assert h.current is None
    h.record({'pv':'e2e4 e7e5','depth':2,'cp':20,'nodes':100,'time':10})
    h.record({'nodes':200,'time':20})
    assert h.current['info']['nodes']==200
    h.record({'pv':'e2e4 c7c5','depth':3,'cp':25})
    assert h.changes==0 and not h.past
    h.record({'pv':'d2d4 d7d5','depth':4,'mate':3})
    h.record({'time':40,'nps':5000})
    h.record({'pv':'e2e4 e7e5','depth':5,'cp':30})
    snap=h.snapshot();assert snap['changes']==2
    assert [r['move'] for r in snap['history']]==['d2d4','e2e4']
    assert snap['history'][0]['info']['mate']==3 and snap['history'][0]['info']['time']==40
    assert 'cp' not in snap['history'][0]['info']
    assert 'nodes' not in h.current['info'] # Do not attribute an earlier PV's nodes to a new line.
    assert snap['history'][-1]['info']['pv']=='e2e4 c7c5'


def test_history_is_bounded_snapshots_are_stable_and_unknown_final_move_is_not_mislabelled():
    h=SearchHistory(limit=3)
    for i in range(10):h.record({'pv':'e2e4' if i%2 else 'd2d4','depth':i,'cp':i,'wdl':[300,500,200]})
    snap=h.snapshot();assert snap['omitted']==6 and len(snap['history'])==3
    previous=json.dumps(snap)
    h.record({'nodes':500});assert json.dumps(snap)==previous
    h.finish('g1f3',{'pv':'e2e4','cp':999})
    assert h.current['move']=='g1f3' and 'cp' not in h.current['info'] and h.selected=='g1f3'
    assert h.snapshot()['omitted']==7
    h.record({'pv':'nonsense','depth':100});assert h.current['move']=='g1f3'


def test_delta_parser_ignores_messages_and_multipv_and_preserves_score_perspective():
    engine=UciEngine(profile(),DEFAULTS)
    engine._info('info depth 10 score cp 23 lowerbound nodes 100 wdl 300 500 200 pv e2e4')
    h=SearchHistory();h.record(white_info(engine.last_update,False))
    assert h.current['info']['cp']==-23 and h.current['info']['score_bound']=='upperbound'
    assert h.current['info']['wdl']==[200,500,300] and engine.last_info['wdl']==[300,500,200]
    engine._info('info depth 11 pv d2d4')
    h.record(white_info(engine.last_update,False))
    assert 'cp' not in h.current['info'] and engine.last_info['cp']==23
    before=dict(engine.last_info)
    engine._info('info string depth 99 score cp 999 pv g1f3');assert engine.last_info==before
    engine._info('info multipv 2 depth 99 score cp 999 pv g1f3');assert engine.last_info==before
    engine._info('info score mate -2');h.record(white_info(engine.last_update,False))
    assert h.current['info']['mate']==2 and h.current['info']['score_bound']=='exact'
    engine.job.close()


def test_live_search_captures_changes_between_polls_and_retains_each_side(tmp_path):
    async def run():
        db=await Database().open(tmp_path);r=Runner(db)
        try:
            t=await db.call('create_tournament','PV changes',[profile('A','search_changes',.15),profile('B','search_changes',.15)],
                            {'cycles':1,'paired':False,'max_plies':4,'concurrency':1,'time_control':{'kind':'nodes','nodes':100}})
            await db.call('set_state',t['id'],'running');await r.start()
            seen=set();deadline=time.monotonic()+15
            while time.monotonic()<deadline:
                assert not r.error
                for aid,v in list(r.live.items()):
                    for side in ('white','black'):
                        d=r.search_detail(aid,side)
                        if d['available'] and d['complete']:
                            assert d['changes']==2 and len(d['history'])==2
                            assert d['current']['info']['cp']==(40 if side=='white' else -40)
                            assert d['current']['info']['wdl']==([300,500,200] if side=='white' else [200,500,300])
                            seen.add(side)
                    if v.get('ply')==2 and v.get('clock_active')=='white':
                        d=r.search_detail(aid,'white')
                        if d['revision']==0:assert d['changes']==0 and not d['history'];seen.add('reset')
                    status=r.status()['live'][0]
                    assert 'attempt' in status and 'history' not in status.get('searches',{}).get('white',{})
                if r.completed and not r.tasks:break
                await asyncio.sleep(.01)
            assert seen=={'white','black','reset'} and r.completed==1
            assert not r.search_histories
        finally:await r.close()
    asyncio.run(run())


def test_search_endpoint_is_separate_authenticated_and_scoped(tmp_path):
    async def run():
        app=await create_app(tmp_path,'fixture-token');r=app['runner']
        async with TestClient(TestServer(app)) as client:
            assert (await client.get('/api/search/test?side=white')).status==403
            h=SearchHistory();h.record({'pv':'e7e5 g1f3','cp':-20})
            r.search_histories['test']={'black':h};r.live['test']={'game':'g','searches':{'black':{'ply':4,'move_number':8,'complete':False}}}
            headers={'X-Arena-Token':'fixture-token'}
            response=await client.get('/api/search/test?side=black',headers=headers);data=await response.json()
            assert data['game']=='g' and data['move_number']==8 and data['current']['info']['cp']==-20
            assert (await (await client.get('/api/search/missing',headers=headers)).json())=={'available':False}
            assert (await client.get('/api/search/test?side=other',headers=headers)).status==400
            assert (await client.get('/assets/search.js')).status==200
            r.live.clear();r.search_histories.clear()
    asyncio.run(run())
