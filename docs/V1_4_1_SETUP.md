# Engine Arena 1.4.1 — private test update

Designed by Mark Young. Coding and implementation by OpenAI Codex.

This update includes the private 1.4.0 Season Manager and addresses Jean-Paul
(Ipmanchess)'s engine-selection and configuration feedback. Public release is
pending the owner's tests. It does not change an existing tournament's conditions.

## Engine configuration

In Engine library, **Select all matching profiles** selects every profile matching
the search, including later pages. Clear the search to select the whole library.
**Clear selection** removes the selection without deleting engines.

**Bulk settings** now offers Threads, Hash, engine SyzygyPath, saved engine move
books, maximum book plies, book move selection and independent time controls.
Other UCI options accept an advertised name and value, including engine-native
book options. Use `true` or `false` for check options. Button commands are not
persistent settings. Ponder and variant remain tournament controls.

Imported profiles without option definitions show **Discover missing options**.
With games paused, it checks engines one at a time without searching and saves
their advertised options. Existing option values and executable fingerprints
are preserved. You can stop after the current engine; failures remain listed.

Only enabled changes are applied. Preview shows old/new values and skipped
options, including unsupported settings and values outside an engine's range.
The preview is paged. Applying uses a single transaction and rejects a stale
preview if profiles have changed. Already saved tournaments keep their snapshots.

For engine move books, import a PGN or BIN in an individual profile first, then
choose that saved book in Bulk settings. Changing only maximum plies preserves
each engine's existing book; profiles without a book are skipped. These books
choose moves for individual engines. A shared starting-position book remains
available in tournament setup, independently of engine move books.

## Tournament setup

Choose engines directly in the tournament dialog using search, paging and
selection controls. For a gauntlet, mark **Candidate** beside each intended
engine's name. Each candidate plays the remaining opponents, not other candidates.
At least one candidate and one opponent are required. The preview shows the
resulting game count before saving. The old numeric candidate field is hidden.

New, unsaved setups save automatically to the workspace database. Wait for
**Draft saved — safe to close**. Returning from Engine library, closing the dialog,
or restarting the application restores the draft. Time controls, KO tiebreak
sequences, openings, participants and other entered settings are retained.
**Start fresh** discards that unsaved draft. Successfully creating a tournament
clears it; rejected saves keep it. Saved-tournament editing still requires
**Save changes** and remains locked after its first start.

Only one new-tournament draft is retained per workspace. Concurrent-window edits
are detected instead of silently overwriting another draft. A failed draft save
is shown clearly; uncommitted input cannot be guaranteed after forced termination.

## Clocks and tablebases

Clock-tolerance shortcuts offer 0, 0.05, 0.25, 0.5 and 1 second, and custom values
remain available. Tolerance is grace before a time forfeit, including fixed time
per move. It is separate from charged overhead, engine Move Overhead and startup,
readiness or hang watchdogs. It does not impose a chess clock on node-only play.
The default remains 0.05 second; choose the allowance appropriate to your test.

The referee Syzygy directory enables **GUI adjudication** for covered positions.
It does not set engines' SyzygyPath or produce their TB-hit counts. Set engines'
SyzygyPath in Engine library or Bulk settings for engine probing. Missing material
tables leave the game running. Engines decide which searches report TB hits.
The earlier limited fixed-movetime diagnostics did not reproduce Ipman's timeout
rate; this release does not claim to fix an established timing defect.

## Installing the private update

Pause and drain active tournaments and events, close Engine Arena, then run
`EngineArenaSetup-1.4.1-win-x64.exe`. Keep the existing data folder. The installer
updates the program; it does not replace tournament results or engine profiles.


## Validation on October 9, 2026

- 110 distinct targeted Python tests passed, plus 12 release-resource checks.
- All 48 existing JavaScript checks passed.
- Browser workflows passed draft reopening/reload, KO staged controls, named
  gauntlet roles, bulk range warnings and successful/failed save feedback.
- Bulk API checked 1,100 profiles; browser selection and paging checked 510,
  including 505 selected profiles for one bulk operation.
- All eight language catalogs passed (3,674 messages each). Layout checks passed
  32 combinations of language, theme and window width.
- Packaged Windows app completed 16 capped real-engine workflow games with no
  engine failures: eight node-only and eight fixed-time-per-move games.
  Four PGN presets parsed with legal moves and reports were generated.
- Imported-profile option discovery passed stop/resume, unchanged saved options,
  stale-update rejection and refusal while games are active.
- Forced termination of the disposable packaged app preserved the committed
  unsaved setup after restart. Later bulk edits preserved tournament snapshots.

These were workflow/regression checks on the development PC. They do not replace
Ipman's testing on his computer or establish the cause of his reported timeouts.
