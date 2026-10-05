# Engine Arena 1.1.0 — local test candidate

Prepared October 3, 2026. Designed by Mark Young. This version adds optional
simultaneous tournaments. Public release and the owner's installation are pending.
Production tournament data was not opened or modified during this work.

## Changes

- Tournament manager offers **One at a time** and **Run together**.
- Shared CPU thread, engine-memory, game-count and GPU-group budgets apply alongside
  each tournament's limits. Mixed pondering costs are accounted for separately.
- Low/Normal/High priorities guide resource-time sharing. Waiting large games can
  reserve capacity without stopping unrelated work that fits the remaining budget.
- Search, filters, sortable columns, progress, bulk controls, individual pause/resume,
  game-limit changes and clear resource waiting messages make the list manageable.
- Live boards can show all running tournaments, with names on each card.
- Shared limits and priority history are recorded in run-session reports.
- Transactional queue settings preserve priorities, holds and global limits on restart.
  Existing workspaces keep sequential mode; recovery requires explicit resume.
- Automatic table refresh retains keyboard focus. Pending actions disable their controls,
  and a stale list revision can refresh and retry once while retaining server validation.
  All eight language catalogs include
  the new controls; the user guide describes the new workflow.

## Validation

The full regression checkpoint passed **479 Python tests and 45 JavaScript tests**.
After the final resource-reservation and report-history changes, all **46 focused
scheduler, queue, resource and runtime-report tests** passed again. The API check
verifies report evidence immediately after changing global limits and priority.

Packaged 1.1.0 checks used disposable workspaces and real Stockfish, Berserk and Lc0:

- **1.0.1 data upgrade:** four original results, standings, exact automatic PGN bytes
  and saved queue order retained; sequential mode remained the default.
- **28 games across four simultaneous tournaments:** up to three tournaments and four
  games overlapped. Global CPU reservation stayed within four threads. Across two GPU
  tournaments, Lc0 peaked at one instance while CPU games continued.
- **Forced native-app termination:** two committed results survived; four unfinished
  attempts across three tournaments retained their 21 saved moves. Recovery archived
  those attempts and continued the recorded games from their original openings.
- **693 UCI search commands** were pure `go nodes N` commands. All four PGN presets
  parsed with legal moves, correct game counts and unique official attempt IDs.
- **All ten formats**, paired and unpaired, ran through the shared manager. Together
  with five event/league configurations, this checked **402 short games, 38 reports**
  and standings/opening-pair reconciliation. Six suite/benchmark runs checked **30
  cases**. Restart retained results, queue state and exact automatic PGN bytes.
- Replacement replay preserved the original timeout, changed the official TF count
  once and retained opening-pair accounting. Diagnostic replay did not change standings.
  Automatic retry retained the original crash. An actual OS-denied PGN write produced
  a visible error and recovered after retry. Termination during a partially written
  backup recovered with results intact.
- The manager workflow passed bulk limits, search/sort, independent pause/resume,
  all-tournament boards, pause-all and reload checks. **32 combinations** of language,
  theme and viewport width passed at an enlarged 20px font, with no page/dialog
  overflow, missing translations or browser errors. Keyboard focus survives refresh.
- **3,235 messages in each of eight catalogs** passed catalog consistency checks.

The final installer checksum and packaged payload verification are in its
`.exe.validation.json` and `.exe.sha256` companion files. Local evidence is retained
under `test-output/manager-*`. Failed preliminary harness runs are not counted as
passing: a sandbox denied test-engine launches, a test initially read the wrong
nested report field, and the initial focus check exposed the UI issue fixed above.

## Scope and next test

These are short lifecycle and integration checks, not a new endurance run or proof
of performance on every computer. Actual clock/UCI timing behavior was not changed.
The prior long-tournament evidence remains documented separately.

Global budgets apply within one workspace; they do not coordinate separate app
instances or impose operating-system CPU/RAM limits. Resource costs use profile
settings. Priorities are relative weights, not guaranteed percentages. Linked
events/leagues retain ordered stages; suites and benchmarks wait for idle engines.

The owner should install this exact candidate, verify the existing workspace opens
with results/settings retained, then try two or more tournaments with shared CPU/GPU
limits, independent pause/resume, report/export and restart. No new CPU sensor-driver
installation is needed. Native-speaker translation review, physical laptop/DPI checks
and a longer simultaneous run remain useful acceptance work. No GitHub publication
was made as part of this task.
