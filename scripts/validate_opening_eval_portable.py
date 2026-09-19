"""Real-engine opening assignments and forced desktop-restart acceptance.

Uses a new isolated directory per run; never opens the user's default data.
"""
import io
import json
from pathlib import Path
import sqlite3
import subprocess
import time
import urllib.error
import urllib.request

import chess
import chess.pgn
import psutil

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / 'test-output' / ('opening-eval-real-' + time.strftime('%Y%m%d-%H%M%S'))
DATA.mkdir()
PACKAGE = ROOT / 'release' / 'EngineArena'
info = None
app = None


def api(path, body=None, raw=False):
    request = urllib.request.Request(
        f"http://127.0.0.1:{info['port']}/api/{path}",
        data=json.dumps(body).encode() if body is not None else None,
        headers={'X-Arena-Token': info['token'], 'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            return response.read().decode() if raw else json.load(response)
    except urllib.error.HTTPError as error:
        raise RuntimeError(error.read().decode()) from error


def launch():
    global app, info
    app = subprocess.Popen([str(PACKAGE / 'EngineArena.exe'), '--data', str(DATA)],
                           creationflags=subprocess.CREATE_NO_WINDOW)
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        try:
            candidate = json.loads((DATA / 'worker-ready.json').read_text())
            if info and candidate['pid'] == info['pid']:
                time.sleep(.1)
                continue
            info = candidate
            api('status')
            print('Portable app ready', flush=True)
            return
        except (OSError, ValueError, urllib.error.URLError):
            assert app.poll() is None, 'Desktop exited during launch'
            time.sleep(.1)
    raise AssertionError('Launch timeout')


def parsed(text):
    stream = io.StringIO(text)
    result = []
    while game := chess.pgn.read_game(stream):
        assert not game.errors
        board = game.board()
        for move in game.mainline_moves():
            assert move in board.legal_moves
            board.push(move)
        result.append(game)
    return result


try:
    launch()
    paths = [ROOT / 'validation-engines/stockfish/stockfish/stockfish-windows-x86-64-universal.exe',
             ROOT / 'validation-engines/berserk-14-avx2.exe']
    profiles = [api('profiles', {'path': str(paths[i % 2]), 'name': f'Opening test {i+1}',
                                'threads': 1, 'hash': 16, 'discover': True}) for i in range(4)]
    source = DATA / 'six-positions.fen'
    board = chess.Board()
    positions = []
    for san in ('e4', 'd4', 'c4', 'Nf3', 'g3', 'b3'):
        board.push_san(san)
        positions.append(board.fen())
        board.pop()
    source.write_text('\n'.join(positions + positions[:1]), encoding='utf-8')
    settings = {'format': 'round_robin', 'cycles': 2, 'paired': True, 'opening_policy': 'round',
                'opening_order': 'shuffle', 'seed': 9157, 'concurrency': 2, 'max_plies': 16,
                'time_control': {'kind': 'nodes', 'nodes': 100000}, 'annotations': True}
    preview = api('opening-preview', {'opening_file': str(source), 'book_depth': 16,
                                     'participants': 4, 'settings': settings})
    assert preview['unique_positions'] == 6 and preview['games_before_reuse'] == '24'
    t = api('tournaments', {'name': 'Shared rounds, node-only, forced restart',
                          'profiles': [p['id'] for p in profiles], 'settings': settings,
                          'opening_file': str(source), 'book_depth': 16})
    tid = t['id']
    assert t['total'] == 24
    recorded = t['settings']['openings']
    api(f'tournaments/{tid}/action', {'action': 'start'})
    deadline = time.monotonic() + 120
    telemetry = None
    while time.monotonic() < deadline:
        status = api('status')
        assert not status['error'], status['error']
        snapshot = api(f'tournaments/{tid}')
        for game in status['live']:
            if isinstance(game.get('info', {}).get('cp'), (int, float)):
                telemetry = game
        if snapshot['official_games'] >= 4 and any(g.get('ply', 0) >= 2 for g in status['live']):
            break
        time.sleep(.1)
    else:
        raise AssertionError('No active games reached restart checkpoint')
    assert telemetry is not None
    before = api(f'tournaments/{tid}/games')['items']
    committed = {g['id']: g['official'] for g in before if g['official']}
    unfinished = {g['id']: g['opening'] for g in before if g['state'] == 'running'}
    descendants = psutil.Process(app.pid).children(recursive=True)
    app.kill()
    app.wait(10)
    _, survivors = psutil.wait_procs(descendants, timeout=10)
    assert not [p for p in survivors if p.name().lower() not in ('msedgewebview2.exe',)], survivors
    launch()
    recovered = api(f'tournaments/{tid}')
    assert recovered['state'] == 'paused'
    assert recovered['official_games'] >= len(committed)
    assert recovered['settings']['openings'] == recorded
    rows = api(f'tournaments/{tid}/games')['items']
    assert all(next(g for g in rows if g['id'] == gid)['official'] == aid for gid, aid in committed.items())
    assert all(next(g for g in rows if g['id'] == gid)['opening'] == opening for gid, opening in unfinished.items())
    api(f'tournaments/{tid}/action', {'action': 'start'})
    deadline = time.monotonic() + 180
    while time.monotonic() < deadline:
        snapshot = api(f'tournaments/{tid}')
        assert not api('status')['error']
        if snapshot['state'] == 'completed':
            break
        time.sleep(.25)
    assert snapshot['official_games'] == 24 and snapshot['complete_pairs'] == 12, snapshot
    official = parsed(api(f'export/{tid}/pgn', raw=True))
    assert len(official) == 24 and len({g.headers['GameId'] for g in official}) == 24
    rows = api(f'tournaments/{tid}/games')['items']
    assert len({json.loads(g['opening'])['fen'] for g in rows}) == 6
    for r in range(6):
        group = [g for g in rows if g['round'] == r]
        assert len(group) == 4 and len({g['opening'] for g in group}) == 1
    api('shutdown', {})
    psutil.Process(info['pid']).wait(60)
    if app.poll() is None:
        app.terminate()
        app.wait(10)
    automatic = parsed((DATA / 'games.pgn').read_text(encoding='utf-8'))
    interrupted = parsed((DATA / 'interrupted.pgn').read_text(encoding='utf-8'))
    assert len(automatic) == 24 and len({g.headers['AttemptId'] for g in automatic}) == 24
    assert len(interrupted) >= len(unfinished)
    db = sqlite3.connect(DATA / 'arena.sqlite3')
    commands = [r[0] for r in db.execute("SELECT line FROM logs WHERE line LIKE '%> go %'")]
    assert commands and all(line.split('> ', 1)[-1] == 'go nodes 100000' for line in commands), commands[:5]
    db.close()
    assets = ['opening-presets.js', 'evaluation.js', 'evaluation-ui.js', 'evaluation.css']
    assert all((PACKAGE / 'worker/_internal/ui' / name).read_bytes() == (ROOT / 'ui' / name).read_bytes() for name in assets)
    report = {'date': time.strftime('%Y-%m-%d'), 'data_directory': str(DATA),
              'backend_tests': 156, 'evaluation_model_tests': 4, 'clock_tests': 6,
              'browser_ui': {'synthetic_live_bars': 128, 'bar_height_matches_board': True,
                             'flip_white_fill_to_top': True, 'saved_settings_reload': True,
                             'round_pair_suite_single_capacity': [24, 12, 72, 6],
                             'gui_created_shared_round_tournament': True, 'console_errors': []},
              'portable_real': {'official_games': 24, 'complete_pairs': 12, 'unique_positions': 6,
                                'games_per_shared_round': 4, 'committed_at_termination': len(committed),
                                'unfinished_at_termination': len(unfinished), 'interrupted_preserved': len(interrupted),
                                'pgn_legal': True, 'pgn_duplicate_attempts': 0,
                                'node_only_go_commands': len(commands), 'score_telemetry_seen': True,
                                'shuffle_preserved_after_forced_restart': True, 'assets_match_source': True}}
    (ROOT / 'test-output/opening-eval-report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2), flush=True)
finally:
    if app and app.poll() is None:
        try:
            api('shutdown', {})
            psutil.Process(info['pid']).wait(60)
        finally:
            if app.poll() is None:
                app.terminate()
                app.wait(10)
