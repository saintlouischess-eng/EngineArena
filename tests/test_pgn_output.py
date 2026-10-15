import contextlib
import io
import os
import sqlite3
import types
import subprocess
import sys
import asyncio
import time
import chess
import chess.pgn
import pytest
from arena.store import Store
from arena.pgn_output import Target, Outputs, configure
from test_pgn_readable import make_game


def games(path):
    result=[]
    with path.open(encoding='utf-8-sig') as f:
        while g:=chess.pgn.read_game(f):
            assert not g.errors;result.append(g)
    return result


def setup(tmp_path):
    store=Store(tmp_path/'data')
    t,g=make_game(store,{'fen':chess.STARTING_FEN})
    service=Outputs(types.SimpleNamespace(store=store))
    output=service.prepare({'enabled':True,'path':str(tmp_path/'list.pgn'),'mode':'new','preset':'clean'})
    configure(store,t['id'],output)
    return store,t,g,service,tmp_path/'list.pgn'


def dispose(store,service):
    for t in service.targets.values():t.close()
    service.executor.shutdown();store.close()


def test_multiple_tournaments_restart_replacement_and_diagnostic(tmp_path):
    store,t,g,service,path=setup(tmp_path)
    try:
        service.tick();assert len(games(path))==1
        original=path.read_bytes()
        service.tick();assert path.read_bytes()==original
        for mode,result in [('diagnostic','1-0'),('replacement','0-1')]:
            store.set_state(t['id'],'paused');store.requeue(t['id'],[g['id']],mode=mode)
            store.set_state(t['id'],'running');changed=store.claim(t['id']);store.finish(changed['aid'],result,'fixture')
            service.tick();assert len(games(path))==1
            assert games(path)[0].headers['Result']==('1/2-1/2' if mode=='diagnostic' else '0-1')
        assert len(store.game_detail(g['id'])['attempts'])==3
        t2,g2=make_game(store,{'fen':chess.STARTING_FEN})
        output=service.prepare({'enabled':True,'path':str(path),'mode':'append','preset':'clean'})
        configure(store,t2['id'],output);service.tick()
        assert {p.headers['GameId'] for p in games(path)}=={g['id'],g2['id']}
        before=path.read_bytes()
        for target in service.targets.values():target.close()
        service.targets.clear();service.status.clear();service.tick()
        assert path.read_bytes()==before
    finally:dispose(store,service)


@pytest.mark.parametrize('stage',['before_write','partial_append','after_write','after_replace'])
def test_committed_export_recovers_each_file_commit_gap(tmp_path,monkeypatch,stage):
    store,t,g,service,path=setup(tmp_path)
    try:
        if stage=='after_replace':
            service.tick();store.set_state(t['id'],'paused');store.requeue(t['id'],[g['id']],mode='replacement')
            store.set_state(t['id'],'running');r=store.claim(t['id']);store.finish(r['aid'],'1-0','fixture')
        target=next(iter(service.targets.values()))
        if stage in ('after_write','after_replace'):
            monkeypatch.setattr(target,'checkpoint',lambda:(_ for _ in ()).throw(OSError('simulated power loss')))
        else:
            def crash(recovery=False):
                if stage=='partial_append':
                    body=target.db.execute('SELECT body FROM append_bytes LIMIT 1').fetchone()[0]
                    with path.open('ab') as f:f.write(body[:37]);f.flush();os.fsync(f.fileno())
                raise OSError('simulated power loss')
            monkeypatch.setattr(target,'write_file',crash)
        service.tick();assert service.status[str(path).lower() if os.name=='nt' else str(path)]['state']=='error'
        target.close();service.targets.clear();service.status.clear()
        service.tick();assert not next(iter(service.status.values())).get('error')
        result=games(path);assert len(result)==1
        assert result[0].headers['Result']==('1-0' if stage=='after_replace' else '1/2-1/2')
    finally:dispose(store,service)


def test_external_edits_are_not_destroyed_and_new_file_is_safe(tmp_path):
    store,t,g,service,path=setup(tmp_path)
    try:
        service.tick();path.write_bytes(path.read_bytes()+b'EXTERNAL EDIT\n');before=path.read_bytes()
        service.tick();assert next(iter(service.status.values()))['state']=='error'
        assert path.read_bytes()==before
        with pytest.raises(ValueError,match='already exists'):
            service.prepare({'enabled':True,'path':str(path),'mode':'new'})
        assert path.read_bytes()==before
        with pytest.raises(ValueError,match='data folder'):
            service.prepare({'enabled':True,'path':str(store.folder/'games.pgn')})
    finally:dispose(store,service)


def test_import_existing_pgn_and_identity_deduplication(tmp_path):
    store=Store(tmp_path/'data');service=Outputs(types.SimpleNamespace(store=store));path=tmp_path/'import.pgn'
    try:
        t,g=make_game(store,{'fen':chess.STARTING_FEN})
        path.write_text(store.export_official(t['id'],export_options={'preset':'testing'}),encoding='utf-8')
        original=path.read_bytes()
        output=service.prepare({'enabled':True,'path':str(path),'mode':'append','preset':'testing'})
        configure(store,t['id'],output);service.tick()
        assert path.read_bytes()==original and len(games(path))==1
        t2,g2=make_game(store,{'fen':chess.STARTING_FEN});configure(store,t2['id'],output);service.tick()
        assert len(games(path))==2
        assert path.read_bytes().startswith(original)
    finally:dispose(store,service)


def test_reset_removes_official_game_and_preserves_original_attempt(tmp_path):
    store,t,g,service,path=setup(tmp_path)
    try:
        service.tick()
        with store.tx():store._set_official(store.one('SELECT * FROM games WHERE id=?',(g['id'],)),None)
        service.tick();assert games(path)==[]
        assert store.one('SELECT result FROM attempts WHERE id=?',(g['aid'],))['result']=='1/2-1/2'
    finally:dispose(store,service)


def test_deleted_tournament_leaves_exported_file_intact(tmp_path):
    store,t,g,service,path=setup(tmp_path)
    try:
        service.tick();before=path.read_bytes();store.set_state(t['id'],'paused')
        store.delete_tournament(t['id'],t['name']);service.tick()
        assert path.read_bytes()==before
        assert not store.one('SELECT 1 FROM pgn_links')
        assert not store.one('SELECT 1 FROM pgn_changes')
    finally:dispose(store,service)


def test_other_workspace_cannot_write_to_managed_output(tmp_path):
    store,t,g,service,path=setup(tmp_path)
    try:
        service.tick();before=path.read_bytes()
        with pytest.raises((OSError,ValueError)):Target(path,'foreign','clean')
        next(iter(service.targets.values())).close();service.targets.clear()
        with pytest.raises(ValueError,match='another Engine Arena'):Target(path,'foreign','clean')
        assert path.read_bytes()==before
    finally:dispose(store,service)


def test_forced_export_process_termination_and_recovery(tmp_path):
    store,t,g,service,path=setup(tmp_path)
    try:
        for target in service.targets.values():target.close()
        service.targets.clear()
        code='''import os,sys
from arena.pgn_output import Target
t=Target(sys.argv[1],sys.argv[2],'clean')
t.checkpoint=lambda:os._exit(77)
t.sync(sys.argv[3],[sys.argv[4]])
'''
        r=subprocess.run([sys.executable,'-c',code,str(path),service.workspace,str(store.path),t['id']],timeout=20)
        assert r.returncode==77
        service.tick()
        assert len(games(path))==1 and not next(iter(service.status.values())).get('error')
        before=path.read_bytes();service.tick();assert path.read_bytes()==before
    finally:dispose(store,service)


@pytest.mark.parametrize('text',[
    '[Event "Truncated"]\n[Result "1-0"]\n\n1. e4 e5\n',
    '[Event "Interrupted"]\n\n1. e4 *\n',
    'not a PGN\n',
])
def test_bad_existing_file_is_untouched(tmp_path,text):
    store=Store(tmp_path/'data');service=Outputs(types.SimpleNamespace(store=store));path=tmp_path/'bad.pgn'
    try:
        path.write_text(text,encoding='utf-8');before=path.read_bytes()
        with pytest.raises(ValueError):service.prepare({'enabled':True,'path':str(path),'mode':'append'})
        assert path.read_bytes()==before
    finally:dispose(store,service)


def test_api_create_select_continue_disable_and_live_status(tmp_path):
    from aiohttp.test_utils import TestClient,TestServer
    from arena.server import create_app
    from test_core import profile
    async def run():
        app=await create_app(tmp_path/'data','outputs');db=app['db'];runner=app['runner']
        runner.scheduler.cancel();await asyncio.gather(runner.scheduler,return_exceptions=True)
        async with TestClient(TestServer(app),headers={'X-Arena-Token':'outputs'}) as client:
            profiles=[(await db.call('save_profile',profile(n)))['id'] for n in ['A','B']]
            output={'enabled':True,'path':str(tmp_path/'api.pgn'),'mode':'new','preset':'annotated'}
            response=await client.post('/api/tournaments',json={'name':'PGN API','profiles':profiles,'settings':{'cycles':1},'pgn_output':output})
            assert response.status==200,await response.text()
            t=await response.json();tid=t['id']
            await db.call('set_state',tid,'running');await db.call('fill_queue',tid,2)
            g=await db.call('claim',tid);await db.call('finish',g['aid'],'1-0','fixture')
            await runner.pgn_outputs.flush()
            r=await (await client.get('/api/pgn-output')).json()
            assert r['links'][0]['tid']==tid and r['targets'][0]['games']==1
            s=await (await client.get('/api/status')).json();assert s['pgn_outputs'][0]['state']=='saved'
            response=await client.post('/api/pgn-output',json={'tid':tid,'enabled':False});assert response.status==200
            before=(tmp_path/'api.pgn').read_bytes()
            g=await db.call('claim',tid);await db.call('finish',g['aid'],'0-1','fixture');await runner.pgn_outputs.flush()
            assert (tmp_path/'api.pgn').read_bytes()==before
            response=await client.post('/api/pgn-output',json={'tid':tid,**output,'mode':'append'});assert response.status==200
            await runner.pgn_outputs.flush();assert len(games(tmp_path/'api.pgn'))==2
    asyncio.run(run())
