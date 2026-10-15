# Engine Arena 1.4.0 — private season-manager candidate

This update is for local acceptance testing. It has not been published.
The public version remains 1.2.14. Existing leagues retain their recorded rules,
engine snapshots, pairings, scheduling order and results when upgraded.

## Creating a competition

Save a source tournament containing the selected engine profiles and default test
conditions. In Events & leagues, choose **Create season competition…**. The source
is copied as a settings snapshot and is not run or consumed by the season manager.

Three editable presets cover independent divisions, progressive championships,
and qualification followed by league seasons. Field size is user-selected; there
is no fixed 64-engine ceiling. Division sizes may differ and must add up to the
field. Each division requires at least two engines. Choose movement counts at
each boundary (zero closes that boundary), seasons, paired cycles and a final.

In Division League, divisions can play concurrently within one shared resource
budget. Movements apply next season. In Progressive Championship, play starts
at the bottom. Promoted engines join the residents of the next division in the
same season. Relegations and retained places determine the next season's roster.
An engine can therefore reach the championship from the lowest division.

Qualification can be round robin or the existing club Swiss pairing system.
It places the entire field into divisions by results. Swiss is not an
implementation of TCEC's particular Monrad procedure or FIDE Dutch pairing.
Odd fields use the existing recorded bye policy. If no rematch-free Swiss pairing
exists, the event pauses for pairing review; it does not silently invent a round.

Choose saved tournament conditions independently for qualification, each division,
and the championship. These snapshot their time controls, opening inventory and
adjudication settings. An explicit stage override replaces per-engine clock
handicaps for that stage. Each division can have its own number of pairs per
matchup. All stages use color-reversed opening pairs. Each opening inventory and
seed has a recorded advancing cursor; independent divisions sharing the same
inventory start that phase from the same cursor. Subsequent stages advance beyond
the longest used sequence. Repetition is possible after an inventory is exhausted.

The preview shows the regular schedule before saving. Boundary playoffs and final
tiebreaks add games. Choosing an early-clinched final can reduce the planned final
length; it finishes the current opening pair before stopping. The default plays
all regular final games. Tied finals continue in complete pairs. Tiebreak controls
can be changed independently. Resource concurrency does not limit participant count.

## Placements, updates and history

Placement can use the source standings tiebreaks, or played playoffs for ties
crossing a division/promotion/relegation/championship qualification boundary.
Multi-engine playoffs use paired round robins, recursively resolving only the
still-tied boundary groups. Playoff points do not enter the original stage table.
No finite maximum guarantees a winner if engines continue drawing indefinitely.

Every new competition begins with a roster review. Then choose automatic
continuation, a review between seasons, or a review between stages. Engine updates
are permitted only in configured windows. Frozen versions remain fixed. Automatic
continuation keeps the approved versions and does not download engine updates.

At a review window, choose a registered replacement version. The GUI tests its
connection, supported options and readiness before committing it. Executable and
explicit network fingerprints are verified. Use separate version folders; replacing
a previously used executable at the same path is rejected. The engine family
keeps its league identity and earned place, but games/ratings retain their actual
version and settings. Updates do not retrospectively rename historical games.

At a season boundary, a new entrant can replace a withdrawn engine or join a
selected division. The division-assignment editor can withdraw participants or
adjust placements. Historical participants remain in earlier stages. Movement
validation must still succeed. Changing the number of divisions requires a new
competition. Adding another season prepares a review window, never starts games.

The event view shows stage history, live progress, results and champions. Open a
stage for its complete standings, Elo/CI/LOS, game history, report and PGN exports.
Event text/JSON reports describe the season rules, placement decisions, stage
conditions and updates. Stage ratings are not merged into an apparent uniform
rating across different versions, opponents and controls.

Correcting a result requires explicit invalidation of dependent stages. Original
attempts and superseded stages remain archived. The stage checkpoint restores its
recorded roster, opening cursors and rules before advancement is recalculated.

## Retire, fresh copy and delete

**Retire** stops future competition and retains its history. **Fresh copy** creates
an unstarted competition using the saved setup (for a season manager, the current
roster), with no games or results. Engine binaries and books are shared references.

**Delete event** removes the event and all linked stages, including qualification,
playoffs, finals, superseded stages and empty drafts. The event list supports
selected events or all events, with a preview before confirmation. Source
tournaments, engine installations, books, reusable presets and independently
exported files remain available. Source templates can be deleted separately.

Pause and drain all games/experiments first. Cleanup rewrites managed PGN streams,
clears report caches, removes records from managed recovery backups, compacts
storage and reports reclaimed managed-storage bytes. An independent durable
deletion receipt prevents an older managed backup from resurrecting the event.
Cleanup continues after interruption; saving errors are reported and scheduling
stops until resolved. The receipt retains opaque IDs, not games or engine settings.

## Installing this candidate

Let the current test finish, or Pause & drain the event and wait for zero active
games. Close Engine Arena, run the private installer and reopen. Existing tests
continue using their original rules; use a new season competition to test these
features. Nothing is published or deleted merely by installing this update.

## Candidate validation

The targeted backend review passed 187 distinct tests, including 19 season tests;
48 existing JavaScript checks passed. Browser acceptance covered three presets,
roster review, readable reports and deletion across all eight languages and 32
layout combinations. A 1000-engine fixture verified bounded game materialization.

The packaged desktop completed 52 real Stockfish/Berserk workflow games in both
season modes. All four PGN presets parsed legally; standings and completed pairs
reconciled. Forced termination preserved committed results and archived unfinished
attempts, then resumed the event. An old database snapshot kept 50 results and
eight legacy divisions. A between-season profile change preserved earlier games.
Deleting both test events removed 11 stages from the database and managed backups
and returned 13.8 MiB of test data to disk. These short checks do not replace the
owner's full season test or laptop acceptance. This candidate is not published.
