# Engine Arena 1.1.2 — manager and save clarity

Local candidate for owner testing. Not published or installed over the owner's app.

- Tournament manager shows **One at a time** and **Run together** as prominent
  choices, with a persistent selected state. Run together opens the shared-budget
  review directly. Existing workspaces retain their selected mode and budgets.
- Cleaner run/pause controls, compact resource meters, readable progress and
  status, fewer buttons per row, and selection-only bulk controls. Timed starts
  and finish-then-pause remain in **Start time & stop options**. Row **Options…**
  includes setup editing and removal; removing an entry preserves its data.
- Create/edit shows **Saving…**, prevents repeat clicks and accidental dismissal,
  closes on committed success, selects the saved tournament, and confirms its
  name, game count and paused state. Rejected saves keep editable inputs.
- API create/edit no longer waits for a potentially long full recovery copy after
  the SQLite transaction has already committed. The worker coalesces background
  backup requests, including changes made during another copy. A backup failure
  remains visible and stops scheduling; it does not misreport a committed save
  as a failed creation. Shutdown still waits for backup work and copies the latest
  committed state. Transactional storage and rotation are retained.
- Eight languages, light/dark themes and enlarged text supported. The stationary
  pointer / restored-focus hover-help correction from 1.1.1 is retained.

## Validation

Targeted Python coverage: 49 tests for setup acknowledgement, editing, queue and
shared execution passed. New cases hold a backup open while three setups and an
edit commit, verify one follow-up copy contains all of them, expose a simulated
backup failure, and verify shutdown backs up a just-saved setup before scheduler
processing. Browser tests cover mode discovery, simultaneous mock tournaments,
bulk limits, filtering/sorting, individual/global pause, focus retention, all-game
boards, 32 translated/theme/size dialog layouts, 14 hover-help checks and create/
edit/rejected-save feedback with repeat-click protection. Existing editor workflow
regressions also passed. The final packaged app passed the same manager, save-feedback and hover-help
checks, plus stale-revision recovery and row-options edit/remove (data retained).
The complete regression suite passed: 485 Python tests and 45 JavaScript tests.
All 3,250 catalog entries are present in each of the eight languages.

This is a usability and setup-acknowledgement update. It does not change chess
clocks, UCI commands, tournament results, pairings or rating mathematics.

## Install

When ready, pause and drain active tournaments, close Engine Arena, and run
`EngineArenaSetup-1.1.2-win-x64.exe` using the existing installation folder.
Saved tournaments stay in the separate data folder. Normal updates do not need
WebView2 repair. Check 1.1.2 in the sidebar before resuming your tests.
