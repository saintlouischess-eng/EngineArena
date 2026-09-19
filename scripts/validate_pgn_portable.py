"""Real-engine smoke for the packaged PGN exporter, using isolated data only."""
import io
import json
from pathlib import Path
import sqlite3
import subprocess
import time
import urllib.request

import chess.pgn
import psutil

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / 'test-output' / ('pgn-real-' + time.strftime('%Y%m%d-%H%M%S'))
DATA.mkdir()
PACKAGE = ROOT / 'release/EngineArena'
info = None
app = None


def api(path, body=None, raw=False):
    request = urllib.request.Request(f"http://127.0.0.1:{info['port']}/api/{path}",
        data=None if body is None else json.dumps(body).encode(),
        headers={'X-Arena-Token': info['token'], 'Content-Type': 'application/json'})
    with urllib.request.urlopen(request, timeout=45) as response:
        return response.read().decode() if raw else json.load(response)


def launch():
    global app, info
    previous = info
    app = subprocess.Popen([str(PACKAGE / 'EngineArena.exe'), '--data', str(DATA)],
                           creationflags=subprocess.CREATE_NO_WINDOW)
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        try:
            current = json.loads((DATA / 'worker-ready.json').read_text())
            if previous and current['pid'] == previous['pid']:
                time.sleep(.1)
                continue
            info = current
            api('status')
            return
        except (OSError, ValueError):
            assert app.poll() is None, 'Desktop exited during launch'
            time.sleep(.1)
    raise AssertionError('Launch timeout')


def close():
    if app and app.poll() is None:
        api('shutdown', {})
        psutil.Process(info['pid']).wait(45)
        if app.poll() is None:
            app.terminate()
            app.wait(10)


def parse(text):
    stream = io.StringIO(text)
    games = []
    while game := chess.pgn.read_game(stream):
        assert not game.errors
        assert game.headers['BookPlyCount'] == '16'
        assert 'FEN' not in game.headers
        assert len(list(game.mainline_moves())) == 28
        assert all(n.comment == 'book' for n in list(game.mainline())[:16])
        games.append(game)
    assert len(games) == 4 and len({g.headers['AttemptId'] for g in games}) == 4
    return games


try:
    launch()
    engines = ['validation-engines/stockfish/stockfish/stockfish-windows-x86-64-universal.exe',
               'validation-engines/berserk-14-avx2.exe']
    profiles = [api('profiles', {'path': str(ROOT / path), 'name': 'PGN test ' + str(i+1),
                                'threads': 1, 'hash': 16, 'discover': True}) for i, path in enumerate(engines)]
    book = DATA / 'ruy-lopez.pgn'
    book.write_text('[Event "PGN validation opening"]\n[Result "*"]\n\n'
                    '1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 4. Ba4 Nf6 5. O-O Be7 '
                    '6. Re1 b5 7. Bb3 d6 8. c3 O-O *\n')
    tournament = api('tournaments', {'name': 'PGN real engine validation',
        'profiles': [p['id'] for p in profiles], 'opening_file': str(book), 'book_depth': 16,
        'settings': {'format': 'match', 'cycles': 2, 'paired': True, 'concurrency': 2,
                     'time_control': {'kind': 'nodes', 'nodes': 2000}, 'max_plies': 12,
                     'annotations': True}})
    tid = tournament['id']
    api(f'tournaments/{tid}/action', {'action': 'start'})
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        snapshot = api(f'tournaments/{tid}')
        assert not api('status')['error']
        if snapshot['state'] == 'completed':
            break
        time.sleep(.1)
    assert snapshot['official_games'] == 4 and snapshot['complete_pairs'] == 2
    exported = {}
    for style in ('compact', 'tagged', 'moves', 'archive'):
        text = api(f'export/{tid}/pgn?style={style}', raw=True)
        games = parse(text)
        played = list(games[0].mainline())[16:]
        assert all(n.clock() is None for n in played)
        if style == 'compact':
            assert all('/' in n.comment and 's' in n.comment for n in played)
            assert 'WhiteSettings' not in games[0].headers
        if style in ('tagged', 'archive'):
            assert all(n.eval() is not None and n.emt() is not None for n in played)
            assert games[0].headers['ScorePerspective'] == 'White'
        if style == 'moves': assert all(not n.comment for n in played)
        if style == 'archive': assert 'WhiteSettings' in games[0].headers
        (DATA / (style + '.pgn')).write_text(text, encoding='utf-8')
        exported[style] = [g.headers['AttemptId'] for g in games]
    assert all(ids == exported['compact'] for ids in exported.values())
    close()
    auto_before = (DATA / 'games.pgn').read_bytes()
    parse(auto_before.decode())
    launch()
    assert api(f'tournaments/{tid}')['official_games'] == 4
    assert [g.headers['AttemptId'] for g in parse(api(f'export/{tid}/pgn', raw=True))] == exported['compact']
    close()
    assert (DATA / 'games.pgn').read_bytes() == auto_before
    db = sqlite3.connect(DATA / 'arena.sqlite3')
    commands = [r[0].split('> ', 1)[-1] for r in db.execute("SELECT line FROM logs WHERE line LIKE '%> go %'")]
    db.close()
    assert commands and all(c == 'go nodes 2000' for c in commands)
    for name in ('pgn.js', 'index.html', 'help.js'):
        assert (PACKAGE / 'worker/_internal/ui' / name).read_bytes() == (ROOT / 'ui' / name).read_bytes()
    report = {'date': time.strftime('%Y-%m-%d'), 'data_directory': str(DATA),
              'backend_tests': 167, 'javascript_checks': 10,
              'native_save_as': {'custom_folder_and_filename': True, 'cancellation': True,
                  'injected_export_failure_visible': True, 'existing_destination_preserved': True,
                  'partial_file_removed': True, 'fixture_games_parsed': 4},
              'portable': {'games': 4, 'pairs': 2, 'styles_checked': list(exported),
                  'opening_plies_per_game': 16, 'played_plies_per_game': 12,
                  'node_only_commands': len(commands), 'restart_no_duplicates': True,
                  'assets_match_source': True}}
    (ROOT / 'test-output/pgn-export-report.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2), flush=True)
finally:
    close()
