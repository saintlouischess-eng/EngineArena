"""Short real-engine check in an explicitly selected installed-beta test workspace."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import sqlite3
import time
import urllib.request

import chess.pgn

ROOT = Path(__file__).resolve().parent.parent
parser = argparse.ArgumentParser()
parser.add_argument('--ready', type=Path, required=True)
parser.add_argument('--check-restart', action='store_true')
args = parser.parse_args()
ready = args.ready.resolve()
assert ready.is_relative_to(ROOT / 'test-output'), 'Only isolated test-output workspaces are allowed'
info = json.loads(ready.read_text())
report_path = ROOT / 'test-output/installer-games-report.json'


def request(path, body=None):
    req = urllib.request.Request(
        f"http://127.0.0.1:{info['port']}/api/" + path,
        None if body is None else json.dumps(body).encode(),
        {'X-Arena-Token': info['token'], 'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=30) as response:
        return response.read()


def api(path, body=None):
    return json.loads(request(path, body))


if args.check_restart:
    report = json.loads(report_path.read_text())
    assert api('tournaments/' + report['tournament'])['official_games'] == 4
    assert hashlib.sha256((ready.parent / 'games.pgn').read_bytes()).hexdigest() == report['pgn_sha256']
    assert api('preferences')['confidence'] == 99
    report['restart_retained_results_pgn_preferences'] = True
    report_path.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print('Installed beta restart retained all results, exact PGN bytes and preferences.')
    raise SystemExit

profiles = []
for name, relative in [('Stockfish', 'validation-engines/stockfish/stockfish/stockfish-windows-x86-64-universal.exe'),
                       ('Berserk', 'validation-engines/berserk-14-avx2.exe')]:
    profiles.append(api('profiles', {'name': name + ' installer test', 'path': str(ROOT / relative),
                                     'threads': 1, 'hash': 16, 'discover': True})['id'])
api('preferences', {'confidence': 99})
tournament = api('tournaments', {'name': 'Installed beta acceptance', 'profiles': profiles,
    'settings': {'format': 'match', 'cycles': 2, 'concurrency': 2,
                 'time_control': {'kind': 'nodes', 'nodes': 150000}}})
tid = tournament['id']
api(f'tournaments/{tid}/action', {'action': 'start'})
start = time.monotonic()
while time.monotonic() - start < 180:
    snapshot = api('tournaments/' + tid)
    if snapshot['state'] == 'completed':
        break
    time.sleep(.3)
assert snapshot['official_games'] == 4 and snapshot['state'] == 'completed'
for style in ('compact', 'tagged', 'moves', 'archive'):
    stream = io.StringIO(request(f'export/{tid}/pgn?style={style}').decode())
    attempts = []
    while game := chess.pgn.read_game(stream):
        assert not game.errors
        board = game.board()
        for move in game.mainline_moves():
            assert move in board.legal_moves
            board.push(move)
        attempts.append(game.headers['AttemptId'])
    assert len(attempts) == len(set(attempts)) == 4
with sqlite3.connect(ready.parent / 'arena.sqlite3') as db:
    commands = [line for (line,) in db.execute('SELECT line FROM logs') if '> go ' in line]
    assert commands and all(line.split('> ', 1)[1] == 'go nodes 150000' for line in commands)
report = {'tournament': tid, 'games': 4, 'pairs': 2, 'max_concurrency': api('status')['max_active_games'],
          'seconds': time.monotonic() - start, 'pure_node_commands': len(commands),
          'four_pgn_formats_legal_unique': True,
          'pgn_sha256': hashlib.sha256((ready.parent / 'games.pgn').read_bytes()).hexdigest(),
          'scope': 'Installed beta in isolated development-host workspace; not a clean-laptop claim'}
report_path.write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report, indent=2))
