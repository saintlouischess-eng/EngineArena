"""Completed-history storage benchmark; synthetic copies, not 50,000 engine games.

Uses real recorded move telemetry and engine profiles, 80 plies per game, full
annotated PGNs, and reversed-color pairs. Bulk fixture loading is deliberately
not reported as tournament throughput. Run before/after against the same data.
"""
import argparse
import asyncio
import json
import hashlib
import math
import os
from pathlib import Path
import sqlite3
import sys
import time

import psutil
import chess.pgn
import io
import re

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from arena.store import Store, encode
from arena.runner import Database
from arena.reports import opening_report
from arena.trends import tournament_series, _cache
from arena.pgn_export import OfficialPgnReader


def measure(fn, repeats=5):
    values = []
    for _ in range(repeats):
        start = time.perf_counter()
        fn()
        values.append(1000 * (time.perf_counter() - start))
    ordered = sorted(values)
    return {'median_ms': ordered[len(ordered)//2],
            'p95_ms': ordered[min(len(ordered)-1, math.ceil(.95*len(ordered))-1)],
            'samples_ms': values}


def seed(folder, target):
    s = Store(folder)
    try:
        t = s.one('SELECT id FROM tournaments ORDER BY created LIMIT 1')
        if not t:
            source = sqlite3.connect(ROOT/'test-output/graph-load/arena.sqlite3')
            source.row_factory = sqlite3.Row
            row = source.execute('''SELECT g.* FROM games g JOIN
                (SELECT aid FROM moves GROUP BY aid HAVING count(*)>=80 LIMIT 1) m
                ON m.aid=g.official''').fetchone()
            assert row
            profiles = [json.loads(source.execute('SELECT profile FROM participants WHERE tid=? AND slot=?',
                        (row['tid'], row[c])).fetchone()[0]) for c in ('white', 'black')]
            moves = source.execute('SELECT * FROM moves WHERE aid=? AND ply<=80 ORDER BY ply', (row['official'],)).fetchall()
            opening = json.loads(row['opening'])
            t = s.create_tournament('Synthetic completed-history scale fixture', profiles,
                  {'cycles': 100000, 'time_control': {'kind': 'nodes', 'nodes': 100000}, 'max_plies': 80}, [opening])
            tid = t['id']
            s.set_state(tid, 'running');s.fill_queue(tid, 2)
            for _ in range(2):
                g = s.claim(tid)
                s.move_batch([(g['aid'], m['ply'], m['uci'], m['san'], m['fen'], m['elapsed'],
                              json.loads(m['clocks']), json.loads(m['info']), []) for m in moves])
                s.finish(g['aid'], '1/2-1/2', 'max_plies_adjudication', 'Synthetic benchmark fixture')
            s.set_state(tid, 'paused');s.export_pending();source.close()
        tid = t['id']
        templates = s.rows('SELECT g.*,a.started,a.ended,a.clocks,a.identity,a.detail,o.pgn FROM games g '
                          'JOIN attempts a ON a.id=g.official JOIN outbox o ON o.aid=a.id '
                          'WHERE g.tid=? ORDER BY g.number LIMIT 2', (tid,))
        moves = [s.rows('SELECT * FROM moves WHERE aid=? ORDER BY ply', (r['official'],)) for r in templates]
        count = s.one('SELECT count(*) n FROM games WHERE tid=?', (tid,))['n']
        started = time.perf_counter()
        for begin in range(count, target, 256):
            end = min(target, begin+256)
            games = [];attempts = [];plies = [];outbox = []
            for n in range(begin, end):
                r = templates[n % 2];gid = '1'*24+f'{n:08x}';aid = '2'*24+f'{n:08x}'
                games.append((gid, tid, n, n//2, n%2, 0, 1, n%2, 1-n%2, n//2, r['opening'], 'completed', 'original', aid, 0))
                attempts.append((aid, gid, 1, 'original', r['started']+n, r['ended']+n,
                                 '1/2-1/2', 'max_plies_adjudication', r['detail'], r['clocks'], r['identity']))
                plies.extend((aid, m['ply'], m['uci'], m['san'], m['fen'], m['elapsed'], m['clocks'], m['info']) for m in moves[n%2])
                pgn = r['pgn'].replace(r['id'], gid).replace(r['official'], aid)
                pgn = pgn.replace('[OpeningPair "0"]', f'[OpeningPair "{n//2}"]').replace('[Round "1"]', f'[Round "{n//2+1}"]')
                outbox.append((aid, 'games', pgn))
            with s.tx():
                s.db.executemany('INSERT INTO games VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)', games)
                s.db.executemany('INSERT INTO attempts VALUES(?,?,?,?,?,?,?,?,?,?,?)', attempts)
                s.db.executemany('INSERT INTO moves VALUES(?,?,?,?,?,?,?,?)', plies)
                s.db.executemany('INSERT INTO outbox(aid,stream,pgn) VALUES(?,?,?)', outbox)
                s.db.execute('UPDATE tournaments SET cursor=? WHERE id=?', (end//2, tid))
                s.db.execute('UPDATE aggregates SET d=?,p2=? WHERE tid=?', (end, end//2, tid))
                s.db.execute('UPDATE rankings SET score=? WHERE tid=?', (end/2, tid))
                s.db.execute('UPDATE report_revisions SET revision=? WHERE tid=?', (end, tid))
            # Fixture-only bulk materialization; production exporter is measured below.
            with (folder/'games.pgn').open('ab') as f:
                for _, _, pgn in outbox:f.write(pgn.encode('utf-8'))
                f.flush();os.fsync(f.fileno());offset = f.tell()
            with s.tx():
                s.db.execute("UPDATE exports SET last_id=(SELECT max(id) FROM outbox),offset=? WHERE stream='games'", (offset,))
            if end % 5000 < 256 or end == target:
                print(json.dumps({'seeded': end, 'seconds': round(time.perf_counter()-started, 2)}), flush=True)
        s.db.execute('PRAGMA wal_checkpoint(TRUNCATE)')
        return tid
    finally:s.close()


async def writer_benchmark(folder, tid):
    start = time.perf_counter();db = await Database().open(folder)
    result = {'reopen_ms': 1000*(time.perf_counter()-start)}
    try:
        backup = asyncio.create_task(db.call('backup'))
        # Submit durable audit writes while the backup is in progress. On the
        # original implementation these queue behind the entire backup/check.
        await asyncio.sleep(.025)
        start = time.perf_counter();latencies=[]
        while not backup.done() or not latencies:
            tick = time.perf_counter()
            await db.call('execute', 'INSERT INTO audit(tid,created,action,body) VALUES(?,?,?,?)',
                          (tid, time.time(), 'scale_latency_probe', '{}'))
            latencies.append(1000*(time.perf_counter()-tick))
            await asyncio.sleep(.02)
        await backup
        result.update(backup_seconds=time.perf_counter()-start+.025,
                      writes_during_backup=len(latencies), writer_wait_max_ms=max(latencies),
                      writer_wait_p95_ms=sorted(latencies)[math.ceil(.95*len(latencies))-1])
    finally:await db.close()
    return result


def benchmark(folder, tid, count):
    s = Store(folder)
    try:
        assert s.snapshot(tid)['official_games'] == count
        assert s.snapshot(tid)['complete_pairs'] == count//2
        result = {'completed_games': count, 'moves': count*80,
                  'database_bytes': s.path.stat().st_size,
                  'automatic_pgn_bytes': (folder/'games.pgn').stat().st_size}
        for name, fn in (
            ('standings', lambda: s.snapshot(tid)),
            ('games_first_page', lambda: s.games(tid, limit=50)),
            ('games_last_page', lambda: s.games(tid, offset=count-50, limit=50)),
            ('games_failed_filter', lambda: s.games(tid, 'failed', limit=50)),
            ('idle_pgn_export_check', s.export_pending),
        ):result[name] = measure(fn)
        result['opening_report'] = measure(lambda: opening_report(s.path, tid), 3)
        def cold_trends():
            _cache.clear();tournament_series(s.path, tid)
        result['uncached_history_graph'] = measure(cold_trends, 3)
        result['cached_history_graph'] = measure(lambda: tournament_series(s.path, tid))
        result['working_set_bytes'] = psutil.Process().memory_info().rss
        result['outbox_query_plan'] = s.rows('EXPLAIN QUERY PLAN SELECT * FROM outbox WHERE stream=? AND id>? ORDER BY id LIMIT 64', ('interrupted', 0))
        start=time.perf_counter();reader=OfficialPgnReader(s.path,tid);size=0;peak=0;ids=set();digest=hashlib.sha256()
        try:
            while chunk:=reader.chunk():
                size+=len(chunk);digest.update(chunk)
                for aid in re.findall(rb'\[AttemptId "([^\"]+)"\]',chunk):
                    assert aid not in ids;ids.add(aid)
                peak=max(peak,psutil.Process().memory_info().rss)
        finally:reader.close()
        assert len(ids)==count and size==result['automatic_pgn_bytes']
        result['streamed_official_pgn']={'seconds':time.perf_counter()-start,'bytes':size,
            'unique_attempts':len(ids),'sha256':digest.hexdigest(),'peak_process_working_set_bytes':peak}
        # Validate legal moves/annotations for both color templates and samples
        # throughout the fixture; all remaining records are exact move copies.
        samples=s.rows('SELECT o.pgn FROM games g JOIN outbox o ON o.aid=g.official '
            'WHERE g.tid=? AND (g.number IN (0,1,?) OR g.number%997=0)',(tid,count-1))
        for row in samples:
            game=chess.pgn.read_game(io.StringIO(row['pgn']))
            assert game and not game.errors and len(list(game.mainline_moves()))==80
        result['independently_parsed_pgn_samples']=len(samples)
    finally:s.close()
    result['backup'] = asyncio.run(writer_benchmark(folder, tid))
    print(json.dumps(result), flush=True)
    return result


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--label',default='before')
    parser.add_argument('--counts', type=int, nargs='+', default=[1000, 20000, 50000])
    parser.add_argument('--folder',default='history-scale')
    args=parser.parse_args();folder=(ROOT/'test-output'/args.folder).resolve()
    if folder.parent!=ROOT/'test-output':raise ValueError('Use a data folder directly inside test-output')
    folder.mkdir(exist_ok=True)
    report={'fixture': 'Synthetic completed games with real engine profiles and 80 recorded legal plies each; no real-engine throughput or physical GUI latency claim.', 'results': []}
    path=ROOT/f'test-output/history-scale-{args.label}.json'
    for count in args.counts:
        tid=seed(folder,count);report['tournament']=tid
        report['results'].append(benchmark(folder,tid,count))
        path.write_text(json.dumps(report,indent=2),encoding='utf-8')


if __name__=='__main__':main()
