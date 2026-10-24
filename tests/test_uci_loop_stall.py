"""On-time pipe replies must survive a stalled application loop, not late moves."""
import asyncio
from pathlib import Path
import sys
import time

import chess
import pytest

from arena.engine_process import EngineProcess
from arena.store import DEFAULTS
from arena.uci import EngineFailure, UciEngine


def peer(wait=.1, **settings):
    return UciEngine({'path': sys.executable, 'name': 'Receipt fixture', 'hash': 1,
                     'args': [str(Path(__file__).with_name('fault_engine.py')), '--wait', str(wait)]},
                     DEFAULTS | {'tolerance': 0, 'startup_timeout': 15} | settings)


@pytest.mark.parametrize('count', [1, 3])
def test_on_time_replies_survive_application_loop_stall(count):
    async def run():
        engines = [peer() for _ in range(count)]
        try:
            for engine in engines:
                await engine.start()
            tasks = [asyncio.create_task(e.play(chess.Board(), 'go wtime 600 btime 600', .6)) for e in engines]
            await asyncio.sleep(.04)
            time.sleep(1.0)  # Deliberate stall in THIS disposable test process only.
            for engine, task in zip(engines, tasks):
                move, elapsed, info = await task
                assert move in chess.Board().legal_moves
                assert .07 <= elapsed < .6
                assert info['depth'] == 7  # Pending telemetry was parsed before return.
                assert any('# Clock receipt:' in line for line in engine.log)
                # A new search must not reuse the previous receipt.
                _, next_elapsed, _ = await engine.play(chess.Board(), 'go wtime 600 btime 600', .6)
                assert .07 <= next_elapsed < .6
        finally:
            for engine in engines:
                await engine.close()
                if engine.process:
                    assert not engine.process.stdout.thread.is_alive()
                    assert not engine.process.stderr.thread.is_alive()
    asyncio.run(run())


def test_late_reply_still_loses_after_same_loop_stall():
    async def run():
        engine = peer(wait=.8)
        try:
            await engine.start()
            task = asyncio.create_task(engine.play(chess.Board(), 'go wtime 300 btime 300', .3))
            await asyncio.sleep(.04)
            time.sleep(1.1)
            with pytest.raises(EngineFailure) as failure:
                await task
            assert failure.value.reason == 'timeout'
            assert 'Move took' in str(failure.value)
        finally:
            await engine.close()
    asyncio.run(run())


def test_slow_telemetry_callback_does_not_charge_engine_clock():
    async def run():
        engine = peer()
        try:
            await engine.start()
            engine.info_hook = lambda info: time.sleep(1.0)
            move, elapsed, _ = await engine.play(chess.Board(), 'go wtime 600 btime 600', .6)
            assert move in chess.Board().legal_moves and .07 <= elapsed < .6
        finally:
            await engine.close()
    asyncio.run(run())


def test_ponderhit_receipt_survives_stall():
    async def run():
        engine = peer(ponder=True)
        engine.profile['args'] += ['--mode', 'ponder']
        try:
            await engine.start()
            board = chess.Board()
            move, _, _ = await engine.play(board, 'go wtime 600 btime 600', .6)
            board.push(move)
            predicted = engine.ponder_candidate
            await engine.begin_ponder(board, 'go wtime 600 btime 600')
            board.push_uci(predicted)
            task = asyncio.create_task(engine.play(board, 'go wtime 600 btime 600', .6))
            await asyncio.sleep(.04)
            time.sleep(1.0)
            move, elapsed, _ = await task
            assert move in board.legal_moves and 0 <= elapsed < .6
        finally:
            await engine.close()
    asyncio.run(run())


@pytest.mark.parametrize('budget,reason', [(0.2, 'timeout'), (None, 'hang')])
def test_silent_engine_watchdogs_remain_effective(budget, reason):
    async def run():
        engine = peer(wait=3, hang_timeout=.35)
        try:
            await engine.start()
            with pytest.raises(EngineFailure) as failure:
                await engine.play(chess.Board(), 'go nodes 123', budget)
            assert failure.value.reason == reason
        finally:
            if engine.process:
                engine.process.kill()  # Only this fixture; avoids its deliberate sleep.
            await engine.close()
    asyncio.run(run())


def test_info_flood_is_bounded_and_cannot_hide_bestmove():
    async def run():
        code = "import sys,time;sys.stdin.readline();time.sleep(.05);print('info depth 1 nodes 1\\n'*15000,end='');print('bestmove e2e4',flush=True);sys.stdin.readline()"
        process = await EngineProcess.create(sys.executable, '-u', '-c', code)
        try:
            receipt = process.stdout.arm()
            process.stdin.write(b'go\n')
            await process.stdin.drain()
            time.sleep(.6)
            assert receipt.snapshot()[0] == 'e2e4'
            assert process.stdout.discarded_info > 0
            assert len(process.stdout._lines) <= process.stdout.MAX_LINES
            assert process.stdout._bytes <= process.stdout.MAX_BYTES
            for _ in range(process.stdout.MAX_LINES):
                line = await asyncio.wait_for(process.stdout.readline(), 2)
                if line.startswith(b'bestmove'):
                    assert line.received == receipt.snapshot()[1]
                    break
            else:
                pytest.fail('Bestmove was lost behind telemetry')
        finally:
            process.kill()
            await process.wait()
            await process.close_pipes()
    asyncio.run(run())
