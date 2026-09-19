"""Isolated GUI load fixture: 128 synthetic live games, no engine processes.

Use count.json in the fixture directory to test games disappearing. This script
serves the real UI/API and preferences, but never records synthetic game results.
"""
import asyncio
import json
import os
from pathlib import Path
import secrets
import sys
import time

import chess
from aiohttp import web

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from arena.server import create_app


async def main():
    folder = ROOT / 'test-output' / 'live-boards-ui'
    folder.mkdir(exist_ok=True)
    token = secrets.token_urlsafe(32)
    app = await create_app(folder, token)
    db, runner = app['db'], app['runner']
    runner.scheduler.cancel()
    await asyncio.gather(runner.scheduler, return_exceptions=True)
    existing = await db.call('rows', 'SELECT id FROM tournaments')
    if not existing:
        profiles = [await db.call('save_profile', {'name': f'Synthetic engine {s}', 'path': sys.executable, 'threads': 1, 'hash': 1}) for s in ('A', 'B')]
        t = await db.call('create_tournament', 'UI fixture — 128 synthetic live games', profiles, {'cycles': 64})
        prefs = {'fontSize': 16, 'boardCount': 32, 'panels': {'live': {'column': 'right', 'order': 0, 'height': 9000}, 'focus': {'visible': False}, 'search': {'visible': False}}}
        await db.call('execute', 'INSERT OR REPLACE INTO preferences VALUES(?,?)', ('ui', json.dumps(prefs)))
    else:
        t = await db.call('tournament', existing[0]['id'])
    await db.call('set_state', t['id'], 'running')
    await db.call('fill_queue', t['id'], 128)
    await db.call('set_state', t['id'], 'paused')
    games = await db.call('rows', 'SELECT id,number FROM games WHERE tid=? ORDER BY number', (t['id'],))
    assert len(games) == 128
    positions = []
    board = chess.Board()
    for move in ('e2e4', 'e7e5', 'g1f3', 'b8c6'):
        board.push_uci(move)
        positions.append((board.fen(), move))
    (folder / 'count.json').write_text('128')
    original_status = runner.status

    def status():
        count = json.loads((folder / 'count.json').read_text())
        tick = int(time.monotonic() / 3)
        live = []
        for i, game in enumerate(games[:count]):
            fen, move = positions[(tick + i) % len(positions)]
            side = 'white' if fen.split()[1] == 'w' else 'black'
            clocks = {s: {'control': {'kind': 'fischer', 'seconds': 180, 'increment': 2}, 'remaining': 120 + i, 'stage': 0} for s in ('white', 'black')}
            live.append({'tid': t['id'], 'game': game['id'], 'number': i, 'fen': fen, 'last_move': move, 'white': {'name': f'Synthetic A {i+1}'}, 'black': {'name': f'Synthetic B {i+1}'}, 'ply': tick, 'status': side.title() + ' thinking', 'clock_active': side, 'search_elapsed': time.monotonic() % 3, 'clocks': clocks})
        return original_status() | {'live': live, 'active_games': count}

    runner.status = status
    app['stop'] = asyncio.Event()
    server = web.AppRunner(app)
    await server.setup()
    site = web.TCPSite(server, '127.0.0.1', 0)
    await site.start()
    info = {'port': site._server.sockets[0].getsockname()[1], 'token': token, 'pid': os.getpid()}
    (folder / 'worker-ready.json').write_text(json.dumps(info))
    print(json.dumps(info), flush=True)
    try:
        await app['stop'].wait()
    finally:
        await server.cleanup()


if __name__ == '__main__':
    asyncio.run(main())
