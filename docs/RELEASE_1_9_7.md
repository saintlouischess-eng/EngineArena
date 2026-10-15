# Engine Arena 1.9.7 — stable release

Released October 14, 2026. This release brings the work since 1.2.14 into one public update.

**Designed by Mark Young. Coding and implementation by OpenAI Codex**, under Mark Young's direction.

## Choose your download

- **EngineArenaSetup-1.9.7-win-x64.exe** — the complete offline installer, including Python, .NET, Microsoft WebView2 setup, optional PawnIO setup, and corresponding application source. Recommended for first-time installation and ordinary updates.
- **EngineArena-1.9.7-win-x64.zip** — a smaller extract-and-run package with the same application, boards, rooms, pieces and features. Python and .NET are included. Microsoft WebView2 Runtime must already be installed; use the full installer if it is missing. The ZIP omits the offline WebView2 installer and the duplicate application-source folder. Matching source is available from this release's **Source code** downloads and the [v1.9.7 source tree](https://github.com/saintlouischess-eng/EngineArena/tree/v1.9.7).

Both downloads target **Windows 11 x64 (Intel/AMD)**. Extract the ZIP completely before starting `EngineArena.exe`; do not run it from inside the archive. Extract a new version into a fresh folder. The ZIP does not create Start menu entries or an uninstaller. It uses the same default `%LOCALAPPDATA%\EngineArena\Data` workspace as the installed application; it is an application ZIP, not a separate copy of your saved tournaments. Close the other copy first. Use `EngineArena.exe --data "D:\Engine Tests\Arena"` for a different local workspace.

Pause and drain active games, close Engine Arena, then update. Existing profiles, events, games and ratings are retained; intermediate development updates are not required. Leave optional WebView2 repair unchecked when your runtime already works. Add your own engines and opening books. Engine Arena itself is unsigned; bundled prerequisite installers retain their upstream signatures.

## Main additions since 1.2.14

- **Rating Center:** automatic cross-tournament ratings, separate time-control categories, thread/GPU configurations, optional rating anchors, engine-family views and best-version filtering. Compact evidence can remain after tournament deletion; collection and retention default to on. Ratings can also be reset or removed explicitly.
- **Configurable seasons and events:** qualification, division placement, admission/field-size controls, promotion/relegation, roster reviews and engine-version updates. Custom competitions link stages with different supported formats, time controls and advancement rules. Championship matches support continuing tiebreaks. Season dashboards, engine careers and readable summaries show the full competition.
- **Player Arena:** play engines with click or drag moves on the 2D/3D boards, engine books, time controls, tenth-second clocks, resign/draw controls, challenge series, separate personal ratings, thinking/move panels, sounds and PGN saving. Panels resize, dock and float.
- **Board and room customization:** detailed 1849-style Staunton and Tal 1962 pieces; walnut/maple and purpleheart/maple board options; lighting/material choices, photographic rooms and a separate animated chess club. Camera tours, low-angle viewing, saved framing, 4K photographs and remembered photo destinations. The live club is capped at **30 FPS**; room motion can follow Windows preferences, animate, or remain still.
- **Workflow improvements:** stronger library bulk controls and deletion, retained engine selections during setup, clearer event-stage navigation, scalable scoresheets and search panels, focused-board sound, and a fifty-/seventy-five-move rule counter.
- **Extend completed round robins:** add new engines to a completed standalone round robin while preserving earlier results and scheduling only the missing matchups. Preview the added games first. Event stages, Swiss and knockout tournaments are excluded from this extension workflow.

Existing features remain: ten tournament formats, simultaneous tournaments with shared resource budgets, queues, Banksia/Cute Chess profile importing, independent engine books, all supported time controls including pure fixed nodes, SPRT, suites/benchmarks, failure replays/replacements, automatic PGNs, transactional recovery, selectable confidence intervals and eight interface languages.

## Final corrections

Completed-event summaries now identify the actual championship season and final-match score, distinguish placement-playoff records and avoid repetitive panels/conditions. Quick match PGN saving and focused-board sound after resizing were corrected. Opening replay shows the proper move number. Adding drafts with equal creation timestamps preserves their creation order. The bundled multidict dependency is updated to 6.9.1 for its upstream reference-leak fix. CPU rating comparisons remain compatible across recorded Windows/display-driver maintenance updates.

## Validation

- **850 Python tests and 96 JavaScript tests passed**, with independent statistical references for Elo, confidence intervals, LOS, SPRT and pool ratings.
- Packaged checks covered all ten formats, 402 short lifecycle games in 38 tournaments, five event configurations, two seasons, 20 queued tournaments and six suite/benchmark runs.
- Recovery checks covered forced termination, unfinished attempts, failed PGN writes, interrupted backups, diagnostic replays, official replacements and retained original attempts.
- A separate **256-game node-controlled run at up to 28 concurrent games** passed with live boards/graphs and exports. Deleting those test tournaments reclaimed **98.60%** of measured managed storage while preserving all 256 compact rating records in the database and both backups.
- The owner installed the update. A further **12-game round robin using the installed build** passed with four engines, fractional increments, no failures, all four PGN presets, reports, rating reconciliation and unchanged results/PGN after restart.
- Player Arena, long move history, sound/resizing, event summaries, eight languages and graphics context recovery were checked. Installer payload verification covered **2,445 files**.

Short tests are functional checks, not engine-strength measurements or guarantees for every engine and driver. Graphics recovery/resource tests use software WebGL and simulated context loss; this review did not repeat overnight physical-GPU testing. Large exports and first technical reports still scale with archive size. CPU temperature/core-clock readings require supported hardware and the optional elevated sensor reader.

## Package identity and source

The installer is the exact tested 1.9.7 file, unchanged for publication. Its bundled documentation retains the earlier candidate wording. This release page, public README and ZIP instructions record the subsequent approval. ZIP executable, worker, UI and assets are identical to that installer; only distribution documentation and source-folder packaging differ.

Installer: **900,295,604 bytes**. SHA-256:
`c9598018d90fb3db7931c5373cf5995c30d4a4f0479e97c72dbb2e3593acddfd`

The release includes SHA-256 checksums and a concise validation receipt for both downloads. Application source and original artwork are **GPL-3.0-or-later**; third-party authorship/licenses remain in the packages. [Credits](../CREDITS.md) · [User guide](USER_GUIDE.md) · [Feedback](https://github.com/saintlouischess-eng/EngineArena/issues)
