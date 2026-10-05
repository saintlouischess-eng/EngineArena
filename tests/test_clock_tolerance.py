"""Clock debt regression from the September 20 live KO audit."""
import asyncio
import json

import chess
import pytest

from arena.models import Clock, TimeControl, go_command
from arena.runner import Database, Runner
from arena.store import DEFAULTS
from arena.uci import EngineFailure, UciEngine


def simulated_reply(monkeypatch, elapsed):
    """Supply timestamped replies without depending on OS timer granularity."""
    sent = []
    monkeypatch.setattr('arena.uci.time.perf_counter', lambda: 100.0)

    async def send(engine, command):
        sent.append(command)
        if command.startswith('go ') or command == 'ponderhit':
            board = chess.Board(engine.info_position)
            move = next(iter(board.legal_moves)).uci()
            seconds = elapsed(engine, board) if callable(elapsed) else elapsed
            engine.search.set_result((move, 100.0 + seconds, None))

    monkeypatch.setattr(UciEngine, 'send', send)
    return sent


@pytest.mark.parametrize('budget,elapsed,accepted', [
    # Actual pre-move clock and elapsed time in KO game 29, ply 200.
    (-0.048024300042015966, 0.004765099998621736, False),
    (-0.03, 0.01, True),
    (-0.03, 0.03, False),
    (0.01, 0.04, True),
    (None, 0.4, True),  # Pure node/depth controls remain clock-free.
])
def test_reply_uses_remaining_tolerance(monkeypatch, budget, elapsed, accepted):
    async def run():
        simulated_reply(monkeypatch, elapsed)
        engine = UciEngine({}, DEFAULTS)
        if accepted:
            move, _, _ = await engine.play(chess.Board(), 'go nodes 100', budget)
            assert move in chess.Board().legal_moves
        else:
            with pytest.raises(EngineFailure) as exc:
                await engine.play(chess.Board(), 'go wtime 1 btime 1000', budget)
            assert exc.value.reason == 'timeout'
    asyncio.run(run())


@pytest.mark.parametrize('ponder', [False, True])
def test_exhausted_tolerance_cannot_start_or_hit_search(monkeypatch, ponder):
    async def run():
        sent = simulated_reply(monkeypatch, 0)
        engine = UciEngine({}, DEFAULTS)
        engine.pondering = ponder
        engine.ponder_position = chess.STARTING_FEN
        with pytest.raises(EngineFailure) as exc:
            await engine.play(chess.Board(), 'go wtime 1 btime 1000', -0.05)
        assert exc.value.reason == 'timeout'
        assert 'before search' in str(exc.value)
        assert not sent
    asyncio.run(run())


def test_wait_watchdog_uses_only_unspent_tolerance(monkeypatch):
    async def run():
        async def send(engine, command):
            # The peer never replies: this checks the wait deadline itself,
            # independently of a bestmove timestamp arriving after the limit.
            pass
        observed = []
        from arena.uci import search_result
        async def wait(future, started, timeout):
            observed.append(timeout)
            return await search_result(future, started, timeout)
        monkeypatch.setattr(UciEngine, 'send', send)
        monkeypatch.setattr('arena.uci.search_result', wait)
        engine = UciEngine({}, DEFAULTS)
        with pytest.raises(EngineFailure) as exc:
            await engine.play(chess.Board(), 'go wtime 1 btime 1000', -.03)
        assert exc.value.reason == 'timeout'
        assert observed == pytest.approx([.02])
    asyncio.run(run())


@pytest.mark.parametrize('control', [
    {'kind': 'sudden_death', 'seconds': .01},
    {'kind': 'fischer', 'seconds': .01, 'increment': 0},
    {'kind': 'staged', 'stages': [{'seconds': .01, 'moves': 0}]},
])
def test_runner_cannot_renew_tolerance_after_zero(monkeypatch, tmp_path, control):
    async def run():
        # White spends 20 + 20 + 30 ms. Its 10 ms clock plus 50 ms
        # tolerance must reject the third move, even though each is <50 ms.
        searches = {'white': 0, 'black': 0}
        def elapsed(engine, board):
            side = 'white' if board.turn else 'black'
            searches[side] += 1
            return (.03 if searches[side] == 3 else .02) if board.turn else .001
        simulated_reply(monkeypatch, elapsed)
        async def start(engine):
            engine.identity = {'name': engine.profile['name']}
        monkeypatch.setattr(UciEngine, 'start', start)
        db = await Database().open(tmp_path)
        runner = Runner(db)
        try:
            profiles = [{'name': name, 'path': 'simulated-clock-peer',
                         'time_control': tc} for name, tc in [
                             ('White', control),
                             ('Black', {'kind': 'sudden_death', 'seconds': 10})]]
            t = await db.call('create_tournament', 'Cumulative tolerance', profiles,
                              {'cycles': 1, 'paired': False, 'max_plies': 6, 'tolerance': .05})
            await db.call('set_state', t['id'], 'running')
            await db.call('fill_queue', t['id'], 1)
            g = await db.call('claim', t['id'])
            runner.live[g['aid']] = {'tid': t['id'], 'game': g['id']}
            await runner._game(g, t)
            a = await db.call('one', 'SELECT * FROM attempts WHERE id=?', (g['aid'],))
            assert a['result'] == '0-1' and a['reason'] == 'timeout', a['detail']
            assert searches['white'] == 3
            moves = await db.call('rows', 'SELECT * FROM moves WHERE aid=? ORDER BY ply', (g['aid'],))
            assert len(moves) == 4
            assert json.loads(moves[-1]['clocks'])['white']['remaining'] == pytest.approx(-.03)
        finally:
            await runner.close()
    asyncio.run(run())


def test_increment_stage_bonus_and_delay_replenish_actual_budget():
    fischer = Clock(TimeControl.parse({'kind': 'fischer', 'seconds': .01, 'increment': .1}))
    fischer.consume(.02)
    assert fischer.budget == pytest.approx(.09)
    staged = Clock(TimeControl.parse({'kind': 'staged', 'stages': [
        {'seconds': .01, 'moves': 1}, {'seconds': 1, 'moves': 0}]}))
    staged.consume(.02)
    assert staged.budget == pytest.approx(.99)
    for kind in ('delay', 'bronstein'):
        delay = Clock(TimeControl.parse({'kind': kind, 'seconds': .01, 'delay': .1}))
        delay.consume(.12)
        assert delay.remaining == pytest.approx(-.01)
        assert delay.budget == pytest.approx(.09)
    nodes = Clock(TimeControl.parse({'kind': 'nodes', 'nodes': 777}))
    assert nodes.budget is None and go_command(nodes, nodes, nodes) == 'go nodes 777'
