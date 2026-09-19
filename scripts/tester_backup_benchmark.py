"""Bounded large-history backup check; operates only on a separate fixture copy."""
import asyncio
import json
from pathlib import Path
import shutil
import sqlite3
import sys
import time

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from arena.runner import Database,Runner


async def main():
    source=ROOT/'test-output/history-live';target=ROOT/'test-output/tester-backup-scale'
    if target.exists():raise SystemExit('Benchmark fixture already exists; preserve it and inspect its report.')
    target.mkdir()
    with sqlite3.connect(source.joinpath('arena.sqlite3').as_uri()+'?mode=ro',uri=True) as reader:
        with sqlite3.connect(target/'arena.sqlite3') as writer:reader.backup(writer,pages=1024)
    for name in ('games.pgn','interrupted.pgn'):
        if (source/name).exists():shutil.copy2(source/name,target/name)
    start=time.perf_counter();db=await Database().open(target);opened=time.perf_counter()-start
    try:
        games=await db.call('one','SELECT count(*) n FROM games WHERE invalid=0 AND official IS NOT NULL')
        start=time.perf_counter();assert await db.call('backup',force=False);copied=time.perf_counter()-start
        files={p.name:p.stat().st_mtime_ns for p in (target/'backups').glob('recovery-*.sqlite3')}
        start=time.perf_counter();assert not await db.call('backup',force=False);reused=time.perf_counter()-start
        assert files=={p.name:p.stat().st_mtime_ns for p in (target/'backups').glob('recovery-*.sqlite3')}
        status=dict(db.store.backup_state)
    finally:
        start=time.perf_counter();await Runner(db).close();closed=time.perf_counter()-start
    report={'database_bytes':(target/'arena.sqlite3').stat().st_size,'official_games':games['n'],
            'open_seconds':opened,'full_verified_copy_seconds':copied,'unchanged_backup_check_seconds':reused,
            'unchanged_shutdown_seconds':closed,'copy_files_unchanged':files=={p.name:p.stat().st_mtime_ns for p in (target/'backups').glob('recovery-*.sqlite3')},
            'backup':status,'scope':'Separate copy of existing synthetic-plus-real history. Warm-cache local measurements. Changed data still requires a full verified copy; no power-loss or long soak claim.'}
    (ROOT/'test-output/tester-backup-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))

if __name__=='__main__':asyncio.run(main())
