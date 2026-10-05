# Engine Arena 1.0 — final local review

Review date: September 27, 2026. This build is for the owner's final laptop approval.
GitHub publication remains on hold. Tests use isolated workspaces; the owner's saved
tournaments, engines, books and settings were not changed.

## Changes from the preceding candidate

- Opening the same workspace twice now gives a clear explanation and preserves the
  existing worker's connection record. It starts no competing worker.
- Hover help closes when a control is activated, including by keyboard, so it cannot
  cover the newly opened report/export menu. Navigation help is fully localized.
- SPRT hypothesis tooltips now refer to the selected tested engine and configurable
  error targets. CPU sensor instructions no longer describe the installer as a beta.
- Desktop, sidebar, installer and documentation consistently identify Version 1.0.0.
- A new user guide covers installation/upgrades, engines, books, tournaments, queue,
  clocks, resources, live views, reports, recovery, retries and storage. It is available
  from the Start menu after installation.

## Fresh application checks

| Area | Result and scope |
|---|---|
| Regression | 457 Python and 44 JavaScript tests passed. All 44 JavaScript tests were rerun after the final help-text corrections; all eight catalogs contain 3,144 matching messages with no validation errors. |
| Fresh user workflow | Added and discovered a real Stockfish engine, cloned its profile, created and edited an unstarted tournament, queued and completed 12 node-only games, reviewed standings/reports, and exported PGN through the native Save As dialog. All 1,452 exported plies replayed legally. |
| Formats and events | 402 short real-engine games across all ten formats with paired and unpaired openings, round-robin/Swiss groups feeding round-robin/KO finals, and a two-season league. 38 reports reconciled against raw results. Queues resumed correctly. |
| Suites and benchmarks | 30 cases exercised the experiment lifecycle, results and exports. Separate forced-shutdown tests covered both experiment types. |
| Packaged integration | 84 games tested separate engine books, shared master openings, exact node-only UCI commands, fractional increments, live concurrency changes, reports, four PGN presets and exact PGN preservation after restart. Real Lc0 stayed at one GPU instance while CPU games overlapped. |
| Mathematical references | Independent SciPy calculations: 1,408 descriptive-statistics cases over 11 confidence levels and 144 SPRT cases. Maximum Elo discrepancy 8.41e-12; maximum SPRT discrepancy 6.09e-10. Pool ratings checked against 180 independent estimates and dense covariance. |
| Participant scale | A 10,000-participant, 9,999-edge pool produced 50 visible estimates in approximately 2.22 seconds with 11.1 MB traced allocation. Tournament size remains independent of process concurrency. |
| Recovery | Forced native application termination in every format, a suite and a benchmark: committed results retained, unfinished attempts archived, continued from recorded openings, no duplicate official results or orphan engines. Additional packaged interruption retained saved moves. |
| Failure handling | Original timeout preserved after official replacement; official TF and pair accounting updated without double-counting. Diagnostic replay left standings unchanged. Crash retry preserved attempts. Actual OS-denied PGN writes were reported, committed results retained, and saving resumed successfully. Interrupted backup recovered safely. |
| Layouts and controls | 232 workspace/dialog/layout checks, ten clock layouts, 12 graph/theme/font combinations, eight languages, large text and widths from 1,050 to 2,560 pixels. Run-control state checks included 13 cases and the previous flicker regression. Report previews and HTML/text/PGN export workflows passed. |
| WebView2 setup | Ten production installer-policy cases and the real runtime loader probe passed with the runtime present and simulated absent. The shared runtime and hardware driver were not altered. |

Format and event fixtures use short ply caps and decisive starting positions to test
scheduling and results, rather than engine strength. The format suite used the source
desktop; the separate packaged suite used the frozen Version 1.0 worker. Timing and
memory measurements are specific to this development computer.

## Large-history and load measurements

The history fixture contains 50,000 completed games and four million saved moves in
a 3.81 GB database. It copies real game telemetry to exercise history volume; it is
not presented as 50,000 newly played games or a repeat of the earlier week-long test.

- Standings query p95: 0.44 ms. Last history page p95: 5.99 ms.
- Failure-filter query p95: 127.6 ms. Opening-summary query p95: 284.1 ms.
- Clean database reopen: 22.9 ms (database operation, not full desktop startup).
- Readable PGN export: 50,000 unique official attempts, 166 MB, 146 seconds, bounded
  process memory of approximately 66.5 MB. Export IDs reconciled exactly; sample
  games independently replayed legally. Different presets legitimately differ in size.
- Backup: 12.8 seconds while 403 writes continued; p95 writer wait 5.2 ms.
- Full legal load run: 1,024 games over four phases at 32 concurrent games. All
  finished by checkmate, with no timeout, crash, hang, illegal move or ply-cap result.
  The two UI phases displayed 32 boards and 16 graphs, with no JavaScript errors;
  frame p95 was 6.2 ms. Live reports, PGN exports and backups ran during play.
  Average elapsed time was 3.24% higher with the UI in this short controlled test;
  this is a measured comparison, not a universal overhead guarantee.
- Deleting those four load tournaments reclaimed 1,216,262,197 bytes in 25.3 seconds.
  The main database and both recovery copies were checked for integrity, empty
  game/history tables and reclaimed pages. Profiles and preferences survived restart.
- Full 50,000-game standard report: 0.77 seconds; cached: 0.20 seconds. The first
  technical report scanned four million moves in 40.1 seconds; cached: 0.24 seconds.
  Technical calculation runs in a separate cancellable process. The completed
  fixture's packaged desktop became ready in 0.94–0.98 seconds and closed in 0.80
  seconds. These are clean opens/closes with an up-to-date backup; a needed backup
  or crash-recovery integrity check can take longer.

Final load, deletion, full-report and installer measurements are recorded alongside
the final installer in its validation receipt. The installer is delivered only after
those checks pass. Detailed raw development evidence is retained under
`test-output/v1-final-review`; it is not bundled with personal paths and engine logs.

## Scope and final approval

This is a local functional and regression review, not a promise of zero possible
bugs or compatibility with every engine and computer. Automated responsive layouts
do not replace physical DPI checks; translated catalogs still benefit from native
speaker feedback. Forced process termination tests do not simulate every possible
power-loss or storage-device failure.

The remaining release decision is the owner's laptop test of the exact delivered
installer: upgrade, open existing data, run a representative tournament, export a
report and PGN, close and reopen, and confirm the preferred display and hardware
settings. No new Windows installation, laptop approval or public release is claimed
by this review. Historical test documents describe their own earlier builds.
