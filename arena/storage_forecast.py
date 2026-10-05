"""Coarse capacity planning from small counters, never a scan of saved moves."""
import json
import math

MIN_SAMPLE = 100


def project(usage, *, used_database_bytes, completed, remaining, conditional=False):
    """Include all retained copies and a separate temporary-space allowance.

    The workspace average includes books, retries and other fixed data. It is
    deliberately labelled an estimate, not a per-engine prediction or quota.
    """
    sampled = completed >= MIN_SAMPLE
    db_rate = used_database_bytes / completed if sampled else None
    pgn_rate = usage['pgn_bytes'] / completed if sampled else None
    database = max(usage['database_bytes'], used_database_bytes)
    if sampled:
        # Reusable pages can absorb growth without enlarging the physical file.
        database = max(database, math.ceil(used_database_bytes + db_rate * remaining))
    backups = database * usage['settings']['backup_copies']
    pgn = usage['pgn_bytes'] + (math.ceil(pgn_rate * remaining) if sampled else 0)
    total = database + backups + pgn + usage['wal_bytes'] + usage['temporary_bytes']
    additional = max(0, total - usage['total_bytes'])
    # SQLite compaction and verified backup replacement need working space.
    # This allowance is not a guarantee against every possible disk workload.
    temporary = 2 * database
    headroom = usage['free_disk_bytes'] - additional - temporary
    return {'sample_games': completed, 'minimum_sample': MIN_SAMPLE,
            'remaining_games': remaining, 'conditional': conditional,
            'bytes_per_game': math.ceil(db_rate + pgn_rate) if sampled else None,
            'projected_total_bytes': total if sampled else None,
            'additional_bytes': additional if sampled else None,
            'temporary_allowance_bytes': temporary,
            'headroom_bytes': headroom,
            'warning': headroom < 0 or usage['free_disk_bytes'] < 256 * 1024**2}


def collect(db, usage):
    counts = dict(db.execute('''SELECT tid,coalesce(sum(n),0) FROM game_counts
        WHERE invalid=0 AND has_official=1 GROUP BY tid'''))
    remaining = 0
    conditional = False
    for tid, total, settings in db.execute("SELECT id,total,settings FROM tournaments WHERE state IN ('paused','running','draining')"):
        remaining += max(0, total - counts.get(tid, 0))
        conditional |= json.loads(settings).get('format') in ('swiss','knockout','double_elimination','ladder','sprt')
    pages = db.execute('PRAGMA page_count').fetchone()[0]
    free = db.execute('PRAGMA freelist_count').fetchone()[0]
    size = db.execute('PRAGMA page_size').fetchone()[0]
    return project(usage, used_database_bytes=(pages-free)*size,
                   completed=sum(counts.values()), remaining=remaining, conditional=conditional)
