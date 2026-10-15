"""Defaults protect compact rating evidence without restoring explicit opt-outs."""
import asyncio
from contextlib import closing
import sqlite3

import pytest
from aiohttp.test_utils import TestClient,TestServer
from arena.store import Store
from arena.server import create_app
from arena import events
from test_rating_center import tournament,finish,read
from test_seasons import create,drive


def backup_counts(folder):
    counts={}
    for path in (folder/'backups').glob('recovery-*.sqlite3'):
        with closing(sqlite3.connect(path)) as db:
            counts[path.name]=db.execute('SELECT count(*) FROM rc_games').fetchone()[0]
    return counts


def test_collection_defaults_new_lists_and_explicit_opt_out_survive_restart(tmp_path):
    with closing(Store(tmp_path)) as s:
        assert s.one("SELECT automatic FROM rc_pools WHERE id='main'")['automatic']==1
        enabled=s.rating_center_call('command',{'action':'create','name':'Automatic'})['id']
        disabled=s.rating_center_call('command',{'action':'create','name':'Manual','automatic':False})['id']
        tid=tournament(s);finish(s,tid,['1-0','1/2-1/2']);s.set_state(tid,'paused')
        assert read(s,pool=enabled)['official_games']==2
        assert read(s,pool=disabled)['official_games']==0
        # A settings request that omits collection must not turn it off.
        s.rating_center_call('command',{'action':'configure','pool':enabled})
        assert s.one('SELECT automatic FROM rc_pools WHERE id=?',(enabled,))['automatic']==1
        s.rating_center_call('command',{'action':'configure','pool':'main','automatic':False})
    with closing(Store(tmp_path)) as s:
        assert s.one("SELECT automatic FROM rc_pools WHERE id='main'")['automatic']==0
        s.rating_center_call('command',{'action':'configure','pool':disabled})
        assert s.one('SELECT automatic FROM rc_pools WHERE id=?',(disabled,))['automatic']==0
        tid=tournament(s);finish(s,tid,['1/2-1/2','0-1']);s.set_state(tid,'paused')
        assert read(s,pool=enabled)['official_games']==4
        assert read(s,pool=disabled)['official_games']==0
        assert read(s)['official_games']==2


def test_default_retention_keeps_ratings_anchor_and_backup_then_adds_new_games(tmp_path):
    with closing(Store(tmp_path)) as s:
        tid=tournament(s);finish(s,tid,['1-0','1/2-1/2','0-1','1/2-1/2']);s.set_state(tid,'paused')
        key=read(s)['items'][0]['id']
        s.rating_center_call('command',{'action':'anchor','entry':key,'category':'blitz','rating':3700})
        before=read(s);s.export_pending();s.backup();snapshots=backup_counts(tmp_path)
        assert max(snapshots.values())==4
        s.delete_tournament(tid,'Rating test')
        assert read(s)['items']==before['items'] and read(s)['anchor']==before['anchor']
        assert s.one('SELECT count(*) n FROM attempts')['n']==0
        assert (tmp_path/'games.pgn').stat().st_size==0
        for path in (tmp_path/'backups').glob('recovery-*.sqlite3'):
            with closing(sqlite3.connect(path)) as db:
                # Older rotating backups legitimately precede some results.
                assert db.execute('SELECT count(*) FROM rc_games').fetchone()[0]==snapshots[path.name]
                assert db.execute('SELECT count(*) FROM tournaments').fetchone()[0]==0
    with closing(Store(tmp_path)) as s:
        assert read(s)['items']==before['items']
        tid=tournament(s);finish(s,tid,['1/2-1/2','0-1']);s.set_state(tid,'paused')
        assert read(s)['official_games']==6 and read(s)['pairs']==3
        assert read(s)['anchor']==before['anchor']
        assert all(x['games']==6 for x in read(s)['items'])


@pytest.mark.parametrize('scope',['tournament','event'])
@pytest.mark.parametrize('choice',[None,False])
def test_deletion_api_omission_keeps_evidence_explicit_false_removes_it(tmp_path,scope,choice):
    with closing(Store(tmp_path)) as s:
        if scope=='tournament':
            tid=tournament(s);finish(s,tid,['1-0','1/2-1/2']);s.set_state(tid,'paused')
        else:
            e=drive(s,create(s,n=4)['id']);eid=e['id']
        count=s.one('SELECT count(*) n FROM rc_games')['n'];assert count>0
        s.export_pending();s.backup();snapshots=backup_counts(tmp_path)
        assert max(snapshots.values())==count
    async def run():
        app=await create_app(tmp_path,'retention-default-test')
        runner=app['runner'];runner.scheduler.cancel();await asyncio.gather(runner.scheduler,return_exceptions=True)
        async with TestClient(TestServer(app),headers={'X-Arena-Token':'retention-default-test'}) as client:
            if scope=='tournament':url=f'/api/tournaments/{tid}/delete';body={'confirmed':True,'name':'Rating test'}
            else:
                preview=await (await client.post('/api/events',json={'action':'delete_preview','ids':[eid]})).json()
                url='/api/events';body={'action':'delete','ids':[eid],'expected':preview['events'],'confirmed':True}
            if choice is not None:body['keep_ratings']=choice
            response=await client.post(url,json=body);assert response.status==200,await response.text()
    asyncio.run(run())
    with closing(Store(tmp_path)) as s:
        assert s.one('SELECT count(*) n FROM rc_games')['n']==(count if choice is None else 0)
        assert s.one('SELECT count(*) n FROM attempts')['n']==0
        for path in (tmp_path/'backups').glob('recovery-*.sqlite3'):
            with closing(sqlite3.connect(path)) as db:
                # Shutdown may create a new recovery snapshot of the final state.
                assert db.execute('SELECT count(*) FROM rc_games').fetchone()[0]==(snapshots.get(path.name,count) if choice is None else 0)
