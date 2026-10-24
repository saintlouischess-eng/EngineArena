# Engine Arena

**Engine Arena 1.10.3** is a Windows desktop application for chess-engine testing, automated tournaments and seasons, live analysis, and playing against engines.

**Designed by Mark Young. Coding and implementation by OpenAI Codex**, under Mark Young's direction.

[Download installer or ZIP](https://github.com/saintlouischess-eng/EngineArena/releases/tag/v1.10.3) · [User guide](docs/USER_GUIDE.md) · [Release notes](docs/RELEASE_1_10_3.md) · [Report an issue](https://github.com/saintlouischess-eng/EngineArena/issues)

## Install or update

**Windows 11 x64 (Intel/AMD).** Choose the complete **EngineArenaSetup-1.10.3-win-x64.exe**, or the smaller **EngineArena-1.10.3-win-x64.zip** extract-and-run download. Both have the same features and graphics. The ZIP requires an existing Microsoft WebView2 Runtime; the installer includes its offline setup. Python and .NET are included in both.

Pause and drain games, then close Engine Arena. Run setup in your existing installation folder, or extract the entire ZIP into a fresh folder and launch `EngineArena.exe`. You can update directly from an earlier release; intermediate updates are not needed. Saved profiles, tournaments, events and ratings are stored separately and retained. The ZIP creates no Start menu shortcuts or uninstaller. Engine Arena itself is unsigned.

Both packages use `%LOCALAPPDATA%\EngineArena\Data` by default. Only one copy can open that workspace at a time. Use `EngineArena.exe --data "D:\Engine Tests\Arena"` for another local workspace. Add your own chess engines and opening books; engine executables are not bundled. Supported CPU temperature/core-clock readings use an optional signed PawnIO driver and elevated sensor reader. Leave optional WebView2 repair unchecked when your runtime works.

## New in this release

Follow an engine, adjustable final-result hold, readable panel text sizes,
optional tiebreak values, PV arrows, seven interface themes, deletable presets,
persistent activity history, and clearer rating identities. Standalone round
robins support add/withdraw/replace after pause and drain, with newcomer catch-up
and optional ratings-only retention of withdrawn engines' games. Large-field
rating convergence and delayed engine-reply timing are corrected.
See [release notes](docs/RELEASE_1_10_3.md) for scope, workflow and limitations.

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

959 backend tests and 105 JavaScript tests passed, plus 61 timing-focused tests
against the packaged worker's code. Packaged roster replacement, restart,
standings, PGN and retained-rating checks passed. Installer/ZIP integrity and
corresponding source are verified. The 400-entry marathon is still running;
this is not a completed endurance claim. See [validation and limits](docs/RELEASE_1_10_3.md).

## Build and source

The Windows shell is C#/.NET 10 WPF with WebView2; the interface uses HTML/CSS/JavaScript. A separate Python 3.12 worker uses asynchronous engine communication and transactional SQLite storage. Chess engines execute as separate native processes.

See [build instructions](docs/BUILDING.md). Matching source is in this repository/tag and GitHub's **Source code** downloads. The full installer also includes it in `Source`; the smaller application ZIP omits that duplicate folder. Both retain third-party notices and applicable dependency-source archives. Runtime code/assets match the tested installer; release documentation was finalized afterward.

Engine Arena application source and original artwork are **GPL-3.0-or-later**. Bundled components retain their own licenses. See [LICENSE](LICENSE), [NOTICE](NOTICE), [third-party notices](docs/THIRD_PARTY.md) and [credits](CREDITS.md).
