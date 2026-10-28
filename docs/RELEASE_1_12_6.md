# Engine Arena 1.12.6 — Broadcast Designer and Viewing Improvements

This release adds a configurable broadcast workspace for OBS and other browser-source capture tools. It also includes the rating, focused-game and cleanup improvements developed since public version 1.10.3.

**Designed by Mark Young. Coding and implementation by OpenAI Codex, under Mark's direction.**

## Broadcast Designer

- Create a show with movable, resizable panels, saved scenes, undo/redo, private preview, import/export and twelve editable starting presets for matches, leagues, large tournaments and other layouts.
- Choose the tournament to broadcast, or use an event playlist. The broadcast output remains separate from ordinary Engine Arena workspaces, so using the rest of the application does not change the show.
- Follow selected games from their opening through their official finish. The director waits for fresh games, shows all their moves, and holds the final position and result. Automatic scene/event changes respect game boundaries; an explicit cut remains available.
- Use 2D or 3D boards, the application's themes and piece sets, wood finishes, rooms and camera options. Configure thinking-arrow color and added delay from 0 to 10 seconds. Three-dimensional rendering remains capped at 30 FPS.
- Choose from 23 panel types, including the board, match score, standings, Rating Center, moves, thinking, graphs, results, progress, conditions, text and images.
- Set entry limits, rows per page, rotation intervals and independent text sizes. Rotating tables finish the selected standings pages before showing the selected ratings pages. Elo badges beside the players identify the exact recorded configurations where a matching rating is available.
- Show both engines on one graph, or one at a time, with configurable colors and line, dotted-line, bar, area, step or dot styles. Available search metrics include evaluation, depth, nodes, NPS and clock time.
- Configure scrolling tickers or stationary headlines, speed, colors, spacing, custom messages and included events. Result headlines show engine ratings and clearly describe an upset as beating a higher-rated opponent, not gaining that many rating points. Scrolling content changes between complete passes.
- A larger header presents progress, engine count and an estimated finish when enough pace information exists. A compact result display preserves the final board position. Standings and ratings use stronger type for TV and phone viewing.
- The latest polish removes the embedded graph and opening-book line from Moves & thinking to make space for readable text. Dedicated graphs remain available. Depth and compact NPS stay visible beside long engine names.
- Open OBS at verified Normal process priority from the designer. Optional board sounds are supported. Starting the broadcast output does not start a public stream; streaming remains under the operator's control in OBS/YouTube.

## Other improvements since 1.10.3

- Eight additional colorful interface themes, while retaining the earlier themes.
- Saved rating/CI display choices: full interval bounds or plus/minus, and independent 0, 1 or 2 decimal places. These change presentation, not the rating calculation.
- Search several engine names or families together in Rating Center, separated by commas or semicolons.
- Follow winning games using a sustained engine-reported advantage, with adjustable confirmation and switching rules. An evaluation is an estimate, not a guaranteed win.
- Show/hide the focused game's draw-rule counter and collapse its controls to give the board more space.
- Select official-results or all-attempts TF counts, preserving access to earlier attempts after an official replacement.
- Faster tournament and rating deletion: routine cleanup no longer automatically compacts the entire shared database. Freed pages can be reused; explicit Reclaim disk space remains available. Large backup copies can still take time to update safely.

All earlier tournament, season, ratings, recovery and engine-reply timestamp fixes remain included.

## Downloads and updating

- **EngineArenaSetup-1.12.6-win-x64.exe** — full offline Windows installer, including matching application source and optional runtime setup.
- **EngineArena-1.12.6-win-x64.zip** — smaller extract-and-run package with the same runtime, boards, rooms and features. It omits duplicate application source and offline WebView2 setup; matching source is available at this release tag. Dependency notices and applicable dependency source remain bundled.

**Windows 11 x64 (Intel/AMD).** Pause and drain running tournaments, wait for active games to finish, end any live stream, then close Engine Arena before updating. Install over the existing version, or extract the entire ZIP into a fresh folder. Intermediate updates are not required. Saved engines, games, tournaments and ratings are retained. Installing does not replay or change old results.

Python and .NET are included. The ZIP requires Microsoft WebView2 Runtime already installed. Both packages use the same default saved-data folder; close the other copy first, or use `--data` for a separate workspace. Add your own engines and opening books. The application is unsigned. OBS is separate software and is not bundled.

Open **Broadcast → Open Broadcast Designer**, choose a preset and tournament, review the preview, then apply to output and add its local program URL as an OBS Browser Source. Keep control URLs private. Leave Engine Arena and OBS running while broadcasting. See the [Broadcast Designer guide](https://github.com/saintlouischess-eng/EngineArena/blob/v1.12.6/docs/BROADCAST_DESIGNER.md).

## Validation

For the final 1.12.6 build, 33 focused Python tests, 26 JavaScript tests, eight isolated layout workflows and eight packaged-helper checks passed. Asset matching, package-manifest checks and archive integrity passed. The public ZIP is verified against the tested installer payload; runtime code is unchanged by release packaging.

The 400-entry, 159,600-game marathon remains in progress, with more than 47,000 counted games. The installed 1.12.6 build has resumed with 28 active games; new official results reconcile with Rating Center and rotating backups are working. The owner closed and reopened Codex, and the same Arena, worker and OBS processes continued. This verifies this Windows-shortcut launch workflow; it is not a new application crash fix or a completed endurance claim for 1.12.6. OBS reported no rendering/encoding skips during the release check; occasional network drops are separate from those counters.

[User guide](https://github.com/saintlouischess-eng/EngineArena/blob/v1.12.6/docs/USER_GUIDE.md) · [Report an issue](https://github.com/saintlouischess-eng/EngineArena/issues)
