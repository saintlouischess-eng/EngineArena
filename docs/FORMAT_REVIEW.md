# Tournament, suite and benchmark review — September 26, 2026

Status: completed locally. The development executable loads these changes. No installer was rebuilt and nothing was published to GitHub. Tests used isolated workspaces; the owner's database was opened read-only only to copy six engine profiles.

## Coverage and results

| Format | Real paired games | Real unpaired games | Forced desktop termination and recovery |
| --- | ---: | ---: | --- |
| Fixed match | 4 | 2 | Passed |
| Round robin | 40 | 20 | Passed |
| Multiple-candidate gauntlet | 24 | 12 | Passed |
| Self-play | 20 | 10 | Passed |
| Swiss | 24 | 12 | Passed |
| Single-elimination KO | 24 | 12 | Passed |
| Double-elimination KO | 48 | 24 | Passed |
| Ladder | 24 | 12 | Passed |
| Two-engine SPRT | 4 | 2 | Passed |
| Custom matchups | 8 | 4 | Passed |

Real engines: Stockfish 18, Reckless 0.10.0-dev-7300f044, PlentyChess 8.0.0, Cinder 0.6.1, Alexandria-9.0.0 and Integral v8. Thread/hash settings were reduced to one thread and 16 MB for lifecycle checks.

Four multi-stage combinations passed: RR groups or Swiss groups, each feeding either an RR or KO final. A three-division, two-season promotion/relegation league passed. These added 72 games, making **402 completed real-engine games with unique, legal PGNs and no engine failures**. Thirty-eight reports were generated. An independent raw-game reconciliation checked 140 engine rows for W/D/L, played games, score percentages, points, recorded bye awards and suppression of self-play Elo/LOS.

Stockfish/Reckless suite and benchmark runs covered pure nodes, fixed depth and 50 ms per move. All **36 cases** completed without failures; all 12 simple best/avoid suite cases were correct. Benchmark settings exercised one/two threads and repeated samples. These are correctness checks, not meaningful speed rankings.

The development desktop was killed during confirmed active searches **12 times**, once for every format and once for each experiment kind. Every restart retained committed results, archived unfinished attempts, resumed only unfinished work and left no engine child processes. The recovered tournaments completed 154 fixture-engine games with valid PGNs; the recovered suite/benchmark completed 12 official cases and retained their interrupted attempts separately.

Regression checkpoints: **453 Python tests passed**, followed by **66 format/report/localization tests** after the final report clarification (including two new tests). Forty-four JavaScript checks passed across the final suite and focused text-export rerun. Existing aiohttp application-key warnings remain; they did not fail tests. GUI coverage included 160 format layouts (10 formats × 8 languages × 2 widths), suite/benchmark forms, 20 px text, live results, 50-row paging, a complete 52-case JSON/text export and eight-language result views. Screenshots were inspected and several misleading translated column labels were corrected.

## Corrections and improvements

- Experiment completion is idempotent. Repeated callbacks cannot overwrite committed results, advance a case twice or claim the same active case twice. Finishing the last case immediately records completion.
- Old experiment records migrate without losing original attempts/logs. Missing historic thread evidence stays unavailable.
- Benchmark schedules are decoded incrementally. A two-million-case schedule stayed compact; those two million searches were not executed.
- Results use bounded pages and summaries over small indexed metadata. Full exports still contain every attempt, original logs and configuration snapshots.
- Benchmarks require a matching advertised Threads setting; an unsupported configuration produces a visible failure instead of a false scaling measurement. Summaries show measured NPS mean/min/max and reported-NPS coverage.
- Suite timing distinguishes the first correct PV from the final uninterrupted correct-PV sequence. It uses the same monotonic search start as engine timing. Incorrect final moves remain unsolved.
- Invalid EPD answers, unplayable positions, duplicate/invalid thread counts, non-finite watchdogs and invalid experiment state requests are rejected clearly.
- The GUI exposes startup/readiness/hang watchdogs separately from search limits, refreshes open results, distinguishes running from archived attempts, and keeps benchmark tables free of irrelevant solve/accuracy columns.
- Event-stage Start remains disabled unless a diagnostic run is allowed. Use Run event for official stage progression.
- Swiss reports and sharing tables disclose bye points. KO live results and reports identify whether score, playoff score, seed, a standings tiebreak or a manual decision selected the winner. HTML cache version 9 refreshes these explanations without changing results.

## Evidence and reproduction

Main scripts: `validate_all_formats.py`, `audit_format_reports.py`, `validate_format_recovery.py`, `validate_format_experiment_ui.cjs` (with `preview_events.py`). New regressions: `test_experiments_review.py`, report and text-export tests.

Evidence under `test-output/`: `all-formats-real.json`, `all-formats-report-audit.json`, `format-recovery.json`, `all-formats-final.xml`, `format-report-final.xml`, `format-experiment-ui.json`, `experiment-ui-export.json`, `experiment-ui-export.txt`, and the corresponding screenshots and isolated databases.

An early recovery harness read a cached running-game count after a search had finished. The final harness waits for a fixture engine to confirm an in-flight search before killing the desktop. One early event fixture produced only draws under continuous KO rules; the final KO event checks use decisive mate-in-one openings. Those preliminary runs are not counted as final passing evidence.

## Limits

This pass checks functionality and recovery; it is not another week-long stress test or a claim of perfection. Most real games used an eight-ply cap and 1,000 nodes per move. Standalone KO fixtures deliberately selected a bounded legacy playoff/seed policy; KO event fixtures used continuous play with decisive openings. Existing regressions separately exercise sustained ties, manual resolution, result replacement, dependent rounds, color/pair accounting, large fields and SPRT boundaries. Forced desktop termination tests committed-data recovery, not a physical power cut or damaged hardware. Clean-laptop acceptance, long runs on the final build and native-speaker translation review remain useful before release.
