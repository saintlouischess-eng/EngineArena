# Mandatory release contract

These requirements are mandatory. A working beta is not a production acceptance pass. Each item below must have measured evidence before release can be called production ready.

| ID | Mandatory behavior | Evidence required |
|---|---|---|
| LIVE | Standings, W-D-L, score/draw %, head-to-head, Elo, 95% CI, LOS visible during play; paired statistics at each completed opening pair | Live worker + UI checks; independent numerical fixtures; replacement reverses previous contributions |
| SCALE | No arbitrary engine/participant cap, bounded scheduling and independent concurrency, scheduled total before start | 10,000 participants; constant scheduling window; process count bounded at target concurrency |
| HISTORY | Remain responsive as one tournament exceeds 20,000–50,000 completed games, with all moves/PGNs retained | Completed-history benchmarks, bounded exports, concurrent writes during backups, plus a sustained real-engine/UI run at this history size; a large empty schedule is insufficient |
| PGN | Automatic completed-game PGN including identity/version, opening, settings, result, termination and optional telemetry; restart without duplication; separate interruptions | Parse exported games independently; interrupted append and restart fault injection |
| RECOVERY | Transactions for moves/results/schedules/openings/clocks/retries/settings; rotating verified backups; visible save failures | Force terminate application/worker during play and during an uncommitted write; reopen same tournament; only unfinished games restart at recorded opening |
| REPLAY | GUI game/failure filters; selected/all failures; requeue, diagnostic or official replacement; retries preserve attempts and pairs | Replace failed result, compare all aggregates, retry cap, dependency invalidation for Swiss/knockout |
| CLOCK | Sudden death, Fischer, simple/Bronstein delay, stages/repeat, move time, depth, pure `go nodes N`; per-engine controls, presets, queued comparisons | Exact wire command assertions, clock boundary tests, node-only fault classification and real-engine tournament |
| SETUP | File/folder/drag-drop discovery, all UCI option types, profiles/clones/import/export/bulk edit, path browsers, launch arguments | Visual end-to-end setup with multiple real engines |
| FORMATS | Match, round robin, gauntlet, single/double elimination, Swiss, ladder, self-play, SPRT, suites and benchmarks | Pair/color/bye/dependency fixtures for each; statistically validated SPRT |
| CHESS | Standard + all Chess960 positions, legal play/draws/castling, PGN/EPD/FEN/Polyglot, 7-piece Syzygy | Rule fixtures; missing tablebase handling; fifty-move semantics; ponder hit/miss tests |
| UI | High-DPI dark/light desktop, multiboard/focus/replay/setup, vector sets/custom import, arrows, saved layouts, selectable graphs | Visual inspection of every workflow including ultrawide dimensions |
| LOAD | 28–32 concurrent games; resource accounting, process isolation/cleanup, bounded telemetry, pause/drain/cancel | Sustained real-engine run, CPU/RAM/UI latency and game throughput measurements |
| DELIVERY | Source, reproducible build, portable Windows x64 or installer, concise documentation | Clean build and launch on Windows; explicit list of anything unverified |

## Design references

- [UCI specification](https://backscattering.de/chess/uci/): search limits, readiness and ponder lifecycle.
- [python-chess](https://python-chess.readthedocs.io/en/latest/): independent legal moves, Chess960, PGN, EPD, Polyglot and Syzygy support (GPL-3.0-or-later).
- [SQLite WAL](https://sqlite.org/wal.html): transactional recovery and concurrent readers.
- [Fastchess statistical implementation](https://github.com/Disservin/fastchess/blob/master/app/src/matchmaking/sprt/sprt.cpp): reference for multinomial likelihood, opening-pair sampling and sequential boundaries. Implementation must be independently checked, not assumed correct from resemblance.
- [Cute Chess](https://github.com/cutechess/cutechess): established engine tournament workflow reference.

## Acceptance status

Not yet accepted for production. See [beta validation scope](BETA_VALIDATION.md) for published measurements and remaining checks. Unimplemented or unverified requirements remain production release blockers.
