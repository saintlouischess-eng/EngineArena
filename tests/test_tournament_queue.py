import asyncio
import contextlib
import json
import subprocess
import sys
import time
import pytest
from aiohttp.test_utils import TestClient,TestServer
from arena.store import Store
from arena.runner import Database,Runner
from arena.server import create_app
from test_core import profile,read_pgn


@pytest.fixture
def store(tmp_path):
    with contextlib.closing(Store(tmp_path)) as s:yield s


def draft(s,name='Draft',**settings):
    return s.create_tournament(name,[profile(name+' A'),profile(name+' B')],
        {'concurrency':2,'cycles':2,'max_plies':4,'time_control':{'kind':'nodes','nodes':77},**settings},backup=False)['id']


def command(s,action,**kw):return s.queue_call('command',action,s.queue_call('summary')['revision'],**kw)


def test_queue_order_dedup_edit_and_remove_without_deleting(store):
    ids=[draft(store,str(i)) for i in range(3)]
    assert store.queue_call('add',ids+ids)=={'added':3}
    assert store.queue_call('add',ids)=={'added':0}
    assert all(store.tournament(i)['can_edit'] for i in ids)
    store.edit_tournament(ids[1],'Updated waiting test',{'cycles':7},0,backup=False)
    command(store,'up',tid=ids[2]);command(store,'up',tid=ids[2])
    rows=store.queue_call('page')['items'];assert [r['tid'] for r in rows]==[ids[2],ids[0],ids[1]]
    assert rows[2]['name']=='Updated waiting test' and rows[2]['total']==14
    command(store,'remove',tid=ids[0])
    assert store.tournament(ids[0])['total']==4 and store.tournament(ids[0])['queue'] is None
    assert not store.rows('SELECT * FROM games')


def test_add_is_atomic_and_revision_guards_actions(store):
    a=draft(store);b=draft(store);store.set_state(b,'running')
    with pytest.raises(ValueError):store.queue_call('add',[a,b])
    assert store.queue_call('summary')['total']==0
    store.set_state(b,'paused');store.queue_call('add',all_ready=True)
    assert [i['tid'] for i in store.queue_call('page')['items']]==[a]
    old=store.queue_call('summary')['revision'];command(store,'remove',tid=a)
    with pytest.raises(ValueError,match='changed'):store.queue_call('command','run',old)


def test_removing_last_scheduled_entry_cancels_timed_start(store):
    tid=draft(store);store.queue_call('add',[tid]);command(store,'run',not_before=time.time()+3600)
    command(store,'remove',tid=tid)
    q=store.queue_call('summary');assert q['mode']=='completed' and q['not_before']==0 and q['remaining']==0
    assert store.tournament(tid)['can_edit']


def test_deleting_last_scheduled_tournament_cancels_empty_queue(store):
    from arena.deletion import purge
    tid=draft(store);store.queue_call('add',[tid]);command(store,'run',not_before=time.time()+3600)
    with store.tx():purge(store.db,[tid])
    store.queue_call('tick')
    q=store.queue_call('summary');assert q['mode']=='completed' and q['remaining']==0 and q['not_before']==0


def test_timed_start_and_manual_work_waiting(store,monkeypatch):
    import arena.tournament_queue as q
    a=draft(store);manual=draft(store,'Manual');store.queue_call('add',[a])
    monkeypatch.setattr(q.time,'time',lambda:100)
    command(store,'run',not_before=200);store.queue_call('tick')
    assert store.tournament(a)['can_edit']
    monkeypatch.setattr(q.time,'time',lambda:200);store.set_state(manual,'running')
    store.queue_call('tick');assert store.tournament(a)['state']=='paused'
    store.set_state(manual,'paused');store.queue_call('tick',(),True)
    assert store.tournament(a)['state']=='paused'
    store.queue_call('tick');assert store.tournament(a)['state']=='running' and not store.tournament(a)['can_edit']
    assert store.queue_call('summary')['active_tid']==a
    with pytest.raises(ValueError,match='already running'):command(store,'run')
    with pytest.raises(ValueError):store.queue_call('manual_action',a,'start')


def test_finish_current_and_pause_do_not_start_next(store):
    a,b=[draft(store) for _ in range(2)];store.queue_call('add',[a,b]);command(store,'run');store.queue_call('tick')
    command(store,'finish_current')
    assert store.tournament(a)['state']=='running'
    store.execute("UPDATE tournaments SET state='completed' WHERE id=?",(a,))
    store.queue_call('tick',[a]);assert store.queue_call('summary')['completed']==0
    store.queue_call('tick');q=store.queue_call('summary');assert q['mode']=='paused' and q['completed']==1
    assert store.tournament(b)['can_edit']
    command(store,'run');store.queue_call('tick');assert store.tournament(b)['state']=='running'
    store.queue_call('manual_action',b,'pause');store.set_state(b,'paused');store.queue_call('tick')
    assert store.queue_call('summary')['mode']=='paused'
    command(store,'run');store.queue_call('tick');assert store.queue_call('summary')['active_tid']==b


@pytest.mark.parametrize('kind',['dependency','resource','worker'])
def test_blocked_tournament_holds_remaining_queue(store,kind):
    a,b=[draft(store) for _ in range(2)];store.queue_call('add',[a,b]);command(store,'run');store.queue_call('tick')
    if kind=='worker':store.queue_call('hold','Saving failed')
    else:
        store.execute("UPDATE tournaments SET state='paused',dependency=?,note=? WHERE id=?",('Pairing repair' if kind=='dependency' else '',kind,a))
    store.queue_call('tick')
    assert store.queue_call('summary')['mode']=='paused' and store.tournament(b)['can_edit']


def test_sprt_boundary_advances_only_after_drain(store):
    a=draft(store,format='sprt');b=draft(store,'Next');store.queue_call('add',[a,b]);command(store,'run');store.queue_call('tick')
    store.execute('INSERT INTO sequential_state VALUES(?,?)',(a,json.dumps({'frozen':True,'decision':'H1'})))
    store.set_state(a,'draining');store.queue_call('tick');assert store.tournament(b)['state']=='paused'
    store.set_state(a,'paused');store.queue_call('tick')
    assert store.queue_call('summary')['completed']==1 and store.tournament(b)['state']=='running'


def test_deletion_removes_queue_references_from_storage(store):
    from arena.deletion import purge
    a,b=[draft(store) for _ in range(2)];store.queue_call('add',[a,b]);command(store,'run');store.queue_call('tick')
    with store.tx():purge(store.db,[a])
    q=store.queue_call('page');assert q['active_tid'] is None and q['mode']=='paused'
    assert [i['tid'] for i in q['items']]==[b]


def test_large_queue_paginates_without_scheduling_games(store):
    # A field of jobs, not engine-process or game expansion.
    ids=[draft(store,str(i)) for i in range(120)]
    store.queue_call('add',all_ready=True)
    page=store.queue_call('page',50)
    assert page['total']==120 and len(page['items'])==50 and page['items'][0]['tid']==ids[50]
    assert not store.rows('SELECT * FROM games')


def test_add_all_ready_preserves_creation_order_when_timestamps_tie(store):
    ids=[draft(store,str(i)) for i in range(120)]
    # Make the formerly intermittent Windows clock collision deterministic.
    store.execute('UPDATE tournaments SET created=12345')
    store.queue_call('add',all_ready=True)
    actual=[item['tid'] for offset in (0,50,100) for item in store.queue_call('page',offset)['items']]
    assert actual==ids
    assert not store.rows('SELECT * FROM games')


def test_killed_worker_retains_queue_order_results_and_pending_setup(tmp_path):
    script="""import os,sys
from arena.store import Store
s=Store(sys.argv[1]);ids=[s.create_tournament(n,[{'name':'A'},{'name':'B'}],{'cycles':2},backup=False)['id'] for n in ['First','Second']]
s.queue_call('add',ids);s.queue_call('command','run',s.queue_call('summary')['revision']);s.queue_call('tick')
s.fill_queue(ids[0],4);g=s.claim(ids[0]);s.finish(g['aid'],'1/2-1/2','test','Committed result');g=s.claim(ids[0]);s.export_pending()
print(','.join(ids),flush=True);os._exit(0)
"""
    a,b=subprocess.check_output([sys.executable,'-c',script,str(tmp_path)],text=True).strip().split(',')
    with contextlib.closing(Store(tmp_path)) as s:
        q=s.queue_call('page');assert q['mode']=='paused' and q['active_tid']==a and [i['tid'] for i in q['items']]==[a,b]
        assert s.snapshot(a)['official_games']==1 and s.tournament(b)['can_edit']
        assert s.one("SELECT count(*) n FROM attempts WHERE reason='interrupted'")['n']==1
        command(s,'run');s.queue_call('tick');assert s.queue_call('summary')['active_tid']==a
        assert len(read_pgn((tmp_path/'games.pgn').read_text(encoding='utf-8')))==1


def test_runner_completes_reordered_queue_one_tournament_at_a_time(tmp_path):
    async def run():
        db=await Database().open(tmp_path);runner=Runner(db)
        try:
            ids=[]
            for i in range(3):
                t=await db.call('create_tournament',str(i),[profile('A',wait=.01),profile('B',wait=.01)],
                    {'cycles':2,'concurrency':2+i,'cpu_budget':2,'max_plies':4,'time_control':{'kind':'nodes','nodes':77}})
                ids.append(t['id'])
            await db.call('queue_call','add',ids)
            await db.call('queue_call','command','up',(await db.call('queue_call','summary'))['revision'],ids[2])
            await db.call('queue_call','command','run',(await db.call('queue_call','summary'))['revision'])
            await runner.start();deadline=time.monotonic()+25;order=[]
            while time.monotonic()<deadline:
                assert not runner.error,runner.error
                tids={v['tid'] for v in runner.live.values()};assert len(tids)<=1
                if tids and (not order or next(iter(tids))!=order[-1]):order.append(next(iter(tids)))
                q=await db.call('queue_call','summary')
                if q['mode']=='completed':break
                await asyncio.sleep(.01)
            assert q['mode']=='completed' and q['completed']==3 and order==[ids[0],ids[2],ids[1]]
            starts=await db.call('rows',"SELECT tid FROM audit WHERE action='state' AND json_extract(body,'$.source')='automatic_queue' ORDER BY id")
            assert [r['tid'] for r in starts]==order
            await db.call('export_pending')
            assert len(read_pgn((tmp_path/'games.pgn').read_text(encoding='utf-8')))==12
        finally:await runner.close()
    asyncio.run(run())


def test_api_queue_pause_drains_and_blocks_manual_start(tmp_path):
    async def run():
        app=await create_app(tmp_path,'queue');db=app['db'];runner=app['runner']
        async with TestClient(TestServer(app),headers={'X-Arena-Token':'queue'}) as client:
            t=await db.call('create_tournament','Long queue test',[profile('A',wait=.04),profile('B',wait=.04)],
                {'cycles':20,'concurrency':2,'max_plies':12,'time_control':{'kind':'nodes','nodes':77}})
            tid=t['id'];path='/api/tournament-queue'
            assert (await client.post(path,json={'action':'add','ids':[tid]})).status==200
            assert (await client.post(f'/api/tournaments/{tid}/action',json={'action':'start'})).status==400
            q=await (await client.get(path)).json()
            assert (await client.post(path,json={'action':'run','revision':q['revision']})).status==200
            deadline=time.monotonic()+10
            while not runner.live and time.monotonic()<deadline:await asyncio.sleep(.01)
            assert runner.live
            q=await (await client.get(path)).json()
            assert (await client.post(path,json={'action':'pause','revision':q['revision']})).status==200
            while runner.live and time.monotonic()<deadline:await asyncio.sleep(.02)
            await asyncio.sleep(.2)
            q=await (await client.get(path)).json()
            assert q['mode']=='paused' and not runner.live
            snap=await db.call('snapshot',tid)
            assert snap['state']=='paused' and 0<snap['official_games']<40
            assert not await db.call('one',"SELECT 1 FROM attempts WHERE reason='interrupted'")
            assert (await client.post(path,json={'action':'remove','tid':tid,'revision':q['revision']})).status==200
            assert (await db.call('tournament',tid))['queue'] is None
    asyncio.run(run())
