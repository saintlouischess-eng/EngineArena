import asyncio
import base64
import contextlib
import io
import json
import struct

import chess
import chess.pgn
import chess.polyglot
import pytest
from aiohttp.test_utils import TestClient, TestServer

from arena.openings import inspect_openings
from arena.pgn_export import OfficialPgnReader
from arena.pgn_format import control, render_attempt
from arena.server import create_app
from arena.store import Store


def parse(text):
    game = chess.pgn.read_game(io.StringIO(text))
    assert game and not game.errors
    return game


def make_game(store, opening, settings=None):
    profiles = [{'name': 'White "quoted"', 'threads': 2, 'hash': 64}, {'name': 'Black – unicode', 'threads': 4, 'hash': 128}]
    t = store.create_tournament('Readable export', profiles, {'cycles': 1, **(settings or {})}, [opening])
    store.set_state(t['id'], 'running'); store.fill_queue(t['id'], 2)
    g = store.claim(t['id']); board = chess.Board(opening['fen'], chess960=t['settings']['chess960'])
    for ply in range(1, 3):
        move = next(iter(board.legal_moves)); san = board.san(move); board.push(move)
        clocks = {side: {'remaining': None if (settings or {}).get('time_control', {}).get('kind') == 'nodes' else 179.25} for side in ('white', 'black')}
        store.move(g['aid'], ply, move.uci(), san, board.fen(), 3.904174, clocks, {'cp': 57, 'depth': 33, 'nodes': 200000, 'nps': 70000})
    store.finish(g['aid'], '1/2-1/2', 'threefold_repetition'); store.export_pending()
    return t, g


def test_polyglot_prefix_and_legacy_recorded_history_export(tmp_path):
    book = tmp_path / 'book.bin'; board = chess.Board(); entries = []
    line = ['e2e4', 'e7e5', 'g1f3', 'b8c6', 'f1b5', 'a7a6', 'b5a4', 'g8f6', 'e1g1', 'f8e7', 'f1e1', 'b7b5', 'a4b3', 'd7d6', 'c2c3']
    for uci in line:
        move = chess.Move.from_uci(uci)
        raw = (7 if uci == 'e1g1' else move.to_square) | (move.from_square << 6)
        entries.append((chess.polyglot.zobrist_hash(board), raw)); board.push(move)
    book.write_bytes(b''.join(struct.pack('>QHHI', key, raw, 1, 0) for key, raw in sorted(entries)))
    opening = inspect_openings(book, 16)['items'][0]
    assert opening['moves'] == line
    opening.pop('start_fen') # existing pre-fix tournament records
    with contextlib.closing(Store(tmp_path / 'data')) as store:
        t, g = make_game(store, opening)
        # Old immutable PGN is intentionally ignored on corrected re-export.
        store.execute('UPDATE outbox SET pgn=? WHERE aid=?', ('[Event "old FEN-only export"]\n\n*\n', g['aid']))
        text = store.export_official(t['id']); game = parse(text); nodes = list(game.mainline())
        assert len(nodes) == 17 and [m.uci() for m in game.mainline_moves()][:15] == line
        assert 'FEN' not in game.headers and game.headers['BookPlyCount'] == '15'
        assert all(n.comment == 'book' for n in nodes[:15])
        assert nodes[15].comment == '-0.57/33 3.904s' and nodes[16].comment == '+0.57/33 3.904s'
        assert 'SettingsEncoding' not in text and 'WhiteSettings' not in text
        assert game.headers['TimeControl'] == '180+2' and game.headers['WhiteThreads'] == '2'
        assert game.headers['Termination'] == 'normal'
        assert store.snapshot(t['id'])['official_games'] == 1


def test_custom_start_pgn_preserves_root_and_move_numbers(tmp_path):
    fen = 'rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 8'
    path = tmp_path / 'custom.pgn'
    path.write_text(f'[SetUp "1"]\n[FEN "{fen}"]\n\n8... e5 9. Nf3 Nc6 *\n')
    opening = inspect_openings(path, 3)['items'][0]
    assert opening['start_fen'] == fen
    with contextlib.closing(Store(tmp_path / 'data')) as store:
        t, g = make_game(store, opening)
        text = store.export_official(t['id']); game = parse(text)
        assert game.headers['FEN'] == fen and '8... e5 { book }' in text
        assert len(list(game.mainline_moves())) == 5


@pytest.mark.parametrize('style', ['compact', 'tagged', 'moves', 'archive'])
def test_export_modes_preserve_results_and_control_annotations(tmp_path, style):
    with contextlib.closing(Store(tmp_path)) as store:
        t, g = make_game(store, {'fen': chess.STARTING_FEN})
        text = store.export_official(t['id'], style=style); game = parse(text)
        assert game.headers['Result'] == '1/2-1/2' and game.headers['AttemptId'] == g['aid']
        nodes = list(game.mainline())
        if style == 'moves': assert all(not n.comment for n in nodes)
        elif style == 'compact': assert nodes[1].comment == '-0.57/33 3.904s'
        else:
            assert nodes[1].eval().white().score() == 57 and nodes[1].eval_depth() == 33
            assert nodes[1].emt() == 3.904 and nodes[1].clock() == 179.25
        if style == 'archive':
            settings = json.loads(base64.b64decode(game.headers['WhiteSettings']))
            assert settings['name'] == 'White "quoted"' and settings['threads'] == 2
        else: assert 'SettingsEncoding' not in game.headers
        if style == 'compact':
            reduced = parse(store.export_official(t['id'], style=style, perspective='white', annotations=['eval']))
            assert list(reduced.mainline())[1].comment == '+0.57'


def test_node_only_clock_mate_and_missing_measurements(tmp_path):
    with contextlib.closing(Store(tmp_path)) as store:
        t, g = make_game(store, {'fen': chess.STARTING_FEN}, {'time_control': {'kind': 'nodes', 'nodes': 1000}})
        store.execute('UPDATE moves SET info=? WHERE aid=? AND ply=2', (json.dumps({'mate': -4, 'depth': 20}), g['aid']))
        compact = parse(store.export_official(t['id'])); assert compact.end().comment == '+M4/20 3.904s'
        tagged = parse(store.export_official(t['id'], style='tagged'))
        assert tagged.end().eval().white().mate() == -4 and tagged.end().clock() is None
        assert tagged.headers['TimeControl'] == '-' and 'no chess clock' in tagged.headers['WhiteSearchControl']
        store.execute('UPDATE moves SET info=? WHERE aid=?', ('{}', g['aid']))
        assert parse(store.export_official(t['id'])).end().comment == '3.904s'


def test_invalid_or_missing_opening_history_retains_recorded_fen(tmp_path):
    board = chess.Board(); board.push_san('e4')
    with contextlib.closing(Store(tmp_path)) as store:
        t, g = make_game(store, {'fen': board.fen(), 'moves': ['d2d4']})
        game = parse(store.export_official(t['id']))
        assert game.headers['FEN'] == board.fen() and game.headers['BookPlyCount'] == '0'
        assert 'could not be verified' in game.headers['OpeningHistory']
        assert len(list(game.mainline_moves())) == 2


def test_chess960_opening_root_and_castling(tmp_path):
    root = chess.Board('4k3/8/8/8/8/8/8/RK5R w KQ - 0 1', chess960=True)
    board = root.copy(); board.push_uci('b1h1')
    with contextlib.closing(Store(tmp_path)) as store:
        t, g = make_game(store, {'fen': board.fen(), 'start_fen': root.fen(), 'moves': ['b1h1']}, {'chess960': True})
        game = parse(store.export_official(t['id']))
        assert game.headers['Variant'] == 'Chess960'
        assert list(game.mainline())[0].san() == 'O-O' and list(game.mainline())[0].comment == 'book'


def test_readable_control_descriptions():
    assert control({'kind': 'movetime', 'seconds': 2})[0] == '*2'
    assert control({'kind': 'delay', 'seconds': 60, 'delay': 2}) == ('?', '60s with 2s simple delay')
    assert control({'kind': 'staged', 'stages': [{'moves': 40, 'seconds': 120}, {'moves': 0, 'seconds': 60, 'increment': 1}]})[0] == '40/120:60+1'
    assert 'repeat' in control({'kind': 'staged', 'repeat': True, 'stages': [{'moves': 40, 'seconds': 120}]})[1]


def test_http_export_options_and_invalid_requests(tmp_path):
    async def run():
        app = await create_app(tmp_path, 'pgn'); runner = app['runner']; runner.scheduler.cancel()
        with contextlib.suppress(asyncio.CancelledError): await runner.scheduler
        db = app['db']; t = await db.call('create_tournament', 'Export', [{'name': 'A'}, {'name': 'B'}], {'cycles': 1})
        await db.call('set_state', t['id'], 'running'); await db.call('fill_queue', t['id'], 2)
        g = await db.call('claim', t['id']); await db.call('finish', g['aid'], '1-0', 'fixture')
        async with TestClient(TestServer(app), headers={'X-Arena-Token': 'pgn'}) as client:
            for query in ('style=wrong', 'perspective=black', 'annotations=invalid'):
                response = await client.get(f'/api/export/{t["id"]}/pgn?{query}')
                assert response.status == 400
            for style in ('compact', 'tagged', 'moves', 'archive'):
                response = await client.get(f'/api/export/{t["id"]}/pgn?style={style}')
                assert response.status == 200
                assert parse(await response.text()).headers['AttemptId'] == g['aid']
            assert (await client.get('/assets/pgn.js')).status == 200
    asyncio.run(run())
