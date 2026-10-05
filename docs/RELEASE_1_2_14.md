# Engine Arena 1.2.14 — stable release

Released October 5, 2026. This is Engine Arena's first stable public release, following the earlier 0.2.0 betas and local release candidates.

**Designed by Mark Young. Coding and implementation by OpenAI Codex**, an AI coding assistant working under Mark Young's direction.

## Download and update

Download **EngineArenaSetup-1.2.14-win-x64.exe** from [this release](https://github.com/saintlouischess-eng/EngineArena/releases/tag/v1.2.14). Windows 11 x64 (Intel/AMD). Close Engine Arena before updating and keep the existing installation folder. Saved profiles, tournaments and settings are preserved; no tournament reset is required.

The one-file installer includes Python, .NET, offline WebView2 setup and optional signed PawnIO setup. Leave WebView2 repair unchecked when the installed runtime works. Supply your own chess engines and books. The Engine Arena installer itself is unsigned.

## Included since Beta 2

- Ten tournament formats, custom matchups, linked qualifying events and leagues with promotion/relegation; configurable KO matches and continuing tiebreak play.
- Tournament setup editing before first start, automatic queues, and simultaneous independent tournaments sharing CPU, memory, GPU and game budgets.
- Independent engine move books alongside common tournament openings; live time-forfeit counters and preserved failure history.
- Full time-control choices including fractional increments and pure fixed nodes; separate readiness/hang watchdogs and adjustable clock tolerance.
- Live standings and statistical comparisons, configurable confidence levels, paired/unpaired statistics, anchored ratings, EPD suites and benchmarks.
- Transactional recovery, automatic PGNs, retries, diagnostic replays, official replacements, and storage cleanup that also updates affected recovery copies.
- Refined workspaces, scalable boards/clocks, move scoresheets, compact search history, graphs, evaluation bars, multiple SVG piece sets and optional detailed wooden 3D viewing.
- Eight interface languages; readable reports/text exports; PGN presets with selectable headers/annotations and save destinations.

See the [user guide](USER_GUIDE.md) and [README](../README.md) for setup and scope.

## Final corrections

Windows CPU status queries now use cached readings. The background native CPU reader releases Python's interpreter lock, avoiding the polling stalls found during review. Best-move receipt is timestamped before reader fairness yields.

Saved UCI option names are matched consistently regardless of capitalization, preventing thread/hash overrides from disagreeing with resource budgets. Import previews explain when automatic (zero) threads are converted to an explicit one thread. Existing tournament snapshots retain their settings.

The 3D board's letters and numbers stay upright as the view changes and are hidden by nearer pieces. Theme-button translations were also corrected.

## Validation

- **514 backend tests and 48 JavaScript tests passed**, plus independent score/Elo/CI/LOS, SPRT and pool-rating references.
- All ten formats were exercised paired/unpaired; 38 tournaments/402 short lifecycle games, events/leagues and 30 suite/benchmark cases passed.
- An instrumented eight-engine round robin completed **56 full games / 8,021 legal plies**, with one-second clock tolerance and no timeout/crash/hang/illegal-move failures.
- A separate load check completed **256 full node-controlled games at 32 concurrency**, with live-board/graph and export phases.
- Shared CPU/Lc0 admission, forced termination, interrupted attempts, saving-failure retry, original-attempt preservation and official replacement passed. A further 84-game integration check covered books, fractional controls, live concurrency and recovery.
- A **50,000-game synthetic archive with four million plies** exercised reports, exports, storage and deletion. Deletion reclaimed about **6.58 GB** of managed files, with integrity checks on the main database and all retained recovery copies.
- Packaged checks covered all eight languages, PGN presets, reports and 3D controls/orientations. The owner confirmed successful laptop installation and normal operation, including the 3D board fix.

Short lifecycle checks are not strength measurements. The synthetic archive is not a new endurance tournament. These checks do not guarantee every engine/driver combination or constitute testing on a fresh Windows image. Initial full technical reports and large PGN exports still scale with archive size; cached reports are much faster.

## Artifact identity

The published installer is the exact laptop-tested build; it was not rebuilt for the release announcement or credits. Its bundled documentation records the earlier candidate status. This page and the release receipt record the subsequent laptop approval and publication.

- File: `EngineArenaSetup-1.2.14-win-x64.exe`
- Size: **340,279,489 bytes**
- SHA-256: `1086cbe6534731c0600d611905ba787ef413ce15244ab7577992f5b2b0029cb5`

Source: **GPL-3.0-or-later**. [Credits](../CREDITS.md) · [Feedback and issues](https://github.com/saintlouischess-eng/EngineArena/issues)
