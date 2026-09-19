"""Real-engine queued comparisons across every supported control and handicaps."""
import asyncio
import copy
import io
import json
from pathlib import Path
import re
import sys
import time

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import chess.pgn
from arena.runner import Database, Runner
from arena.store import DEFAULTS
from arena.uci import discover


async def main():
    folder = ROOT / 'test-output' / 'controls-real'
    if (folder / 'arena.sqlite3').exists():
        raise RuntimeError('Preserve the previous evidence; select a fresh validation folder.')
    profiles = []
    for path in (next((ROOT/'validation-engines/stockfish').glob('**/*.exe')),
                 ROOT/'validation-engines/berserk-14-avx2.exe'):
        profiles.append(await discover({'path': str(path), 'threads': 1, 'hash': 32}, DEFAULTS))
    controls = [
        ('sudden_death', {'kind': 'sudden_death', 'seconds': 3}),
        ('fischer', {'kind': 'fischer', 'seconds': 2, 'increment': .03}),
        ('delay', {'kind': 'delay', 'seconds': 2, 'delay': .05}),
        ('bronstein', {'kind': 'bronstein', 'seconds': 2, 'delay': .05}),
        ('staged', {'kind': 'staged', 'stages': [{'moves': 2, 'seconds': .5, 'increment': .01}, {'moves': 0, 'seconds': 2, 'increment': .02}]}),
        ('repeating', {'kind': 'staged', 'stages': [{'moves': 2, 'seconds': .5}, {'moves': 2, 'seconds': .5}], 'repeat': True}),
        ('movetime', {'kind': 'movetime', 'seconds': .025}),
        ('depth', {'kind': 'depth', 'depth': 6}),
        ('nodes', {'kind': 'nodes', 'nodes': 3000}),
        ('handicap', {'kind': 'fischer', 'seconds': 2, 'increment': .03}),
    ]
    db = await Database().open(folder); runner = Runner(db)
    report = {'engines': [p['identity'] for p in profiles], 'runs': []}
    queued = []; started = time.perf_counter()
    try:
        for name, control in controls:
            entrants = copy.deepcopy(profiles)
            if name == 'handicap':
                entrants[0]['time_control'] = {'kind': 'nodes', 'nodes': 1500}
                entrants[1]['time_control'] = {'kind': 'movetime', 'seconds': .025}
            t = await db.call('create_tournament', 'Real control '+name, entrants, {
                'cycles': 2, 'concurrency': 4, 'max_plies': 16,
                'time_control': control, 'hang_timeout': 10, 'tolerance': .2})
            await db.call('set_state', t['id'], 'running'); queued.append((name, t))
        await runner.start()
        while time.perf_counter()-started < 180:
            if runner.error: raise AssertionError(runner.error)
            states = await db.call('rows', 'SELECT state FROM tournaments')
            if all(t['state']=='completed' for t in states): break
            await asyncio.sleep(.2)
        assert all(t['state']=='completed' for t in states), states
        for name, t in queued:
            snapshot = await db.call('snapshot', t['id'])
            games = (await db.call('games', t['id']))['items']
            commands = []; stage_changes = 0; moves = 0
            for g in games:
                detail = await db.call('game_detail', g['id'])
                attempt = detail['attempts'][0]
                assert attempt['reason']=='max_plies_adjudication', (name, attempt['reason'])
                assert len(attempt['moves'])==16
                moves += len(attempt['moves'])
                lines = await db.call('rows', 'SELECT line FROM logs WHERE aid=? ORDER BY id', (attempt['id'],))
                go = [l['line'][2:] for l in lines if l['line'].startswith('> go ')]
                assert len(go)==16, (name, len(go))
                commands.extend(go)
                clocks = [json.loads(m['clocks']) for m in attempt['moves']]
                if name in ('staged', 'repeating'):
                    assert clocks[3]['white']['stage']==clocks[3]['black']['stage']==1
                    assert 'movestogo 2' in go[0] and 'movestogo 1' in go[2]
                    if name=='repeating':
                        assert clocks[7]['white']['moves']==clocks[7]['black']['moves']==0
                        assert 'movestogo 2' in go[8]
                    else: assert 'movestogo' not in go[4]
                    stage_changes += 2
                if name in ('nodes', 'depth', 'movetime', 'handicap'):
                    assert all(c[color]['remaining'] is None for c in clocks for color in ('white','black'))
                    assert all(not re.search(r'\b[wb](?:time|inc)\b', cmd) for cmd in go)
                if name=='nodes': assert set(go)=={'go nodes 3000'}
                if name=='handicap': assert set(go)=={'go nodes 1500','go movetime 25'}
            stream = io.StringIO(await db.call('export_official', t['id'])); ids=[]
            while game := chess.pgn.read_game(stream):
                assert not game.errors and len(list(game.mainline_moves()))==16
                for tag in ('WhiteEngine','BlackEngine','TournamentSettings','Termination','OpeningPair'):
                    assert game.headers[tag]
                ids.append(game.headers['AttemptId'])
            assert len(ids)==len(set(ids))==snapshot['official_games']==4
            assert snapshot['complete_pairs']==2
            report['runs'].append({'control':name, 'settings':t['settings']['time_control'],
                'games':4, 'pairs':2, 'moves':moves, 'clock_stage_transitions':stage_changes,
                'wire_commands':sorted(set(commands)), 'pgn_errors':0})
        report['seconds']=time.perf_counter()-started
        report['peak_concurrency']=runner.max_active
    finally:
        await runner.close()
    (ROOT/'test-output/controls-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({'controls':len(report['runs']),'games':sum(r['games'] for r in report['runs']),
                      'seconds':report['seconds'],'peak_concurrency':report['peak_concurrency']}))


if __name__=='__main__': asyncio.run(main())
