# Engine Arena 1.9.12

Engine Arena 1.9.12 is a maintenance update to 1.9.7, with startup and Rating Center fixes plus an optional opponent-rating-range comparison. It is the same application build Mark is using for the ongoing 400-entry, 159,600-game test.

**Designed by Mark Young. Coding and implementation by OpenAI Codex**, under Mark Young's direction.

## What changed

- **More reliable startup and closing.** Large workspaces have more time to open, with the current startup step and elapsed time displayed. Startup errors have a readable details panel. Closing during initialization cancels startup cleanly; normal closing still waits for saving and backups.
- **Interface loading fixes.** Corrects the `backupHealth is not defined` and `renderStandings is not defined` errors. Interface requests wait for the page scripts to be ready, without waiting for 3D assets.
- **Keep established ratings visible.** Entries with only wins or only losses no longer make established, connected Rating Center ratings disappear. Engines without enough comparison evidence remain listed with an explanation. The anchor stays fixed; no invented games or arbitrary finite ratings are added. The correction also applies to tournament pool ratings and related exports.
- **Optional opponent-range comparison.** In a single Rating Center time category, compare the full ratings with a recalculation using opponents within +/-100, 200, 300, 400 or a custom Elo range. The range is selected from the full-pool baseline, preserves complete opening pairs and uses the same anchor. Full and filtered ratings, rank changes, uncertainty and counted games are shown together. All opponents remains the default.

The opponent-range view is a sensitivity comparison, not a promise of more accurate ratings. Its intervals are conditional on the selected opponents. Official game records and full-scope W-D-L are retained; changing this view does not delete games.

## Downloads and updating

- **EngineArenaSetup-1.9.12-win-x64.exe**: complete offline installer, including Python, .NET, WebView2 setup, optional PawnIO setup and application source.
- **EngineArena-1.9.12-win-x64.zip**: smaller extract-and-run application with the same features and graphics. Python and .NET are included; Microsoft WebView2 Runtime must already be installed. Matching application source is available from this release's Source code downloads.

**Windows 11 x64 (Intel/AMD).** Pause and drain games, wait for active games to finish, close Engine Arena, then run setup in the existing installation folder. Intermediate updates are not required. Existing profiles, tournaments, events and ratings are retained. Leave optional WebView2 repair unchecked when the runtime already works.

For the ZIP, extract the entire archive into a fresh folder before launching EngineArena.exe. The ZIP creates no Start menu entries or uninstaller. Both downloads use the same default saved-data folder, `%LOCALAPPDATA%\EngineArena\Data`; close the other copy first. Use `--data` for a separate workspace. Add your own engines and opening books. Engine Arena itself is unsigned.

## Checks and current testing

The update's targeted checks passed: **98 backend tests and 102 JavaScript tests**, plus source and packaged Rating Center workflows, exports, eight-language interface checks and restart/evidence-preservation checks. A packaged fixture covered 61 configurations and 1,600 counted games. The 100,000-game synthetic rating-range benchmark completed its initial fit in approximately 0.91 seconds on the development computer; this is a bounded performance measurement, not a guarantee for every database or computer.

The installer is the exact tested 1.9.12 file. ZIP runtime files are verified against its installed payload manifest; distribution instructions differ. Some unchanged installer documents retain earlier private-test or release wording. These notes describe this update's scope.

The 400-entry tournament is still in progress. It is ongoing real-world testing, not a completed endurance result. Persistent tournament activity/uptime history is planned for a later update and is not included here.

[User guide](https://github.com/saintlouischess-eng/EngineArena/blob/v1.9.12/docs/USER_GUIDE.md) · [Report an issue](https://github.com/saintlouischess-eng/EngineArena/issues)
