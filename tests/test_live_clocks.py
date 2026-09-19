import asyncio
from pathlib import Path
import sys
import threading
from arena.runner import Database,Runner


def test_live_clocks_freeze_during_durable_move_save_and_retain_handicap(tmp_path):
    async def run():
        db=await Database().open(tmp_path);runner=Runner(db)
        fixture=str(Path(__file__).with_name('fault_engine.py').resolve())
        profiles=[{'name':side,'path':sys.executable,'args':[fixture,'--wait','.15'],'threads':1,'hash':1,
                   'time_control':{'kind':'fischer','seconds':seconds,'increment':1}}
                  for side,seconds in [('A',10),('B',20)]]
        t=await db.call('create_tournament','Clock save',[*profiles],{'cycles':1,'paired':False,'max_plies':2,'concurrency':1})
        await db.call('set_state',t['id'],'running')
        entered=threading.Event();release=threading.Event();original=db.store.move_batch
        def delayed(batch):
            entered.set();assert release.wait(10);return original(batch)
        db.store.move_batch=delayed
        try:
            await runner.start();assert await asyncio.to_thread(entered.wait,10)
            a=runner.status()['live'][0]
            assert a['status']=='Saving move' and a['clock_active'] is None and a['search_elapsed']==0
            assert 10<a['clocks']['white']['remaining']<11
            assert a['clocks']['black']['remaining']==20
            await asyncio.sleep(.1)
            b=runner.status()['live'][0];assert a['clocks']==b['clocks'] and b['search_elapsed']==0
            release.set()
            for _ in range(150):
                await asyncio.sleep(.05)
                if runner.completed:break
            assert runner.completed==1
            page=await db.call('games',t['id']);clocks=page['items'][0]['clocks']
            assert clocks['white']['elapsed']>=.1 and clocks['black']['elapsed']>=.1
            assert 20<clocks['black']['remaining']<21
        finally:release.set();await runner.close()
    asyncio.run(run())


def test_search_telemetry_retains_each_engine_and_clears_new_search(tmp_path):
    async def run():
        db=await Database().open(tmp_path);runner=Runner(db)
        fixture=str(Path(__file__).with_name('fault_engine.py').resolve())
        profiles=[{'name':side,'path':sys.executable,'args':[fixture,'--wait','.3'],'threads':1,'hash':1}
                  for side in ('A','B')]
        t=await db.call('create_tournament','Search provenance',profiles,{'cycles':1,'paired':False,'max_plies':4,'concurrency':1,'time_control':{'kind':'nodes','nodes':100}})
        await db.call('set_state',t['id'],'running')
        observed=set()
        try:
            await runner.start()
            for _ in range(400):
                for view in runner.status()['live']:
                    if view.get('clock_active')=='black' and view['ply']==1:
                        assert view['info']=={} and view['info_side']=='black'
                        assert view['searches']['white']['info']['cp']==14
                        assert view['searches']['white']['complete']
                        assert view['searches']['white']['ply']==1
                        assert view['searches']['black']['info']=={}
                        assert view['searches']['black']['move_number']==1
                        observed.add('black waiting')
                    if view.get('clock_active')=='white' and view['ply']==2:
                        assert view['info']=={} and view['info_side']=='white'
                        assert view['searches']['black']['info']['cp']==-14
                        assert view['searches']['black']['info']['wdl']==[270,410,320]
                        assert view['searches']['black']['complete']
                        assert view['searches']['white']['move_number']==2
                        assert view['searches']['white']['info']=={}
                        observed.add('white waiting')
                if runner.completed:break
                await asyncio.sleep(.01)
            assert observed=={'black waiting','white waiting'}
            assert runner.completed==1
        finally:await runner.close()
    asyncio.run(run())
