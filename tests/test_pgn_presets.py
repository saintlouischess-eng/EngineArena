import asyncio
import base64
import contextlib
import io
import json
import re

import chess
import chess.pgn
import pytest
from aiohttp.test_utils import TestClient,TestServer
from arena.pgn_export import OfficialPgnReader,preview
from arena.pgn_format import render_attempt
from arena.pgn_options import PRESETS,REQUIRED,normalize
from arena.server import create_app
from arena.store import Store
from test_pgn_readable import make_game,parse


def opening():
    board=chess.Board();moves=['e2e4','e7e5','g1f3','b8c6']
    for uci in moves:board.push_uci(uci)
    return {'fen':board.fen(),'moves':moves,'name':'Open game','eco':'C20'}


@pytest.mark.parametrize('preset',PRESETS)
def test_presets_preserve_game_and_preview_matches_stream(tmp_path,preset):
    with contextlib.closing(Store(tmp_path)) as store:
        t,g=make_game(store,opening(),{'opening_source':{'name':'test.bin','depth':4}})
        choices={'preset':preset}
        text=store.export_official(t['id'],export_options=choices);game=parse(text)
        assert list(game.mainline_moves())==list(parse(store.export_official(t['id'])).mainline_moves())
        assert game.headers['Result']=='1/2-1/2'
        keys=list(game.headers);assert keys[:7]==list(REQUIRED) and keys[7:]==sorted(keys[7:])
        assert preview(store.path,t['id'],choices)['pgn']==text
        if preset=='clean':
            assert 'AttemptId' not in game.headers and 'WhiteSettings' not in game.headers
            assert all(not n.comment for n in game.mainline())
        else:
            assert game.headers['OpeningBook']=='test.bin'
            if preset!='archive':assert text.count('End of opening book')==1
        if preset=='archive':
            assert json.loads(base64.b64decode(game.headers['WhiteSettings']))['threads']==2
        elif preset=='testing':
            assert game.headers['AttemptId']==g['aid'] and game.end().clock()==179.25
        assert not re.search(r'\d+\.(?:\.\.)?\s*\n',text.split('\n\n',1)[1])


def test_minimal_headers_protect_fen_node_controls_and_score_perspective(tmp_path):
    board=chess.Board();board.push_uci('d2d4')
    with contextlib.closing(Store(tmp_path)) as store:
        t,g=make_game(store,{'fen':board.fen()},{'time_control':{'kind':'nodes','nodes':77}})
        choices={'preset':'clean','headers':[]}
        game=parse(store.export_official(t['id'],export_options=choices))
        assert game.headers['SetUp']=='1' and game.headers['FEN']==board.fen()
        assert game.headers['TimeControl']=='-' and game.headers['WhiteSearchControl']=='77 nodes/move; no chess clock'
        assert 'AttemptId' not in game.headers
        choices.update(style='compact',annotations=['eval'],perspective='engine')
        game=parse(store.export_official(t['id'],export_options=choices))
        assert game.headers['ScorePerspective']=='Moving engine'
        assert game.end().comment=='+0.57'  # second move in Black-to-move game is White


def test_custom_settings_encoding_labels_and_book_markers(tmp_path):
    with contextlib.closing(Store(tmp_path)) as store:
        t,g=make_game(store,opening())
        for marker,expected in [('none',0),('boundary',1),('all',4)]:
            choices={'preset':'clean','headers':['BlackSettings'],'book_comments':marker,
                     'event':'Export "label"\nonly','site':'Local \\ test','columns':60}
            text=store.export_official(t['id'],export_options=choices);game=parse(text)
            assert sum(bool(n.comment) for n in list(game.mainline())[:4])==expected
            assert game.headers['SettingsEncoding']=='base64-json-utf8' and 'WhiteSettings' not in game.headers
            assert text.startswith('[Event "Export \\"label\\" only"]\n')
            assert '[Site "Local \\\\ test"]\n' in text
        assert store.tournament(t['id'])['name']=='Readable export'


def test_official_replacement_is_exported_once_and_diagnostic_is_excluded(tmp_path):
    with contextlib.closing(Store(tmp_path)) as store:
        t,g=make_game(store,opening());tid=t['id']
        for mode,result in [('diagnostic','1-0'),('replacement','0-1')]:
            store.set_state(tid,'paused');store.requeue(tid,[g['id']],mode=mode);store.set_state(tid,'running')
            changed=store.claim(tid);store.finish(changed['aid'],result,'fixture')
        for preset in PRESETS:
            text=store.export_official(tid,export_options={'preset':preset});stream=io.StringIO(text)
            game=chess.pgn.read_game(stream);assert game.headers['Result']=='0-1' and chess.pgn.read_game(stream) is None
            if preset in ('testing','archive'):assert game.headers['AttemptId']==changed['aid']
        assert len(store.game_detail(g['id'])['attempts'])==3


def test_essential_headers_preserve_chess960_and_asymmetric_controls(tmp_path):
    root=chess.Board('4k3/8/8/8/8/8/8/RK5R w KQ - 0 1',chess960=True)
    board=root.copy();board.push_uci('b1h1')
    with contextlib.closing(Store(tmp_path)) as store:
        t,g=make_game(store,{'fen':board.fen(),'start_fen':root.fen(),'moves':['b1h1']},{'chess960':True})
        profile=json.loads(store.one('SELECT profile FROM participants WHERE tid=? AND slot=?',(t['id'],g['white']))['profile'])
        profile['time_control']={'kind':'fischer','seconds':180,'increment':0.05}
        store.execute('UPDATE participants SET profile=? WHERE tid=? AND slot=?',(json.dumps(profile),t['id'],g['white']))
        text=store.export_official(t['id'],export_options={'preset':'clean','headers':[]});game=parse(text)
        assert game.headers['Variant']=='Chess960' and game.headers['SetUp']=='1'
        assert game.headers['FEN']==root.fen() and list(game.mainline())[0].san()=='O-O'
        assert game.headers['TimeControl']=='?' and game.headers['WhiteTimeControl']=='180+0.05'
        assert game.headers['BlackTimeControl']=='180+2'


def test_essential_headers_use_recorded_knockout_playoff_control(tmp_path):
    recorded={**opening(),'competition_stage':'playoff','playoff_stage':2,
              'playoff_time_control':{'kind':'nodes','nodes':250},'ko_opening_progression':True}
    with contextlib.closing(Store(tmp_path)) as store:
        t,g=make_game(store,opening())
        # The KO scheduler adds these fields to the scheduled game, after the
        # opening source has been normalized at tournament creation.
        store.execute('UPDATE games SET opening=? WHERE id=?',(json.dumps(recorded),g['id']))
        game=parse(store.export_official(t['id'],export_options={'preset':'clean','headers':['OpeningPolicy']}))
        assert game.headers['TimeControl']=='-'
        assert game.headers['WhiteSearchControl']==game.headers['BlackSearchControl']=='250 nodes/move; no chess clock'
        assert game.headers['OpeningPolicy']=='KO shared sequence; new opening per pair'


def test_fixed_time_per_move_is_not_exported_as_an_hourglass_clock(tmp_path):
    with contextlib.closing(Store(tmp_path)) as store:
        t,g=make_game(store,opening(),{'time_control':{'kind':'movetime','seconds':0.25}})
        game=parse(store.export_official(t['id'],export_options={'preset':'clean','headers':[]}))
        assert game.headers['TimeControl']=='1/0.25'
        assert game.headers['WhiteSearchControl']==game.headers['BlackSearchControl']=='0.25 seconds/move'


def test_automatic_journal_keeps_identifiers_and_annotation_setting(tmp_path):
    with contextlib.closing(Store(tmp_path)) as store:
        t,g=make_game(store,opening(),{'annotations':False})
        game=parse((tmp_path/'games.pgn').read_text(encoding='utf-8'))
        assert game.headers['AttemptId']==g['aid'] and game.headers['GameId']==g['id']
        assert game.headers['WhiteEngine'] and game.headers['WhiteThreads']=='2'
        assert list(game.mainline())[3].comment=='End of opening book'
        assert all(not n.comment for n in list(game.mainline())[4:])
        assert 'ScorePerspective' not in game.headers


@pytest.mark.parametrize('settings',[{'preset':'bad'},{'headers':['FEN']},{'headers':'WhiteEngine'},
    {'annotations':['bad']},{'columns':0},{'columns':True},{'columns':80.5},{'book_comments':'bad'},
    {'names':'bad'},{'date_zone':'bad'},{'event':'x'*201},{'unknown':1}])
def test_invalid_options_rejected(settings):
    with pytest.raises(ValueError):normalize(settings)


def test_preview_and_stream_http_settings_and_empty_tournament(tmp_path):
    async def run():
        app=await create_app(tmp_path,'pgn-options');app['runner'].scheduler.cancel()
        with contextlib.suppress(asyncio.CancelledError):await app['runner'].scheduler
        async with TestClient(TestServer(app),headers={'X-Arena-Token':'pgn-options'}) as client:
            db=app['db'];t=await db.call('create_tournament','Export API',[{'name':'A'},{'name':'B'}],{'cycles':1});tid=t['id']
            schema=await (await client.get('/api/pgn-options')).json();assert len(schema['presets'])==4
            empty=await (await client.post(f'/api/tournaments/{tid}/pgn-preview',json={'preset':'clean'})).json()
            assert empty['game_number'] is None
            await db.call('set_state',tid,'running');await db.call('fill_queue',tid,2)
            g=await db.call('claim',tid);await db.call('finish',g['aid'],'1-0','fixture')
            for preset in PRESETS:
                sample=await (await client.post(f'/api/tournaments/{tid}/pgn-preview',json={'preset':preset})).json()
                response=await client.get(f'/api/export/{tid}/pgn?preset={preset}')
                assert response.status==200 and await response.text()==sample['pgn']
            bad=await client.get(f'/api/export/{tid}/pgn?preset=clean&headers=BadHeader')
            assert bad.status==400
            assert (await client.post(f'/api/tournaments/{tid}/pgn-preview',json={'columns':999})).status==400
    asyncio.run(run())
