"""Isolated, synthetic design fixture. Does not launch engines or access user data."""
import asyncio
import contextlib
import json
from pathlib import Path
import sys
import time

import chess
from aiohttp import web

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from arena.server import create_app
from arena.store import Store
from arena.search_history import SearchHistory


async def main():
    folder = ROOT / 'test-output' / ('design-ui-' + time.strftime('%Y%m%d-%H%M%S'))
    s = Store(folder)
    profiles = [s.save_profile({'name': name, 'path': 'synthetic-review.exe', 'threads': 1, 'hash': 256})
                for name in ['Aurora 18', 'Citadel 8.0', 'Bishop 2.1', 'Horizon 16', 'Ember 4.6', 'Falcon 9', 'Granite 3.5', 'Vesper 1.2']]
    t = s.create_tournament('Engine comparison · synthetic design review', profiles,
                            {'format': 'round_robin', 'cycles': 20, 'concurrency': 8,
                             'tc': {'kind': 'fischer', 'seconds': 180, 'increment': 2}})
    s.set_state(t['id'], 'running')
    s.fill_queue(t['id'], 200)
    for n in range(128):
        g = s.claim(t['id'])
        s.finish(g['aid'], ['1/2-1/2', '1-0', '1/2-1/2', '0-1', '1-0', '1/2-1/2', '1-0'][n % 7], 'fixture')
    s.set_state(t['id'], 'paused')
    s.close()
    app = await create_app(folder, 'design-review')
    app['stop'] = asyncio.Event()
    runner, db = app['runner'], app['db']
    runner.scheduler.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await runner.scheduler
    await db.call('set_state', t['id'], 'running')
    prefs = {'theme': 'dark', 'fontSize': 14, 'pieceSet': 'classic-sculpted', 'boardCount': 4, 'split': 63,
             'panels': {'focus': {'visible': True, 'height': 650}, 'search': {'visible': True, 'height': 620}},
             'evaluation': {'focus': True, 'live': False, 'width': 32, 'range': 5, 'scale': 'linear', 'source': 'active'}}
    await db.call('execute', 'INSERT OR REPLACE INTO preferences VALUES(?,?)', ('ui', json.dumps(prefs)))
    for i in range(8):
        g = await db.call('claim', t['id'])
        board = chess.Board()
        for san in ['e4', 'e5', 'Nf3', 'Nc6', 'Bb5', 'a6', 'Ba4', 'Nf6', 'O-O', 'Be7', 'Re1', 'b5'][:8 + i % 5]:
            board.push_san(san)
        side = 'white' if board.turn else 'black'
        h = SearchHistory()
        for n, move in enumerate(list(board.legal_moves)[:6]):
            h.record({'pv': move.uci(), 'depth': 18 + n, 'seldepth': 30 + n, 'time': 1000 + n * 330,
                      'nodes': 4800000 + n * 350000, 'nps': 2214350, 'cp': 32 + n * 3, 'hashfull': 182, 'tbhits': 0})
        runner.search_histories[g['aid']] = {side: h}
        runner.live[g['aid']] = {'tid': t['id'], 'game': g['id'], 'number': g['number'],
            'white': profiles[g['white']], 'black': profiles[g['black']], 'fen': board.fen(),
            'status': 'White thinking' if board.turn else 'Black thinking', 'ply': board.ply(),
            'last_move': board.peek().uci(), 'san': 'Re1', 'clock_active': side, 'info_side': side,
            'info': h.current['info'], 'search_started': time.monotonic(), 'last_move_seconds': {},
            'clocks': {color: {'control': {'kind': 'fischer', 'seconds': 180, 'increment': 2}, 'remaining': 162.5 + i * 2} for color in ['white', 'black']},
            'searches': {side: {'ply': board.ply(), 'move_number': board.fullmove_number, 'complete': False,
                               'info': h.current['info'], 'history_revision': h.revision}}}
    server = web.AppRunner(app)
    await server.setup()
    site = web.TCPSite(server, '127.0.0.1', 0)
    await site.start()
    ready = {'url': f'http://127.0.0.1:{site._server.sockets[0].getsockname()[1]}/?token=design-review',
             'token': 'design-review', 'folder': str(folder), 'tid': t['id']}
    (ROOT / 'test-output/design-ready.json').write_text(json.dumps(ready), encoding='utf-8')
    print(json.dumps(ready), flush=True)
    try:
        await app['stop'].wait()
    finally:
        runner.live.clear()
        runner.search_histories.clear()
        await server.cleanup()


if __name__ == '__main__':
    asyncio.run(main())
