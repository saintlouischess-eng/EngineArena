import asyncio
import contextlib
import json
import sys
import chess
import pytest
from aiohttp.test_utils import TestClient,TestServer
from arena.conditions import position,preset_settings
from arena.models import TimeControl,Clock,go_command
from arena.server import create_app
from arena.store import Store


def test_edit_default_preset_survives_reopen_and_keeps_snapshot(tmp_path):
    s=Store(tmp_path);default=s.one('SELECT * FROM presets');name=default['name']
    settings=json.loads(default['body'])
    assert settings['time_control']['seconds']==180 and settings['time_control']['increment']==2
    assert settings['threads']==1 and settings['hash']==1024 and settings['paired'] and not settings['ponder']
    t=s.create_tournament('Original',[{'name':'A'},{'name':'B'}],{'time_control':settings['time_control']})
    revised=settings|{'time_control':{'kind':'nodes','nodes':12345},'ponder':True,'hash':64}
    s.save_preset(name,revised,name)
    with pytest.raises(ValueError,match='already exists'):s.save_preset(name,settings)
    s.close();s=Store(tmp_path)
    updated=json.loads(s.one('SELECT body FROM presets WHERE name=?',(name,))['body'])
    assert updated['ponder'] and updated['hash']==64
    c=Clock(TimeControl.parse(updated['time_control']));assert c.budget is None and go_command(c,c,c)=='go nodes 12345'
    assert s.tournament(t['id'])['settings']['time_control']==settings['time_control']
    s.close()


@pytest.mark.parametrize('bad',[{'kind':'staged','stages':[{'moves':40,'seconds':60,'increment':float('nan')}]},
    {'kind':'staged','stages':[{'moves':True,'seconds':60}]},{'kind':'fischer','seconds':True},
    {'kind':'staged','stages':[{'moves':40,'seconds':60,'increment':float('inf')}]},
    {'kind':'staged','stages':[{'moves':40,'seconds':60}],'repeat':'yes'}])
def test_invalid_time_control_cannot_enter_preset(bad):
    with pytest.raises(ValueError):preset_settings({'time_control':bad})


def test_position_rules_and_all_960_roundtrip():
    initial=position({'fen':chess.STARTING_FEN});assert initial['valid'] and len(initial['legal_moves'])==20
    seen=set()
    for n in range(960):
        p=position({'chess960_index':n});assert p['valid'] and p['chess960']
        assert chess.Board(p['fen'],chess960=True).chess960_pos()==n
        assert position(p)['fen']==p['fen'];seen.add(p['fen'])
    assert len(seen)==960
    for fen,message in [('8/8/8/8/8/8/8/8 w - - 0 1','White king is missing'),
      ('4k3/8/8/8/8/8/8/4K3 w K - 0 1','Castling rights'),
      ('4k3/8/8/8/8/8/8/4K3 w - e3 0 1','en-passant')]:
        p=position({'fen':fen});assert not p['valid'] and any(message in e for e in p['errors'])
    for fen in ['4k3/8/8/8/8/8/8/4K3 w - - -1 1','4k3/8/8/8/8/8/8/4K3 w - - 0 0']:
        with pytest.raises(ValueError):position({'fen':fen})


def test_named_position_snapshot_pairs_and_api_restart(tmp_path):
    async def run():
        app=await create_app(tmp_path,'conditions-token');runner=app['runner'];db=app['db']
        runner.scheduler.cancel()
        with contextlib.suppress(asyncio.CancelledError):await runner.scheduler
        async with TestClient(TestServer(app),headers={'X-Arena-Token':'conditions-token'}) as client:
            assert (await client.get('/assets/conditions.js')).status==200
            p1=await db.call('save_profile',{'name':'A','path':sys.executable})
            p2=await db.call('save_profile',{'name':'B','path':sys.executable})
            r=await client.get('/api/profiles?q=A&limit=1');v=await r.json()
            assert v['total']==1 and v['library_total']==2 and len(v['items'])==1
            r=await client.post('/api/positions',json={'name':'Start 42','chess960_index':42});assert r.status==200;saved=await r.json()
            r=await client.post('/api/positions',json={'name':'Start 42','chess960_index':43});assert r.status==400
            request={'name':'Recorded starting position','profiles':[p1['id'],p2['id']],'settings':{'cycles':1,'time_control':{'kind':'nodes','nodes':777}},'saved_position':'Start 42'}
            r=await client.post('/api/tournaments',json=request|{'all960':True});assert r.status==400
            r=await client.post('/api/tournaments',json=request);assert r.status==200;t=await r.json();tid=t['id']
            assert t['settings']['chess960'] and t['settings']['openings']==[saved] and t['total']==2
            r=await client.post('/api/positions',json={'name':'Start 42','original_name':'Start 42','chess960_index':43});assert r.status==200
            await db.call('set_state',tid,'running');await db.call('fill_queue',tid,2)
            games=await db.call('rows','SELECT opening,white,black,pair_no FROM games WHERE tid=? ORDER BY number',(tid,))
            assert len(games)==2 and games[0]['opening']==games[1]['opening']
            assert json.loads(games[0]['opening'])['fen']==saved['fen'] and games[0]['white']==games[1]['black']
            assert games[0]['pair_no']==games[1]['pair_no']
        s=Store(tmp_path)
        assert s.tournament(tid)['settings']['openings']==[saved]
        assert json.loads(s.one('SELECT body FROM positions')['body'])['fen']!=saved['fen']
        s.close()
    asyncio.run(run())
