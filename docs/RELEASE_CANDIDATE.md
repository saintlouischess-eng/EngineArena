# Engine Arena 0.2.0 Beta 3 RC 2

Local candidate, September 27, 2026. Not published. Includes pre-start tournament
editing, the automatic queue, custom matchups, linked events and league divisions,
SPRT and experiment corrections, the studio design, and the Running-button and
light-sidebar fixes. RC 1 installer results below are historical evidence.

Current source validation: 455 Python tests and 44 JavaScript checks passed.
Independent reference checks passed 1,408 score/Elo/CI/LOS cases, 144 SPRT cases,
180 pool estimates and a 10,000-participant sparse rating fixture. All eight
catalogs validate with 3,139 messages each. The 52 Python warnings concern aiohttp
application-key conventions. Detailed second-machine and physical display checks remain open.

September 27 laptop follow-up: the owner reports, "Laptop test looks good" after
receiving RC 2. Record this as a positive user-reported laptop check. Duration,
game counts, restart/export workflows and physical display coverage were not
specified, so it does not close those detailed checks or extended endurance.
The tested installer has not been rebuilt or published following this feedback.

### RC 2 packaged checks

- 84 real-engine integration games passed: profile books, shared master openings,
  fractional increments, pure node commands, live concurrency and Lc0 admission.
  GPU-group occupancy stayed at one while CPU games overlapped. Four committed
  results and four interrupted attempts survived forced native-app termination;
  resumed games retained their openings and archived moves. These feature games
  used documented short ply caps.
- All 20 paired/unpaired format combinations ran through the automatic queue.
  Linked group/Swiss events and a two-season league also completed: 402 games,
  38 generated reports, raw-game W/D/L reconciliation and all four PGN presets
  replayed legally. Six profiles used two real engine binaries. Short capped or
  mate-in-one games test lifecycle, not engine strength.
- 30 packaged suite/benchmark cases passed at nodes, depth and 50 ms/move,
  including measured NPS and effective thread-count checks. Restart retained
  results, queue state and exact automatic-PGN bytes.
- Timeout replacement retained the original attempt, changed the official result
  once and preserved the opening pair. Diagnostic replay left standings unchanged.
  Crash retry, actual test-PGN write denial/retry and termination during a partially
  written backup all passed; recovered databases passed integrity checks.
- Packaged reports, PGN presets and storage controls passed in all eight languages
  at enlarged font sizes. Source interface checks passed 232 layouts, ten clock
  layouts and 13 run-button state/action cases; the packaged current assets match
  source byte-for-byte. Theme switching had already passed contrast and persistence
  checks. These are browser checks, not physical monitor or mouse-latency tests.
- Ten compiled WebView2 policy cases passed with both real present-runtime
  detection and a per-process absent-runtime simulation. The shared runtime and
  sensor driver were not changed.

### RC 2 load measurements

Four alternating baseline/dashboard runs completed **2,048 full legal games** at
up to 32 concurrency, all ending in checkmate, with no engine or saving failures.
All four PGN presets parsed and replayed legally. Active game execution totaled
12.98 minutes; this is a bounded load check, not multi-day endurance evidence.

The dashboard mounted 32 boards and all 16 graphs. Its mean elapsed-time increase
was **1.94%** over the two baseline runs on this development host. Snapshot p95
was 35.5–37.1 ms. Browser frame p95 was 6.2 ms; the two live runs recorded one and
two long tasks totaling 70 and 130 ms. No physical input events were sampled.
These four observations do not establish a universal overhead bound.

The worker's sampled peak private memory was **86.6 MiB** and fell after the live
runs. This excludes engine and browser memory. Twenty-seven live report/export
checks passed; standard reports took at most 0.31 seconds and PGN export requests
at most 10.25 seconds. Background backup activity was observed in every run.
These report timings concern the 512-game phases, not a new 76,500-game dataset.

Deleting the four load tournaments through the packaged app reclaimed
**2,415,948,777 bytes**: managed storage fell from 2,417,304,553 to 1,355,776 bytes
(2.42 GB to 1.36 MB). The main database and both recovery copies contain no
tournament/game/attempt/move/log records, have no free pages and pass integrity
checks. Both engine profiles, preferences and a clean restart were preserved.
Deletion took 46.27 seconds; worker readiness on the cleaned workspace was 0.91 s.
Before deletion, a full technical report for one 512-game phase took 1.34 seconds
and its identical cached report took 0.20 seconds.

### Exact installer verification

Upgrade/uninstall checks run after the final installer is compiled. Their verdict,
tested installer SHA-256 and preservation results are supplied alongside the EXE
in its `.validation.json` file. This document alone is not an exact-file installer
approval. The checks cover updates from public Beta 2 and local RC 1 on the
development host; clean Windows and detailed laptop checks remain separate.

RC 2 evidence is under local `test-output/rc2-*`; reproducible packaged checks
are `scripts/rc_acceptance.py`, `rc_formats_acceptance.py`,
`rc_failure_acceptance.py`, `rc_load_acceptance.py`, `rc_storage_acceptance.py`
and `rc_installer_acceptance.py`. Initial harness setup mistakes (queue revision
lookup and choosing the ordinary environment without numerical-reference
dependencies) were corrected; only completed passing runs are counted.

## Historical RC 1 validation — September 26, 2026

Local candidate, September 26, 2026. Not published. This is a candidate for
additional beta testing; stable-release acceptance remains open.

Post-candidate development: [pre-start tournament editing](TOURNAMENT_EDITING.md) and the [automatic tournament queue](TOURNAMENT_QUEUE.md) are now available in the local development build. These updates are not included in the installer validated below.

## Current validation

All tests below used isolated test folders. Existing personal tournaments,
profiles and settings were not changed during this candidate validation.

| Area | Current result |
| --- | --- |
| Automated regression | 366 Python tests and 42 JavaScript tests passed. The 46 Python warnings concern aiohttp application-key conventions. |
| Independent statistics | 1,408 score/Elo/CI/LOS comparisons, 144 SPRT comparisons and 180 pool estimates passed against independent calculations. |
| Real-engine feature integration | 84 games covered separate engine books, shared master positions, fractional increments, node-only controls, live concurrency, interrupted-game recovery and mixed CPU/GPU scheduling. These feature games used explicit short ply caps. |
| Real-engine load | 1,536 additional games reached legal checkmate without caps or engine failures, at up to 32 simultaneous games. All four PGN presets parsed and replayed legally. |
| GPU admission | With Lc0 and three CPU profiles, the GPU group remained at one active game while CPU games overlapped; peak total concurrency was four under the configured resource budget. |
| Failure recovery | Forced native-application termination retained committed results, saved unfinished attempts and resumed from their recorded openings. Killing the app during a partially written backup also recovered successfully. |
| Result replacement | Original timeout retained; replacement changed the official result exactly once and preserved its completed opening pair. A diagnostic replay left standings unchanged. Crash retry retained all three attempts for two official games. |
| Saving errors | A real Windows PGN write denial produced a visible error and stopped scheduling. Releasing the denied file and retrying recovered the committed result and valid PGN. A SQLite page limit separately tested actual SQLITE_FULL rollback without filling the drive. |
| Interface and languages | Eight languages checked at 1,100 and 1,550 pixel widths with 24 px text; PGN previews, HTML/text reports, storage controls and warning visibility passed without browser errors or horizontal page overflow. Catalog checks cover 2,821 messages per language. |
| Native export | Cancelling Save As restored the controls. Saving 24 games to a chosen path containing spaces and an accented filename produced a legal PGN. |
| Installation and upgrade | Actual Beta 2 installation upgraded to this candidate in an isolated directory. Every installed payload file matched its manifest hash. Existing official games, opening pairs, settings, standings, preferences and exact automatic-PGN bytes survived. New exports/reports and a clean restart passed. |
| Uninstall | Uninstall removed the test application while preserving its tournament database, PGN and an unrelated file inside the installation folder. |
| WebView2 prerequisite | Ten production-policy cases passed with the real loader probe in both present-runtime and simulated-absent-runtime environments, including the previously reported already-installed error. The shared runtime was not removed or reinstalled. |

The installer checks are recorded in local `test-output/rc-installer.json`,
including the exact tested installer hash. Do not infer a clean-machine
installation pass from tests on this development host. An initial harness run
stopped on incorrectly named standings fields; after correcting the harness,
the complete upgrade/restart/export/uninstall sequence passed.

## Measured responsiveness

The four alternating full-dashboard load runs completed 128 games each. Mean
elapsed time increased by **3.84%** with 32 boards and all 16 graph panels mounted,
compared with the packaged worker without a dashboard. The graph runs had
approximately **36–37 ms** 95th-percentile snapshot requests and **6.2 ms**
95th-percentile browser frame spacing. No physical input events were sampled.
One run recorded a single 51 ms long task; the other recorded none.

An earlier 1,024-game comparison exercised boards but accidentally mounted no
graphs; its separate evidence is labelled accordingly. It is not used to claim
full-graph performance. Both comparisons used headless Edge on the development
desktop with ordinary background activity. Short repeated runs do not establish
zero overhead, laptop performance or multi-day reliability of this exact build.

Worker readiness during three native launches was 0.88–0.99 seconds. A small
technical tournament report generated in about 0.22 seconds. These are worker
and small-report measurements, not complete window-load or 76,500-game report
timings. The independent sparse pool fixture handled 10,000 engines in 2.11
seconds with approximately 11.1 MB of traced allocations.

A normal native Close showed the saving/backup progress title and both the
desktop and worker exited cleanly. The native close was observed but was not
timed precisely. Forced-termination checks are separate from that normal close.

Historical evidence includes a completed 76,500-game endurance tournament,
independent statistics/report reconciliation and legal PGN export. Deleting that
tournament and its recovery copies reclaimed 114.35 GB. These observations do
not automatically validate subsequent changes or other computers.

## Reproducible evidence

The local evidence is under `test-output`: `rc-final.xml`, `rc-js.log`,
`rc-math.json`, `rc-pool.json`, `rc-integration.json`, `rc-failures.json`,
`rc-load.json`, `rc-load-graphs.json`, `rc-ui.json` and `rc-native.json`.
The source distribution includes the regression tests and `scripts/rc_*`
harnesses. They use explicit test directories and separately supplied engines;
commercial engines, personal networks and private test workspaces are not shipped.

## Candidate changes

Since public Beta 2: revised knockout matches and opening progression; separate
per-engine move books with shared master positions still available; live time
forfeit counts and original-attempt navigation; adjustable live concurrency;
focused clock layouts; improved large-history startup, reports, PGN presets,
storage cleanup, translations and vector artwork.

Storage planning now uses workspace counters and allocated pages without scanning
saved moves. After 100 official games it estimates future managed storage for
remaining scheduled games, including paused tournaments and configured recovery
copies. It includes a separate temporary-space allowance and warns across views
when free space may be insufficient. This is a rough average: imported data,
retries, game length and engine logging affect it. Conditional rounds and
unbounded playoffs are not a finite storage guarantee. It does not stop play on
the basis of a forecast. Actual saving failures still stop scheduling.

## Checks requiring another machine or hands-on review

September 26 follow-up: the owner reports that the candidate installed successfully
on the laptop and appears to work normally. Laptop installation and basic operation
are recorded as user-confirmed. This report does not establish a fresh Windows
image, detailed data-retention verification or a completed candidate tournament.

- Fresh Windows installation; detailed laptop tournament, export and restart checks.
- Physical monitor changes, mixed DPI, keyboard/mouse responsiveness and executable
  drag-and-drop between windows.
- Optional sensor approval and readings on additional hardware.
- Native-speaker review of translated wording.
- Longer combined runs on this exact candidate, especially other GPU drivers,
  low-memory systems and varied engine time management. The earlier week-long
  tournament remains historical evidence, not a new candidate endurance run.
- Remaining native picker/export placements and physical cross-window drag-and-drop
  listed in `NATIVE_ACCEPTANCE.md`.

No installer or source publication is authorized by this local testing pass.

## Unreleased local format additions — 2026-09-26

Custom matchups, linked group/Swiss-to-final events, and league divisions with promotion/relegation are available in the source-backed development launcher. They are not in the previously delivered RC1 laptop installer. See EVENTS.md for usage, recorded policies, recovery/correction handling and focused validation. Release publishing remains deferred.

Unreleased local SPRT review: see [SPRT.md](SPRT.md) for changes and acceptance evidence. No installer rebuild or publication.
