# Engine Arena 1.2.0 — game viewing and setup

Local candidate for owner testing. Designed by Mark Young. This update has not
been published to GitHub and does not add native WinBoard support.

## Game moves

Open **Game moves** from the Focused game heading, or enable it in **Display &
layout**. It is a separate dockable, floating, resizable panel with its own text
size. The compact scoresheet shows SAN, move numbers, evaluation, depth/selective
depth and measured move elapsed time. **More stats** adds nodes, NPS and the
moving engine's recorded remaining clock.

Select a move to review its position and frozen recorded clocks. **Return to
live** restores live updates; **Final position** returns to a finished game's
last position. Engine search continues to show the current live search, so it is
separate from the recorded scoresheet. Scores use White's perspective *before*
the played move; they are not a fresh analysis of the resulting position.
Missing measurements show a dash. Verified opening history appears as Book;
FEN-only positions do not acquire invented preceding moves.

Move pages contain at most 200 searched/played moves and append incremental
updates. Earlier/later buttons browse long games. Reading or scrolling older
moves preserves your position. The displayed attempt is identified explicitly,
including diagnostic/replacement and whether it is currently official. Use the
existing **Replay** dialog to inspect every preserved earlier attempt.

**Follow next game** is on by default. It follows another active game after the
selected game finishes, but pauses while reviewing a recorded move. Turn it off
to keep the selected game. When no games remain active, the final focused game
stays visible.

## Optional 3D focused board

Choose **2D / 3D** in the Focused game heading. 2D remains the default and uses
the selected SVG pieces. The optional 3D view uses original procedural wooden
Staunton pieces, lighting, coordinates and last-move highlighting. Drag to orbit,
use arrow keys to adjust the camera. The visible zoom bar provides minus/plus
buttons, a slider and a percentage readout. Scroll over the board or focus it
and press +/− to zoom between 60% and 240%. Click the percentage to restore
100%; Home resets the complete camera. The 2D / 3D dialog accepts a zoom
percentage along with viewing angle and rotation. Settings are saved across
restarts and follow the board in docked, floating and expanded views. Close-up
zoom can crop the board; return to 100% for the normal view.

Live cards remain 2D. The 3D renderer redraws for position, camera, size or theme
changes, not on every status poll. It still consumes graphics resources when
redrawing; 2D remains the leanest choice for GPU-sensitive tests. A device/context
failure returns the focused board to 2D with a visible message. Local board
arrows/marks remain a 2D feature. The 3D set is independent of the SVG piece picker.

## Quick match

Use **Quick match** beside New tournament. Choose two distinct profiles, with
search and paged selectors, then set the pair count, concurrency and control.
All existing time-control types remain available, including pure nodes with no
chess clock. The default is one concurrent game, paired openings and Ponder off.

By default the chosen control applies to both *tournament snapshots*, without
editing their engine-library profiles. Uncheck the common-control option to keep
profile handicaps. Threads, Hash, GPU groups and UCI options come from the profiles.
GPU groups default to one slot unless explicitly listed. Both engine processes
count toward a shared GPU group, so two profiles using one GPU slot cannot play
each other and the resource preview rejects that setup.

An optional shared PGN/EPD/FEN/Polyglot file supplies shuffled, seeded starting
positions. Colors reverse within each pair. Positions repeat after the suite is
exhausted. Each profile's move book is off by default and can be enabled for
engine-plus-book testing. The review screen shows total games, effective controls,
resources and opening capacity before **Create paused tournament**. After saving,
use Start/resume or Tournament manager. The full Edit setup remains available
before first start, including adjudication, resource budgets and failure policy.

## Profile imports

Engine library → **Import profiles** accepts Engine Arena profile arrays,
Cute Chess `engines.json` arrays (including `engines` wrappers), and Banksia arrays
with nested `app` records. Preview identifies ready, duplicate and skipped entries;
select the profiles to add. File paths, arguments, UCI options and Threads/Hash
are retained. Select the original GUI folder to resolve relative paths.

The preview does not launch engines. Missing executables, unsupported protocols,
custom initialization and White-POV conversion require attention/manual setup.
WinBoard entries are skipped. Third-party pondering, timeout scaling and restart
policies are not imported as tournament policy. Review GPU budgets and use
**Test connection & discover** on imported profiles before starting a test.
Existing profiles are never overwritten. Identical profiles are skipped; distinct
names/settings remain valid configurations. An import batch commits atomically.

Format references: [Cute Chess engine configuration](https://github.com/cutechess/cutechess/blob/master/projects/lib/src/engineconfiguration.cpp)
and [Banksia engine configuration example](https://github.com/nguyenpham/Banksia/blob/master/jsonexamples/engines.json).
These are configuration imports, not migration of either program's databases.

## Completed tournaments

A nonmodal completion card appears for the selected completed tournament. It
shows official games, complete opening pairs and engine-failure counts, with
direct report, PGN, failure-review and final-game actions. The existing final
standings, KO/SPRT information and tournament notes remain available below.
Failure totals distinguish current official results from original/replacement
attempts and exclude diagnostics. Interrupted records remain in attempt history.
Completing one tournament does not interrupt other tournaments or force a view
change. The final-game action opens the highest-numbered valid official game.

## Validation scope

Automated acceptance covers committed move pages, recorded opening numbering,
attempt isolation, atomic imports/duplicate prevention, a complete node-only
match, interactive scoresheet review, frozen clocks, stable reading during new
moves, finished boards, 3D idle rendering/context-loss fallback, Quick match and
both import formats. The release validation receipt records the final regression
and packaged checks. These short tests do not replace the owner's laptop testing
or prove endurance behavior on every graphics driver or imported engine.
