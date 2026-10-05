# Engine Arena

**Engine Arena 1.2.14** is a Windows desktop application for testing UCI chess engines, running reproducible tournaments, and reviewing live results.

**Designed by Mark Young. Coding and implementation by OpenAI Codex**, an AI coding assistant working under Mark Young's direction.

[Download the Windows installer](https://github.com/saintlouischess-eng/EngineArena/releases/latest) · [User guide](docs/USER_GUIDE.md) · [Release notes and validation](docs/RELEASE_1_2_14.md) · [Report an issue](https://github.com/saintlouischess-eng/EngineArena/issues)

## Install or update

Download **EngineArenaSetup-1.2.14-win-x64.exe** from the release page. Close Engine Arena, run setup, and use the same installation folder when upgrading. Saved engines, tournaments and settings are stored separately and are preserved. Pause and drain games before closing for an update.

The single installer includes the Python and .NET runtimes, offline Microsoft WebView2 setup, and optional signed PawnIO setup for supported CPU sensors. Leave optional WebView2 repair unchecked when the runtime already works. Add your own engines and opening books; engine binaries are not bundled. Supported target: **Windows 11 x64 (Intel/AMD)**. The Engine Arena installer itself is unsigned.

Launch from the Start menu. Results normally live in `%LOCALAPPDATA%\EngineArena\Data`. To select another local workspace, launch `EngineArena.exe --data "D:\Engine Tests\Arena"`. Only one worker can open a workspace. Shared resource budgets apply within that workspace.

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

Version 1.2.14 corrects Windows CPU-polling stalls that could delay engine replies, handles UCI option capitalization consistently, clarifies automatic-thread imports, and includes upright, depth-tested 3D coordinates. The owner confirmed successful laptop installation and operation, including the 3D board fix.

The release review passed 514 backend tests and 48 JavaScript tests, independent statistical checks, all ten formats, events/leagues, experiments, shared CPU/GPU scheduling, forced termination/recovery, failed-result replacement, saving-failure handling, reports and PGNs. It included a 56-game eight-engine round robin, 256 full node-controlled games at 32 concurrency, and a synthetic 50,000-game/four-million-ply archive for storage and deletion checks. All eight packaged interface languages were exercised.

These checks do not guarantee compatibility with every engine or driver. Initial technical reports and large PGN exports still take time proportional to stored data; cached reports are faster. The synthetic archive is a scale check, not a new endurance run. See [release validation and limits](docs/RELEASE_1_2_14.md). Earlier candidate documents retain their historical test scope.

## Build and source

The Windows shell is C#/.NET 10 WPF with WebView2; the interface uses HTML/CSS/JavaScript. The isolated Python 3.12 worker uses asynchronous engine communication and SQLite transactional storage. Chess engines execute as separate native processes.

See [build instructions](docs/BUILDING.md). Application and corresponding third-party source/notices are also included in the installer. The public application code and assets match the tested installer; release documentation and credits were finalized afterward without rebuilding that installer.

Engine Arena application source and original artwork are **GPL-3.0-or-later**. Bundled components retain their respective licenses. See [LICENSE](LICENSE), [NOTICE](NOTICE), [third-party notices](docs/THIRD_PARTY.md) and [credits](CREDITS.md).
