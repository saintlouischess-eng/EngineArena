# Storage and recovery maintenance

Engine Arena saves every move and completed result transactionally. Recovery snapshots are additional copies of that shared database; their interval is independent of the move-saving interval.

## Worker & recovery

The **Storage & backup settings** panel displays database, transaction journal, recovery-copy, automatic PGN and temporary cleanup sizes, total managed storage, and free drive space.

- **Recovery copies:** 2–10, default **3**. A reduced limit is enforced only after a replacement snapshot has passed its integrity check and disk flush. It never removes the only verified snapshot before publishing its replacement.
- **Minimum backup interval:** 1–60 minutes, default **5**. Slow backups run less often automatically. Unchanged verified snapshots are reused. Normal application shutdown waits for the final recovery copy.
- **Reclaim disk space:** stop or pause and drain all tournaments and experiments first. This converts legacy text logs to compressed blocks, compacts the main database, creates a verified snapshot, applies retention, and compresses/compacts the retained older snapshots. Progress remains readable during cleanup. Starting or changing games is blocked until it finishes.

Saving a smaller copy limit does not immediately delete files. Run Reclaim disk space to apply it now, or let the next verified backup apply it.

## Planning a long tournament

Expand **Storage planning estimate** in Worker & recovery. After 100 official
games, the estimate uses the workspace's occupied database pages and automatic
PGN size per official game. It projects the remaining scheduled games across
running and paused tournaments, including the configured number of recovery
copies. Existing reusable database pages are taken into account. A separate
temporary-space allowance reserves twice the projected database size for
compaction and verified replacement; it is not a guaranteed upper bound.

The estimate is deliberately approximate. Fixed imported data and retries are
included in the average; changes in engines, logging or game length can change
growth. Knockout playoffs and other conditional schedules can change the game
count. External exports are not included. Before 100 games, projected growth is
unavailable, but low-space checks include the current database and recovery work.

The interface checks every 30 seconds outside the storage view and every two
seconds inside it. A warning appears across views when the estimated requirement
exceeds available space or free space falls below 256 MiB. Reading small counters
and page metadata does not scan saved moves or hold the writer connection. A
forecast never silently stops a tournament; actual saving failures stop scheduling
and require recovery as described below.

## What is preserved

Log compression is lossless: original order, timestamps and diagnostic text are retained. New log blocks commit in the same transaction as the move. Games, original attempts, failures, settings, opening seeds, clocks, engine observations, statistics and PGNs remain intact. Reports and the recent-diagnostic view read both old text rows and compressed blocks. Use the updated build to read compressed diagnostics.

The existing per-line input limit remains unchanged. Compression does not introduce an additional retention limit or discard successful-game diagnostics.

## Tournament deletion

Deleting a tournament removes its records from the main database, automatic PGNs and recovery snapshots. The database and affected snapshots are then compacted, returning freed space to Windows. Other tournaments, library profiles, reusable presets and external exports are preserved. Large deletions can take time and need temporary working space. After verified cleanup, abandoned compaction/deletion images and orphaned recovery-snapshot WAL/shared-memory journals are also removed. Sidecars of an existing recovery snapshot and unrelated files are preserved.

A durable deletion ledger prevents an older recovery snapshot from resurrecting a deleted tournament. An interrupted deletion resumes at startup. Original snapshots remain recoverable until their cleaned, compacted replacements are verified and flushed.

## Interrupted maintenance and saving failures

Log conversion uses bounded, atomic batches. SQLite compaction is transactional. A durable maintenance marker permits cleanup to resume after application termination; it does not require restarting a tournament. Backup replacement uses a temporary file, an integrity check, a disk flush and an atomic rename.

After interrupted cleanup, the desktop opens the recovery screen while the saved maintenance job continues in the background. Progress and worker status remain available; game starts and other data changes wait until recovery finishes. This avoids treating a lengthy cleanup as a failed application startup.

Failures are reported in the storage panel and worker status; scheduling stops until saving is repaired. Use Reclaim disk space or Retry saving, or reopen the program, to resume unfinished cleanup. Temporary files are counted in the storage display and cleared when cleanup succeeds. External PGN exports and files retained from an earlier corruption diagnosis are not automatically removed.

## Fast reopening of completed workspaces (September 26)

An unchanged, cleanly closed workspace now saves a small `clean-shutdown.json` receipt after closing SQLite. It identifies the database/WAL generation and the most recent verified recovery file. The receipt is consumed before startup can modify data. Matching receipts reuse a recent successful integrity check and an unchanged verified backup; missing, modified, expired (24 hours), or unclean receipts fall back to verification. Missing/changed recovery files are never accepted as current. Actual database changes still require a new verified snapshot. Optional receipt failure affects speed only, not committed results or recovery.

Old deletion-ledger entries previously made temporary lookup-table changes count as database changes on every launch. The lookup now occurs outside the durable mutation transaction unless a tournament actually needs removal. This prevents pointless full backups of a completed archive at each close.

The real 76,500-game database contains 9,741,800 saved moves and is approximately 28.5 GB. Its initial check took about 30–32 seconds; making and verifying a new full backup took about 86 seconds. After the fix, an unchanged Store reopened in 0.076 seconds and closed in 0.004 seconds with no new backup. These are database-worker measurements, not complete desktop startup times. The storage footprint is unchanged: the main archive and three recovery copies are retained. Both automatic PGNs were SHA-256 identical before and after the upgrade.

Completed-report caches are disposable, excluded from recovery copies, and removed during tournament deletion. They retain at most four HTML reports and four numerical summaries, each capped at 16 MiB; oversized reports can still be generated but are not cached.

## Validation

The September 21 checks cover exact diagnostic order/timestamps, result and PGN preservation, actual file-size reduction after optimization and deletion, interrupted conversion rollback, forced application-process termination during cleanup, failed replacement with the verified backup retained, cleanup restart, retention bounds, and readable progress while mutations are blocked. The full regression suite also covers tournament recovery, failed-result replacement, PGN integrity, large schedules, node-only play and resource admission.

## Actual stress-tournament deletion (September 26)

At the owner's request, the completed 76,500-game tournament and 76,584 attempts were removed through the normal deletion ledger and cleanup. The main database, three recovery copies, automatic PGNs and report caches fell from 114.35 GB to 1.55 MB in about 11 minutes. Exact managed-file reduction: 114,347,097,765 bytes (106.49 GiB). All tournament-linked tables are empty; every cleaned database passed integrity checks and had zero free pages. The engine library (11 profiles), preset and preferences match the cleaned historical snapshots; external exports were kept. A current verified small recovery copy was published, and clean reopening took 0.099 seconds without making another backup.

This is a real-data result, not an estimate based on deleted rows. Current-drive free space also increased; its exact change includes unrelated system activity. Evidence is in `test-output/deleted-76500-space.json`.
