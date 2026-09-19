# Engine Arena

Windows x64 desktop application for UCI engine testing. **0.2.0 Beta 1 for testing and feedback; production acceptance pending.** Download the single **EngineArenaSetup-0.2.0-beta.1-win-x64.exe** from [GitHub Releases](https://github.com/saintlouischess-eng/EngineArena/releases). See the [laptop testing guide](docs/BETA_TESTING.md) and [validation scope](docs/BETA_VALIDATION.md). All requirements in [the acceptance contract](docs/ACCEPTANCE.md) remain mandatory.

## Run

Run the single installer on Windows 11 x64 (Intel/AMD), then launch Engine Arena from the Start menu. Setup includes Python, .NET and the full offline WebView2 installer. The optional signed CPU sensor driver setup is also included. Add your own UCI engines and opening books. The beta installer is unsigned; do not disable Windows security protections.

Portable source builds can still run `EngineArena.exe` from their complete output folder, with WebView2 installed separately.

By default, results live in `%LOCALAPPDATA%\EngineArena\Data`. Use `EngineArena.exe --data "D:\Engine Tests\Arena"` to select another local data directory. Only one worker may open a data directory at a time. Use a local disk for SQLite WAL storage.

1. Open **Engine library**, add executables or a folder, and test the UCI connection. Testing previews discovery without changing the library; choose Save profile to commit it. The discovered identity/version, all advertised UCI option types, working directory, arguments, file locations and profile settings are editable. Select profiles for a tournament; cloning creates independent configurations.
2. Select **New tournament**. Review the scheduled game total, opening selection and seed, time controls, concurrency, hardware budgets and retry policy. Tournament participants are snapshots, so later library edits do not silently change an existing test.
3. Create the tournament paused, then **Start / resume**. Results and histories remain visible during play. **Pause & drain** finishes active games. **Stop active games** archives unfinished attempts and requeues them from their recorded openings.
4. To replay, pause/drain first. Filter failures or select individual games. A **diagnostic replay** preserves the official result; **Replace official result** switches the official attempt only after replay completes. Original attempts remain. Swiss/knockout replacements that affect later rounds require explicit dependency invalidation.

## Controls and resource budgeting

Use **Hardware display…** in the top status strip to choose and reorder readings. Presets cover CPU/RAM, engine testing and CPU/RAM/GPU; every reading can also be selected individually or hidden. Choose a 2, 5, 10 or 30-second refresh target, Celsius/Fahrenheit, and a specific detected NVIDIA GPU. Preferences and the selected GPU identity survive restart. The strip wraps with the window and the chosen font size.

Available system readings include average CPU load, busiest logical processor, OS-reported nominal CPU clock, live fastest CPU core clock, RAM used/available/total/percentage, page-file usage, free/used capacity on the tournament data drive, system-wide disk and network throughput, system uptime, worker memory and active games. The settings panel identifies the CPU and core counts. The NVIDIA driver provider adds GPU utilization, VRAM used/total/percentage, temperature, power draw/limit, graphics and memory clocks, and fan percentage when supported. It reads the installed `nvidia-smi` utility without changing driver settings or installing software. GPU polling runs only when GPU fields are selected or the settings panel probes available sensors.

Hardware collection runs on a separate thread with a five-second CPU query timeout and three-second GPU query timeout; status requests use the latest cached sample. Missing, stale or disconnected readings show **Unavailable**, never a fabricated zero. CPU temperature uses the bundled LibreHardwareMonitor reader and the signed PawnIO driver. Open **Hardware display… → CPU sensor setup…** to open the included official driver setup, then **Enable CPU readings for this session** and approve Windows permission. Select **CPU temperature** and/or **Fastest CPU core**, then save. Temperature can use automatic die/package or a named sensor. Fastest CPU core displays the highest currently reported per-core operating clock in GHz, with the core identity in hover help. It refreshes at the selected interval and can miss short boosts between samples. The reader alone receives administrator permission and closes with the app; the app and chess engines keep normal permissions. Enable the reader again after reopening the app. Non-NVIDIA GPU telemetry is not supplied by this provider. CPU frequency on Windows is labelled nominal rather than live boost frequency. Disk throughput covers all disks, network throughput sums interfaces, and worker memory excludes engine/desktop processes. See [hardware monitoring details](docs/HARDWARE.md).

Sudden death, Fischer, simple/Bronstein delay, staged/repeating periods, fixed move time, depth and pure nodes are supported. Node-only searches send `go nodes N` without `wtime`, `btime` or `movetime`. An independent search watchdog still detects hangs. Startup, readiness, search and stop watchdogs have separate limits and classifications.

Per-profile time controls override the tournament control, enabling handicaps. Presets can carry time, threads, hash and paired-opening settings. Starting multiple tournaments queues comparisons; the worker completes the active tournament before dispatching the next.

Concurrency is a process budget, independent of participants. Estimated hash plus additional memory is counted for both engines. CPU budgeting uses the larger engine thread allocation without pondering, and both allocations with pondering. Shared GPU group limits count engine processes. **New tournament** also shows a conservative recommended concurrency and a button to apply it. It accounts for the selected profiles, independent thread/hash settings, available memory, Ponder and GPU slots. A zero recommendation identifies a budget that cannot fit one game. Estimates are admission controls, not process memory limits; set additional memory to cover networks and other engine allocations.

## Pairings and tournament ranking

Choose initial selection-order or seeded-random seeding, ordered standings tiebreaks, Swiss bye points, knockout playoff limits/fallbacks, and ladder challenge distance/movement when creating a tournament. The preview shows the base schedule and a conditional maximum where playoffs or a double-elimination final reset may add games.

**Pairings & tiebreaks** shows the saved round and stable participant numbers. Pause and finish the current Swiss round before editing the next one; every participant must appear exactly once, with one bye for an odd field. Rematches require an explicit selection. A knockout configured for a manual tiebreak pauses for an audited winner decision. Playoff games retain the tournament's opening-pair policy and are tagged `CompetitionStage` in PGN. Replacing results requires explicit invalidation of affected later rounds or same-round playoff sequences; all attempts and pairing decisions remain archived.

Engine Swiss uses expanding score-neighbor candidate bands and minimum-weight maximum-cardinality matching. It prefers similar points, color balance and new opponents; it is not FIDE Dutch. Bye points are separate from W-D-L, score percentage and Elo samples. Buchholz sums opponent tournament points per played game; Sonneborn–Berger weights those points by game score. Self-play reports each game once from White's perspective and does not infer between-engine Elo. Ladder standings follow the evolving ladder order, including the final round.

## Saved data and recovery

- `arena.sqlite3` with SQLite WAL/FULL synchronization is the source of truth: immutable tournament snapshots, schedule cursor, stable game/opening-pair identities, attempts, moves, clocks, results and audit events.
- `games.pgn` automatically contains every completed attempt. `AttemptId`, `GameId`, `OpeningPair`, `OpeningLeg` and `AttemptMode` distinguish retries and diagnostics.
- `interrupted.pgn` contains unfinished attempts preserved at interruption/recovery.
- **Results & exports → Export PGN… → Save PGN as…** lets you choose the folder and filename in the desktop app. Current official results are rendered from a consistent database snapshot, including for existing tournaments. Cancellation or a failed transfer leaves an existing destination unchanged. CSV/JSON contain current standings and model labels.
- PGNs now include verified recorded opening moves, marked `{book}`, from move one when the opening began at the normal starting position. FEN-only openings retain their FEN. No move history is invented when it was not recorded or cannot be verified.
- Compact export uses readable score/depth/elapsed-time comments, for example `{+0.57/33 3.904s}`, and readable settings headers. Positive compact scores favor the moving engine by default; White's perspective is selectable. Tagged export uses White-perspective `[%eval]`, `[%emt]`, `[%clk]` and optional search measurements. Moves-only and full technical archive formats are also available, with selectable annotations. Node/depth controls do not invent remaining clocks.
- New automatic PGNs use the compact format. Existing automatic files are preserved; re-export existing tournaments for corrected opening moves and formatting. Full settings and measurements remain in SQLite; the optional technical archive includes base64-encoded settings headers for auditing.
- PGN append offsets are committed in the database after file flush. Startup repairs uncommitted tails and replays the outbox without duplicate attempts.
- Five verified SQLite backups rotate. Unchanged verified copies are reused; full-copy intervals adapt between one and fifteen minutes based on the preceding backup duration. Moves and results still commit transactionally throughout play. Worker & recovery displays backup progress and storage; shutdown shows copy/verification progress. A damaged database is quarantined before backup restoration; the recovered backup timestamp and possibility of missing newer data are reported explicitly.
- A forced application exit closes Windows job objects and kills engine descendants. On relaunch, committed results remain; unfinished attempts become interrupted, and the existing tournament opens paused for resume from its recorded openings.
- Save failures are visible and stop scheduling. Stop active games if necessary, resolve the storage issue, then use **Worker & recovery → Retry saving**. Recovery archives unfinished attempts rather than leaving them stuck as running.

## Statistics

Click a **Live standings** header to sort the whole field; click again to reverse it. Name, games, wins, draws, losses, points, score/draw percentages, Elo, interval width and LOS are sortable. The **#** column always retains the official tournament rank. Sorting and confidence preferences persist across restarts and apply to standings CSV/JSON exports. Reads run on a separate committed database snapshot so sorting does not queue ahead of game saves.

W-D-L and score/draw percentages use current official games. Opening-pair histograms update only when both legs have official results. Logistic Elo and normal-approximation LOS use paired samples when enabled. **Confidence level** offers 50, 68, 80, 85, 90, 95, 98, 99, 99.9 and 99.99%, plus custom percentages from 50 to 99.99. Choose normal approximation or conservative Hoeffding bounds. The selected level also applies to head-to-head, crosstable details, charts, pool ratings and reports; LOS and SPRT decision thresholds stay unchanged. Normal intervals can under-cover small samples, and zero-variance samples have unavailable normal uncertainty/LOS. Conservative bounds remain available but can be infinite. Both methods assume independent samples and fixed sample size; repeated viewing is not a sequential stopping rule. Aggregate Elo versus sampled opposition is not an anchored pool rating. See [statistical methods and calibration](docs/STATISTICS.md).

The tournament progress bar shows completed official games as a percentage of the currently scheduled total. After at least two new results and five seconds of observed active play, it estimates remaining time from recent completion pace. Pauses and restarts clear timing samples. Keep the tournament workspace open to collect timing; returning after an observation gap starts fresh. Knockout schedules may expand, and SPRT may finish before the scheduled maximum. The estimate changes with game lengths, engine speed and available concurrency.

In **Engine library**, use a row's **Delete…** button or select profiles and choose **Delete selected…**. Confirmation lists the affected profiles. This removes library registrations, including clones; engine files stay on disk. Existing tournaments and experiments retain their saved engine settings and results, including participants removed while play is running.

SPRT freezes the first stopping observation transactionally. Games already running can finish and update descriptive standings, but cannot move that boundary. A prescribed automatic retry is resolved before its opening pair enters the sequential sample. Manual official-result replacement invalidates sequential inference while preserving its original evidence; create a new test for a new sequential decision.

**Results & exports → Pool ratings** fits the tournament's connected comparison graph with a chosen reference engine and fixed rating (default: first participant at 0). Search participants, apply the reference and export all ratings as CSV/JSON. The fit uses normalized opening-pair scores when paired, with approximate sandwich intervals at the selected confidence level and LOS relative to the reference. It reports disconnected, separated or insufficient samples explicitly. The reference persists after restart; replacements reconcile automatically. Computation runs in a separate process at reduced CPU priority, using sparse comparisons and paged rows.

**Crosstable** shows row-engine scores against column engines, with independently paged axes and cell details. Head-to-head results also support opponent search and pagination. Display page sizes do not limit tournament participants.

## Display and experiments

**Display & layout** previews six vector piece designs (Classic, Studio, Outline, Geometric, Modern and Walnut), custom static SVG folders, board colors, dark/light themes and 12–24 px text. Hover over controls or focus them with the keyboard for contextual help. Long settings windows have a section index and retain the scheduled-game total above their action buttons. Drag panel handles between columns, resize their heights or the column divider, and save named layouts. Preferences live in the workspace database and survive app restarts. **Focused game** keeps the board and clocks together; **Engine search** shows evaluation, depth, nodes, speed, search time, hash, tablebase hits, reported WDL and the full PV. Both panels have **Float**, **Expand/Restore** and **Dock** controls. Floating windows stay inside the app: drag their headings and lower-right grips to move/resize them, or use arrow keys with those controls focused. The square board and panel text scale with available space. Window geometry survives restarts and named-layout saves. Search can follow the thinking engine or retain White’s/Black’s latest search, labelled with its move number. New searches clear stale measurements. Right-drag draws temporary analysis arrows; right-click marks a square.

**Live boards** offers 2, 4, 8, 16, 32, 64 or 128 boards. The list scrolls inside a bounded panel, so the header and corner grip remain accessible and old oversized panel heights cannot extend across many screens. Use **Size…** in its header to enter a height or choose **Fit to window**. **Float** also enables independent width, dragging and resizing; **Expand/Restore** uses the app area temporarily. Count and dimensions are saved with the workspace. This display choice does not change tournament concurrency.

**Add graph** creates independent monitoring panels for evaluation, mate distance, reported WDL, depth/seldepth, nodes/NPS, move time/clocks, hash occupancy, tablebase hits, host CPU/memory, score/draw trends, Elo with normal or conservative uncertainty, and the recorded SPRT likelihood/boundaries. Follow the focused live game or select a recorded game number. Each panel can be configured, hidden, removed, resized or moved; saved layouts include the graph definitions. Missing telemetry and node-only clocks remain unavailable. SVG and CSV export the displayed samples with labels and units. Long-game display sampling retains adjacent White/Black moves; all original moves remain in SQLite. Hardware graphs retain the latest 600 observations of the current UI session.

**Suites & benchmarks** runs EPD best/avoid-move accuracy cases and repeated thread-scaling measurements using selected profiles. Results retain engine/settings snapshots, elapsed search time, reported nodes and measured NPS. Cases recover independently after interruption. These jobs share the execution queue with tournaments.

Executable and discoverable network SHA-256 fingerprints are saved with tournament participants. If a recorded file changes, the tournament pauses and archives the unfinished attempt instead of awarding a chess loss. Restore the recorded file to resume; reconnect and save a profile to accept a new binary for a new test. Embedded or internally resolved networks are identified as unresolved rather than assigned invented file fingerprints.

## Reusable conditions and starting positions

**New tournament → Openings** offers a fresh position per color-reversed pair, one shared position per round, the same opening suite for every matchup, fresh unpaired games, or one fixed position throughout. Sequential and seeded-shuffle orders visit the unique pool before recycling; seeded random samples with replacement. Round-robin shared rounds give each engine one opponent per round (with byes for odd fields). These are scheduling rounds; independent games can overlap in execution. Both legs of a pair and all retries retain their recorded opening.

The opening capacity preview counts unique positions in FEN/EPD, PGN positions at the chosen depth, or all reachable positive-weight legal Polyglot branches at that depth or earlier book exit. Transpositions are merged; move counters do not make a new position. It shows basic paired/unpaired capacity, capacity for the selected preset and field, and the positions required by the schedule. Exhausting the pool repeats its recorded order, with a warning before creation. Elimination requirements are upper bounds because byes and playoffs depend on results. Large book inventories take time and memory; parsing runs off the game-clock event loop. Recorded inventories and shuffle order survive restart.

**Eval bar** in the Focused game or Live boards header opens visibility, linear/compressed scale, range in pawns, width and score-source controls. Bars use existing engine telemetry, with positive scores favoring White, mate labels, and an unavailable indicator when no score exists. Board flips move the White fill to the White edge. Range clips the graphic while preserving the actual numerical score. Pinning an engine can show its earlier search; hover for the source and move. Settings persist and are included in named layouts. Live bars are optional and work with the 128-card display; no extra analysis engines are launched.

**Time controls & presets** lets you edit the built-in 3m+2s conditions, save a copy, and set time control, threads, hash, Ponder and paired openings. Changes apply when creating a new tournament; existing tests retain their recorded settings. Independent profile time controls remain available for handicap comparisons.

Choose **Set up a position** to place or erase pieces, paste a FEN, change the side to move, castling rights, en-passant square and move counters, or generate any Chess960 start from 0 to 959. Invalid positions cannot be saved. In tournament setup, select **Saved starting position**; Chess960 rules follow that position automatically. Opening files have a separate Chess960 option. Recorded openings do not change when the saved library entry is edited.

**Opening & color results** provides live official W–D–L, score/draw percentages and completed opening pairs. Search for a tournament participant to compare its White and Black results, or select the overall White-side perspective. Opening and participant lists are paged, and CSV exports include every opening in the selected perspective. Diagnostic attempts never enter these totals; official replacements and invalidated rounds update them automatically.

**Tournament report** previews and saves a standalone HTML snapshot with standings, current results, termination reasons, preserved attempts, conditions and a settings fingerprint. Its concise standings table shows the first 50 participants; CSV/JSON retain the full field.

## Display & layout

In **Display & layout**, set **Font size** from 12 to 24 px (default 14), then choose **Apply display**. The setting scales interface text and controls and is saved before the dialog closes. The focused-game board automatically fits the panel's width and height; drag the panel's lower-right grip to resize it, or resize the application window. Clocks and analysis remain in a scrollable area when space is limited.

## Development

Completed-history storage has been benchmarked at 50,000 synthetic games with four million saved moves. Backups run separately from move saving, standings counts update transactionally, and official PGN downloads stream in bounded chunks. A further 2,304 complete real-engine games at 32 concurrent games and an application crash during backup have passed on that history, retaining 52,304 official results. See [validation scope](docs/BETA_VALIDATION.md); this is not a guarantee of constant performance at every database size.

The Windows shell is C#/.NET 10 WPF with WebView2. The interface uses HTML/CSS/JavaScript. The isolated worker uses Python 3.12, asyncio subprocesses, python-chess and a dedicated SQLite writer thread. Concurrent moves can share one durable commit; each game awaits commit before its next search. Engines run as native executable processes.

Create `.venv` with Python 3.12, install `requirements.lock.txt` for the tested dependency versions, then:

```powershell
.\.venv\Scripts\python.exe -m pytest tests --basetemp test-output\pytest -q
dotnet build desktop\EngineArena.csproj -c Release
.\scripts\build.ps1
```

Create `test-output` before directly invoking pytest. The build script does this automatically. `requirements.lock.txt` records the tested Python dependency versions. Source engine binaries used for validation are not redistributed in the application. The portable folder includes selected machine-readable validation evidence in `Validation`.

`scripts/real_validation.py` runs Stockfish/Berserk test configurations after their official binaries are placed in `validation-engines`. `scripts/desktop_crash_validation.py` force-kills the separate desktop test instance and verifies recovery. Use disposable validation data folders, as these tests intentionally interrupt games.

Engine Arena application source is GPL-3.0-or-later; see [LICENSE](LICENSE) and [NOTICE](NOTICE). The installer includes application source and third-party source/notices. Bundled runtimes and prerequisite installers retain their own licenses. Build instructions: [docs/BUILDING.md](docs/BUILDING.md).

### Game clocks and deleting tournaments

Live boards and Focused game show a separate clock for White and Black; the thinking engine is highlighted. Game history and saved-move replay also show recorded clocks. Pure node/depth controls show elapsed move time, without a chess-clock limit; fixed time per move is labelled separately.

To remove a tournament, select it in the tournament list and choose **Delete…**. Review the named confirmation, then choose **Delete tournament and data**. Stop or pause and drain all tournaments and experiments first. This deletes that tournament's settings, participant snapshots, games, attempts, moves, diagnostics, results, automatic PGN entries and recoverable backup records. Engine library profiles, reusable presets, other tournaments and copies exported elsewhere remain. Deletion cannot be undone through recovery backups. Database space becomes reusable; its file may not shrink immediately. Interrupted cleanup resumes on reopening or Retry saving.
