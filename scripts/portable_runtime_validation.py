"""Exercise the portable build without development runtimes on its search path.

This is environment isolation on the development host, not a clean Windows VM.
The optional --keep-open allows follow-up visual acceptance of the same data.
"""
import argparse
import io
import json
import os
from pathlib import Path
import subprocess
import time
import urllib.error
import urllib.request

import chess
import chess.pgn
import psutil

ROOT = Path(__file__).resolve().parent.parent
parser = argparse.ArgumentParser()
parser.add_argument('--keep-open', action='store_true')
args = parser.parse_args()
package = ROOT / 'release' / 'EngineArena'
data = ROOT / 'test-output' / 'portable-isolated'
if data.exists():
    raise RuntimeError('Preserve prior evidence; choose a fresh validation directory.')
data.mkdir(parents=True)
work = data / 'unrelated-working-directory'
work.mkdir()
environment = os.environ.copy()
environment.update(PATH=str(Path(environment['SYSTEMROOT']) / 'System32'),
                   PYTHONHOME=str(work / 'no-python'), PYTHONPATH='',
                   DOTNET_ROOT=str(work / 'no-dotnet'), DOTNET_MULTILEVEL_LOOKUP='0')
app = subprocess.Popen([str(package / 'EngineArena.exe'), '--data', str(data)],
                       cwd=work, env=environment, creationflags=subprocess.CREATE_NO_WINDOW)
info = None


def api(path, body=None):
    request = urllib.request.Request(
        f"http://127.0.0.1:{info['port']}/api/{path}",
        data=json.dumps(body).encode() if body is not None else None,
        headers={'X-Arena-Token': info['token'], 'Content-Type': 'application/json'})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


success = False
try:
    deadline = time.monotonic() + 45
    while time.monotonic() < deadline:
        try:
            info = json.loads((data / 'worker-ready.json').read_text())
            api('status')
            break
        except (OSError, ValueError, urllib.error.URLError):
            assert app.poll() is None, 'Portable application exited during startup'
            time.sleep(.1)
    else:
        raise AssertionError('Portable application did not become ready')
    worker = psutil.Process(info['pid'])
    runtime_paths = {}
    for label, process, dll in [('dotnet', psutil.Process(app.pid), 'coreclr.dll'),
                                ('python', worker, 'python312.dll')]:
        paths = [Path(m.path).resolve() for m in process.memory_maps()
                 if Path(m.path).name.casefold() == dll]
        assert len(paths) == 1 and paths[0].is_relative_to(package.resolve()), (label, paths)
        runtime_paths[label] = str(paths[0].relative_to(package))
    profiles = []
    source = json.loads((ROOT / 'test-output' / 'real-validation' / 'report.json').read_text())
    for profile in source['engines']:
        profiles.append(api('profiles', {'path': profile['path'], 'threads': 1,
                                         'hash': 32, 'discover': True}))
    board = chess.Board()
    for san in ('e4', 'e5', 'Nf3', 'Nc6', 'd4'):
        board.push_san(san)
    tournament = api('tournaments', {
        'name': 'Portable isolated runtime and black-start replay',
        'profiles': [p['id'] for p in profiles],
        'openings': [{'fen': board.fen(), 'name': 'Scotch, Black to move 3'}],
        'settings': {'cycles': 1, 'concurrency': 2, 'max_plies': 16,
                     'time_control': {'kind': 'nodes', 'nodes': 2000}}})
    tid = tournament['id']
    api(f'tournaments/{tid}/action', {'action': 'start'})
    deadline = time.monotonic() + 45
    while time.monotonic() < deadline:
        snapshot = api(f'tournaments/{tid}')
        if snapshot['state'] == 'completed':
            break
        time.sleep(.1)
    assert snapshot['official_games'] == 2 and snapshot['complete_pairs'] == 1
    ids = []
    stream = io.StringIO((data / 'games.pgn').read_text(encoding='utf-8'))
    while game := chess.pgn.read_game(stream):
        assert not game.errors and game.headers['FEN'] == board.fen()
        assert len(list(game.mainline_moves())) == 16
        ids.append(game.headers['AttemptId'])
    assert len(ids) == len(set(ids)) == 2
    report = {'development_runtime_path_removed': True, 'clean_machine': False,
              'unrelated_working_directory': True, 'bundled_runtime_paths': runtime_paths,
              'engine_discovery': [p['identity'] for p in profiles],
              'completed_games': 2, 'complete_pairs': 1, 'pgn_parse_errors': 0,
              'pgn_duplicates': 0, 'opening_fen': board.fen(), 'tournament': tid}
    (ROOT / 'test-output' / 'portable-runtime-report.json').write_text(
        json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report), flush=True)
    success = True
finally:
    if not (success and args.keep_open):
        if info and app.poll() is None:
            api('shutdown', {})
            psutil.Process(info['pid']).wait(60)
        if app.poll() is None:
            app.terminate()
            app.wait(10)
