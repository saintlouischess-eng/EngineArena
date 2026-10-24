# Engine Arena 1.10.3

This release brings the community-requested viewing and tournament workflows, round-robin roster changes, more reliable large-field ratings, and a correction to engine reply timing.

**Designed by Mark Young. Coding and implementation by OpenAI Codex, under Mark's direction.**

## New features since 1.9.12

1. **Follow an engine.** Select an exact engine profile in the focused game and automatically follow its games in the selected tournament. Its last board remains visible while it waits. Selecting another game manually exits follow mode.
2. **See how the game finished.** An adjustable finish hold displays the final position, result and termination before switching. Live boards also have Recent finishes. This affects viewing only; engines keep playing.
3. **Readable panels.** Independent, saved text sizes for standings, game attempts, the engine library, Rating Center and dense result dialogs, including floating and expanded panels.
4. **Understand tied standings.** Optional tiebreak values and Ranking explained show the actual criteria, values and seed fallback. The extra columns can stay hidden when space is limited.
5. **Change a round-robin field without starting over.** Pause and fully drain a standalone RR, then add, withdraw or replace entrants through RR roster. Newcomers can catch up first, interleave, or play after the existing schedule. Changes have a preview and are saved paused.
6. **Persistent activity history.** Review observed application sessions and tournament play, wait, pause and drain activity. Tracking starts with this version; offline gaps are not represented as uninterrupted uptime.
7. **Optional best-move arrows.** Show the current engine's legal primary-PV move on 2D or 3D boards, with an adjustable delay. Off by default; no extra analysis engine is started.
8. **More interface themes.** Midnight, Daylight, Charcoal, Deep Blue, Forest, Warm Parchment and High Contrast, with accent choices. Board materials and rooms remain separately configurable.
9. **Delete saved presets.** Remove unwanted test-condition presets. Deleted starter presets stay deleted, while already-created tournaments retain their saved conditions.
10. **Clearer rating identities.** Profile labels, short configuration IDs and details help identify the exact engine settings behind a rating and an anchor. Renaming a profile does not transfer historical ratings to a different configuration.

## Fair standings after replacements

When withdrawing entrants from a paused, drained standalone RR, choose whether to keep their completed results in standings and ratings, or **keep ratings only and exclude those games from tournament standings**. The latter removes their games from both opponents' tournament totals while preserving the original attempts, PGNs and historical rating evidence. Replacements earn their own results.

This allows a revised double RR to finish with equal counted games for its final field. Game counts remain unequal while catch-up is underway. Original roster revisions remain available. These roster changes do not apply to event stages or other tournament formats.

## Fixes

- **Large-field Rating Center stability:** fixes the numerical convergence problem that could make ratings disappear and later return as games were added. The rating model, anchor and saved games are unchanged; no reset or reimport is needed. A fresh calculation can still take several seconds.
- **Engine clock timing:** independent output readers timestamp complete engine replies. A reply received on time is no longer charged extra time merely because the application's main event loop processes it late. Genuine late replies still lose, and existing watchdog and pondering rules remain enforced. This cannot guarantee timing through a whole-system freeze.
- Retains the earlier startup, interface-loading and rating-retention corrections.

## Downloads and updating

- **EngineArenaSetup-1.10.3-win-x64.exe:** complete offline installer, including application source and optional runtime/driver setup.
- **EngineArena-1.10.3-win-x64.zip:** smaller extract-and-run package with the same application features and graphics. Python and .NET are included; Microsoft WebView2 Runtime must already be installed. Matching application source is available from this tag's Source code downloads.

**Windows 11 x64 (Intel/AMD).** Pause and drain running tournaments, wait for all active games to finish, close Engine Arena, then install over the existing version. Intermediate updates are not required. Profiles, games, tournaments and ratings are retained. Installing alone does not replay games or change past results.

For the ZIP, extract the entire archive into a fresh folder before launching EngineArena.exe. Both packages use the same default data folder, `%LOCALAPPDATA%\EngineArena\Data`; close the other copy first. Use `--data` for a separate workspace. The ZIP does not create shortcuts or an uninstaller. Add your own engines and opening books. Engine Arena itself is unsigned. Leave WebView2 repair unchecked if the runtime already works.

## Validation and ongoing testing

959 backend tests and 105 JavaScript tests passed, with 61 timing-focused tests also passing against code extracted from the packaged worker. Packaged withdrawal, replacement, restart, standings and retained-rating checks passed. The actual installer and runtime/source identity were verified.

The 400-entry, 159,600-game marathon is continuing. Seven replacement engines have caught up, and three specifically authorized replacement games finished normally and were verified in official standings and ratings. At the October 24 morning release review, 31,285 counted tournament games and 32,295 rating games reconciled exactly; the difference is 1,010 deliberately retained historical games. PGN saving and backups were healthy.

The 1.10.3 live run was about 32 minutes old at that review, alongside the controlled tests. This is ongoing real-world testing, not a completed month-long endurance claim. The exact trigger of the earlier overnight timeout incident remains unproven; the delayed-processing defect was reproduced and fixed separately. Some bundled documentation retains historical private-candidate wording; these release notes describe the public release.

[User guide](https://github.com/saintlouischess-eng/EngineArena/blob/v1.10.3/docs/USER_GUIDE.md) · [Report an issue](https://github.com/saintlouischess-eng/EngineArena/issues)
