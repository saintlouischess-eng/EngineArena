"""Committed setup acknowledgement is independent of slow recovery copies."""
import asyncio
import sqlite3
from aiohttp.test_utils import TestClient, TestServer
from arena.server import create_app
from arena.store import SavingError
from test_core import profile


def test_setup_acknowledgement_and_coalesced_backups(tmp_path):
    async def run():
        app=await create_app(tmp_path,'save');db=app['db'];runner=app['runner']
        profiles=[(await db.call('save_profile',profile(n)))['id'] for n in ('A','B')]
        started=asyncio.Event();release=asyncio.Event();second=asyncio.Event();original=db.call;copies=0
        async def slow_copy(method,*args,**kwargs):
            nonlocal copies
            result=await original(method,*args,**kwargs)
            if method=='backup':
                copies+=1
                if copies==1:started.set();await release.wait()
                else:second.set()
            return result
        db.call=slow_copy
        async with TestClient(TestServer(app),headers={'X-Arena-Token':'save'}) as client:
            try:
                async def create(name):
                    response=await asyncio.wait_for(client.post('/api/tournaments',json={'name':name,'profiles':profiles,'settings':{}}),3)
                    assert response.status==200,await response.text()
                    return await response.json()
                first=await create('First');await asyncio.wait_for(started.wait(),3)
                # Recovery copy is blocked; further saves and edits still commit once.
                two=await create('Second');three=await create('Third')
                response=await asyncio.wait_for(client.post(f"/api/tournaments/{first['id']}/setup",json={'name':'Edited','settings':{},'setup_revision':0}),3)
                assert response.status==200
                assert not runner.lifecycle_lock.locked() and copies==1
                assert len(await original('rows','SELECT id FROM tournaments'))==3
                assert runner.backup_requested
                release.set();await asyncio.wait_for(second.wait(),4)
                await asyncio.sleep(.25);assert copies==2
                with sqlite3.connect(db.store.backup_file) as conn:
                    assert sorted(r[0] for r in conn.execute('SELECT name FROM tournaments'))==['Edited','Second','Third']
            finally:release.set()
    asyncio.run(run())


def test_backup_failure_does_not_report_committed_setup_as_failed(tmp_path):
    async def run():
        app=await create_app(tmp_path,'save');db=app['db'];runner=app['runner']
        profiles=[(await db.call('save_profile',profile(n)))['id'] for n in ('A','B')]
        original=db.store._backup_snapshot;failed=asyncio.Event()
        def fail():
            db.store.failure='Backup saving failed: simulated disk failure. Scheduling stopped.'
            db.store._backup_progress(phase='error',error='simulated disk failure')
            raise SavingError(db.store.failure)
        db.store._backup_snapshot=fail
        async with TestClient(TestServer(app),headers={'X-Arena-Token':'save'}) as client:
            try:
                response=await client.post('/api/tournaments',json={'name':'Committed','profiles':profiles,'settings':{}})
                assert response.status==200
                result=await response.json()
                for _ in range(50):
                    status=await (await client.get('/api/status')).json()
                    if status['error']:break
                    await asyncio.sleep(.05)
                assert 'simulated disk failure' in status['error'] and status['backup']['phase']=='error'
                assert (await db.call('tournament',result['id']))['state']=='paused'
                assert len(await db.call('rows','SELECT id FROM tournaments'))==1
            finally:db.store._backup_snapshot=original
    asyncio.run(run())


def test_shutdown_copies_save_that_has_not_reached_scheduler(tmp_path):
    async def run():
        app=await create_app(tmp_path,'save');db=app['db'];runner=app['runner']
        runner.scheduler.cancel();await asyncio.gather(runner.scheduler,return_exceptions=True)
        profiles=[(await db.call('save_profile',profile(n)))['id'] for n in ('A','B')]
        async with TestClient(TestServer(app),headers={'X-Arena-Token':'save'}) as client:
            response=await client.post('/api/tournaments',json={'name':'Last save','profiles':profiles,'settings':{}})
            assert response.status==200 and runner.backup_requested
        with sqlite3.connect(db.store.backup_file) as conn:
            assert conn.execute('SELECT name FROM tournaments').fetchone()[0]=='Last save'
    asyncio.run(run())
