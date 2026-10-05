import asyncio
import io
from pathlib import Path
import sys

import chess
import chess.pgn
import pytest

from arena.store import DEFAULTS
from arena.runner import Database, Runner
from arena.uci import EngineFailure, UciEngine


# Positions and exact replies from the user's September 2026 Naum 4.6 failures.
NAUM_CASES = [
    ('r5k1/5pp1/bBp1pn2/P1N5/4P3/K7/5PpP/2R4R b - - 0 24', 'g2h1Q'),
    ('8/P7/6p1/5k2/1p6/1P6/6K1/q7 w - - 2 90', 'a7a8Q'),
    ('8/P4ppk/8/7p/4P2P/5PP1/1p1K4/1r6 w - - 0 56', 'a7a8Q'),
    ('8/1P4p1/p1n2p2/1b1k1P1p/4pB2/4K2P/1P4P1/8 w - - 0 41', 'b7b8Q'),
    ('8/5P2/7p/8/8/6k1/3q4/5K2 w - - 3 74', 'f7f8Q'),
    ('8/4P2k/p2K4/P2P4/8/8/7p/8 b - - 0 57', 'h2h1Q'),
    ('8/2P5/4bp2/p7/P7/5k1p/8/6K1 w - - 6 67', 'c7c8N'),
    ('8/4P3/pk3K1p/7P/P2P1P2/8/1p6/8 b - - 0 72', 'b2b1Q'),
    ('8/5P2/8/3p4/3P3K/8/3kp3/8 w - - 0 66', 'f7f8Q'),
    ('2R5/3Pb1p1/4k2p/2p5/1p2p3/4P2P/1r1BK1P1/8 w - - 3 44', 'd7d8Q'),
]


def engine(move, ponder=None):
    args = [str(Path(__file__).with_name('fault_engine.py').resolve()), '--bestmove', move]
    if ponder: args += ['--mode', 'ponder', '--ponder-move', ponder]
    return UciEngine({'path': sys.executable, 'args': args, 'hash': 1}, DEFAULTS | {'ponder': bool(ponder)})


@pytest.mark.parametrize('fen,reply', NAUM_CASES + [
    ('7k/P7/8/8/8/8/8/7K w - - 0 1', 'a7a8R'),
    ('7k/P7/8/8/8/8/8/7K w - - 0 1', 'a7a8B'),
    ('7k/P7/8/8/8/8/8/7K w - - 0 1', 'a7a8q'),
])
def test_legal_promotions_from_engine(fen, reply):
    async def run():
        e = engine(reply)
        try:
            await e.start()
            board = chess.Board(fen)
            move, _, info = await e.play(board, 'go nodes 100', None)
            assert move in board.legal_moves
            assert move.uci() == reply.lower()
            assert info['pv'] == reply.lower()
            assert '< bestmove ' + reply in e.log
            board.push(move)
            await e.position(board)
            assert e.log[-1].endswith(' moves ' + reply.lower())
        finally:
            await e.close()
    asyncio.run(run())


@pytest.mark.parametrize('reply', ['a7b8Q', 'a7a6Q', 'a7a8K', 'a7a8', 'A7A8Q', '0000'])
def test_promotion_compatibility_still_rejects_illegal_moves(reply):
    async def run():
        e = engine(reply)
        try:
            await e.start()
            with pytest.raises(EngineFailure) as failure:
                await e.play(chess.Board('7k/P7/8/8/8/8/8/7K w - - 0 1'), 'go nodes 100', None)
            assert failure.value.reason == 'illegal_move'
            assert reply in str(failure.value)
        finally:
            await e.close()
    asyncio.run(run())


def test_uppercase_ponder_promotion_is_sent_back_in_canonical_form():
    async def run():
        e = engine('h2h3', 'a2a1Q')
        try:
            await e.start()
            board = chess.Board('7k/8/8/8/8/8/p6K/8 w - - 0 1')
            move, _, _ = await e.play(board, 'go nodes 100', None)
            board.push(move)
            await e.begin_ponder(board, 'go nodes 100')
            assert e.pondering
            assert any(line.endswith(' moves h2h3 a2a1q') for line in e.log)
            await e.stop_ponder()
        finally:
            await e.close()
    asyncio.run(run())


def test_promotion_is_committed_and_exported_without_losing_raw_reply(tmp_path):
    async def run():
        db = await Database().open(tmp_path)
        runner = Runner(db)
        fen, reply = NAUM_CASES[0]
        profile = engine(reply).profile
        try:
            t = await db.call('create_tournament', 'Promotion regression',
                              [profile | {'name': name} for name in ('White', 'Naum reply fixture')],
                              {'cycles': 1, 'paired': False, 'concurrency': 1, 'max_plies': 1,
                               'time_control': {'kind': 'nodes', 'nodes': 100}}, [{'fen': fen}])
            await db.call('set_state', t['id'], 'running')
            await runner.start()
            for _ in range(200):
                state = await db.call('snapshot', t['id'])
                if state['state'] == 'completed': break
                assert not runner.error
                await asyncio.sleep(.05)
            assert state['state'] == 'completed'
            assert state['official_games'] == 1
            page = await db.call('games', t['id'])
            detail = await db.call('game_detail', page['items'][0]['id'])
            attempt, = detail['attempts']
            assert attempt['reason'] == 'max_plies_adjudication'
            assert attempt['moves'][0]['uci'] == 'g2h1q'
            assert attempt['moves'][0]['san'] == 'gxh1=Q'
            assert any(row['line'] == '< bestmove g2h1Q' for row in attempt['logs'])
            text = await db.call('export_official', t['id'], style='archive')
            game = chess.pgn.read_game(io.StringIO(text))
            assert not game.errors
            assert [m.uci() for m in game.mainline_moves()] == ['g2h1q']
            assert 'gxh1=Q' in text
        finally:
            await runner.close()
    asyncio.run(run())
