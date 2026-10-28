# Engine Arena 1.10.8 — Faster record deletion

Deleting a small tournament or its Rating Center results previously ran VACUUM
and a full integrity scan on the entire shared database and every affected
recovery copy. A ten-game experiment could therefore rewrite many gigabytes of
unrelated marathon data, twice if its ratings were removed separately.

Tournament, event and rating cleanup now remove their records without that
automatic compaction. Freed database pages are available for new games. Use
**Worker & recovery → Reclaim disk space** when you want to shrink the files on
disk. That optional operation still performs full compaction and integrity checks.

Durable deletion receipts, recovery-copy scrubbing, atomic backup replacement,
backup timestamps and PGN cleanup are retained. Existing report readers no longer
force cleanup to wait for a truncating checkpoint. Large recovery copies still
take time to copy safely; deletion is not constant-time. Pause and drain before
deleting, as before. Keep Rating Center evidence remains checked by default;
uncheck it to remove a tournament and its ratings in the same operation.

An isolated 807 MB fixture with two recovery copies and ten target games took:

| Operation | Previous build | 1.10.8 |
| --- | ---: | ---: |
| Delete tournament, retain ratings | 24.69 s | 3.47 s |
| Remove those ten rating records | 24.49 s | 3.27 s |

These are local fixture measurements, not a timing guarantee for a live workspace.
Recovery tests cover interrupted backup replacement, restart completion,
restoration from old backups, retained ratings and unaffected tournaments.

Install after pausing/draining and closing Engine Arena. This update was tested
on isolated data; the running marathon was not stopped or modified.
