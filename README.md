# Engine Arena

**Engine Arena 1.9.7** is a Windows desktop application for chess-engine testing, automated tournaments and seasons, live analysis, and playing against engines.

**Designed by Mark Young. Coding and implementation by OpenAI Codex**, under Mark Young's direction.

[Download installer or ZIP](https://github.com/saintlouischess-eng/EngineArena/releases/tag/v1.9.7) · [User guide](docs/USER_GUIDE.md) · [Release notes](docs/RELEASE_1_9_7.md) · [Report an issue](https://github.com/saintlouischess-eng/EngineArena/issues)

## Install or update

**Windows 11 x64 (Intel/AMD).** Choose the complete **EngineArenaSetup-1.9.7-win-x64.exe**, or the smaller **EngineArena-1.9.7-win-x64.zip** extract-and-run download. Both have the same features and graphics. The ZIP requires an existing Microsoft WebView2 Runtime; the installer includes its offline setup. Python and .NET are included in both.

Pause and drain games, then close Engine Arena. Run setup in your existing installation folder, or extract the entire ZIP into a fresh folder and launch `EngineArena.exe`. You can update directly from an earlier release; intermediate updates are not needed. Saved profiles, tournaments, events and ratings are stored separately and retained. The ZIP creates no Start menu shortcuts or uninstaller. Engine Arena itself is unsigned.

Both packages use `%LOCALAPPDATA%\EngineArena\Data` by default. Only one copy can open that workspace at a time. Use `EngineArena.exe --data "D:\Engine Tests\Arena"` for another local workspace. Add your own chess engines and opening books; engine executables are not bundled. Supported CPU temperature/core-clock readings use an optional signed PawnIO driver and elevated sensor reader. Leave optional WebView2 repair unchecked when your runtime works.

## New in this release

- **Rating Center:** automatic cross-tournament ratings, optional anchors, time categories, thread/GPU configurations, best-version family views and compact rating retention after tournament deletion.
- **Seasons and events:** qualification, division placement, configurable admission/field limits, roster/version reviews, promotion/relegation, custom multi-stage competitions and championship tiebreaks, with careers and shareable summaries.
- **Player Arena:** human play with mouse click/drag, books, clocks, thinking panels, sounds, PGNs, challenge series and separate personal ratings.
- **Viewing:** detailed 1849 and Tal 1962 3D pieces, additional wooden boards, photographic rooms, an animated chess club, camera tours, low-angle views and 4K photos. Live-room rendering is capped at 30 FPS.
- **Polish:** extend completed standalone round robins, bulk engine removal, clearer event summaries, draw-rule counters, long scoresheets, dependable resize/sound behavior and improved queue ordering.

## Testing and tournament features

- **Formats:** match, round robin, gauntlet, Swiss, knockout, double elimination, ladder, self-play, custom matchups and two-engine SPRT. Linked events support qualifying stages and finals; leagues support divisions, promotion and relegation.
- **Tournament manager:** prepare tournaments in advance, edit them before their first start, queue them, or run independent tournaments together. Shared CPU, memory, GPU and game limits control admission. Individual priorities, pause/drain controls and live concurrency changes help manage a busy machine. Participant counts are independent of the number of running engine processes.
- **Engine profiles:** discover UCI options, clone configurations, import compatible Cute Chess/Banksia profiles, and set independent threads, memory, GPU groups and time controls. Participants retain their recorded settings and discoverable engine/network fingerprints.
- **Time controls:** sudden death, Fischer increment, simple/Bronstein delay, staged and repeating controls, fixed move time, depth, and pure `go nodes N` without a chess-clock limit. Readiness and hang watchdogs are separate.
- **Openings:** shared PGN/EPD/FEN/Polyglot starting positions, paired or unpaired games, seeded selection, capacity previews, and optional per-profile PGN/Polyglot move books. Two copies of the same engine can play moves from different books.
- **Live results:** sortable standings, W-D-L, score/draw percentages, head-to-head, completed opening pairs, Elo estimates, configurable confidence intervals, LOS and anchored pool ratings. Visible time-forfeit counters lead to the original failure attempts.
- **Recovery and review:** transactional move/result saving, rotating verified backups, preserved interrupted attempts, automatic retries, diagnostic replays and explicit official replacements. Later-round dependencies are handled explicitly. Deletion and storage maintenance reclaim space in the database and affected backups.
- **Experiments:** EPD suites, fixed-node/depth/time benchmarks and thread-scaling comparisons with saved conditions and readable results.

## Viewing and exports

The configurable workspace offers up to 128 live board cards, focused-game clocks and move scoresheets, engine search and best-move history, evaluation bars, graphs, replay, font sizes, themes and saved layouts. Optional wooden 3D viewing includes detailed 1849-style Staunton pieces, lighting, zoom, vertical framing and traditional kingside crown marks. Hover help and the 3D controls can be hidden.

Hardware displays offer selectable CPU, memory, storage and supported NVIDIA GPU readings. Supported CPU temperature/core-clock sensors use a separately elevated reader and the optional driver. Missing readings are shown as unavailable.

Interface languages: **English, Spanish, French, German, Portuguese, Italian, Dutch and Polish**.

Automatic PGNs preserve completed attempts. Export presets range from clean games to annotated engine testing and full archives, with header/annotation controls and a destination picker. Reports, standings and other applicable views offer readable text, CSV, JSON or standalone HTML; graphs offer SVG/CSV. Original attempts remain available when an official result is replaced.

Useful guides: [Tournament manager](docs/SIMULTANEOUS_TOURNAMENTS.md), [knockout](docs/KNOCKOUT.md), [events and leagues](docs/EVENTS.md), [SPRT](docs/SPRT.md), [opening books and TF counters](docs/ENGINE_BOOKS_AND_TF.md), [PGN exports](docs/PGN_EXPORTS.md), [statistics](docs/STATISTICS.md), [hardware](docs/HARDWARE.md), [storage](docs/STORAGE.md).

## Release checks

850 Python tests and 96 JavaScript tests passed. Packaged validation exercised all ten formats, multi-stage seasons, suites/benchmarks, statistics, recovery, failed-game replacements, reports, all four PGN presets, storage cleanup and eight languages. A 256-game load check used up to 28 concurrent games; deletion reclaimed 98.60% of the measured managed storage while preserving compact rating records. A further 12-game round robin passed after the owner installed this exact build.

These are bounded functional and scaling checks, not a guarantee for every engine or driver. Graphics context-loss tests do not substitute for physical-GPU endurance. See [validation and limits](docs/RELEASE_1_9_7.md). Earlier version documents retain their historical candidate status.

## Build and source

The Windows shell is C#/.NET 10 WPF with WebView2; the interface uses HTML/CSS/JavaScript. A separate Python 3.12 worker uses asynchronous engine communication and transactional SQLite storage. Chess engines execute as separate native processes.

See [build instructions](docs/BUILDING.md). Matching source is in this repository/tag and GitHub's **Source code** downloads. The full installer also includes it in `Source`; the smaller application ZIP omits that duplicate folder. Both retain third-party notices and applicable dependency-source archives. Runtime code/assets match the tested installer; release documentation was finalized afterward.

Engine Arena application source and original artwork are **GPL-3.0-or-later**. Bundled components retain their own licenses. See [LICENSE](LICENSE), [NOTICE](NOTICE), [third-party notices](docs/THIRD_PARTY.md) and [credits](CREDITS.md).
