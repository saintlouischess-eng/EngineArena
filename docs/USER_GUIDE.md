# Engine Arena 1.9.7 — user guide

## Extend a completed round robin

Select a completed standalone round robin in Tournament workspace and choose
**Add engines…**. Search and select new profiles across pages, preview the added
and total game counts, then **Save extension paused**. Start/resume when ready.
Earlier games, attempts, engine snapshots and ratings are retained. Only new
versus existing and new versus new matchups are added. Tournament conditions and
cycles stay fixed; new profiles keep their own resource/time overrides. Existing
profiles cannot be selected twice. Event stages, Swiss and knockout are excluded.

**Focused game → Board & clocks → Show draw-rule counter** toggles the new
counter (on by default). It counts half-moves since the last pawn move or capture;
two half-moves equal one full move. Claims enabled: 100 plies (50 moves). Claims
disabled: the automatic 150-ply (75-move) limit. It follows the displayed position,
including move review. It is not a time estimate or a guarantee of the ending.

See [1.9.4 notes](V1_9_4_TOURNAMENT_EXTENSIONS.md) for opening and recovery details.


## Mouse camera controls

Right-drag up, down, left or right to look around. Continue dragging upward
past the table-level view to look above the board; no extra key is required.
Drag downward to return to the board. The camera stays above the table and
does not flip upside down. Alt + left-drag offers the same control. Shift +
right-drag still adjusts height, and the wheel zooms. Both workspaces share
these controls and remember the view. See [1.9.2 notes](V1_9_2_MOUSE_CAMERA.md).

## Room, camera and library update

**Room motion** in Appearance offers **Follow Windows**, **Animate** and **Still**.
Choose Animate to keep the room moving even when Windows Animation effects are
off. Follow Windows respects that preference and explains a pause on screen.
Still freezes room activity deliberately; clocks and actual games continue.
Animation limits are now **15 or 30 FPS**. Older 60 FPS preferences load as 30.

**Tilt** aims the camera up or down without changing zoom or vertical framing.
Use Appearance → Camera views → **Low angle** for a table-level starting view.
Positive tilt looks upward; negative tilt looks down. Sliders are available in
both board workspaces and numeric tilt in both photo dialogs. Photo adjustments
do not change the saved watching view. Home / Reset camera restores all axes.

Engine-library checkbox choices take priority over old draft participants while
keeping the other draft conditions. **Delete selected (count)…** is beside the
selection count and works across pages. Deleting keeps the current filter, page
and scroll; an emptied final page moves to the previous valid page. Engine files
and recorded tournament snapshots remain intact.

See [1.9.1 notes](V1_9_1_ROOM_LIBRARY.md) for testing and limitations.


New: [Custom competitions](V1_9_CUSTOM_COMPETITIONS.md) lets you arrange stages, choose advancement, review the complete schedule, save templates and edit future stages. Open **Events & leagues → Custom competition…**.

Ratings Center now has **Version display → Best version per engine family**, retaining separate thread/GPU configurations and every version’s underlying rating evidence.

Also included: [Adjudication controls](V1_8_9_ADJUDICATION.md) expose resignation and draw windows and the minimum played plies before a draw. Open **New tournament → Adjudication & SPRT**, or **Edit setup…** before the first start. Defaults are 6 / 12 / 80 plies. Two plies equal one full move; the minimum draw length excludes the imported opening history.

Previously added: [Live environment](V1_7_1_LIVE_ENVIRONMENT.md) adds optional background players, chess-club furnishings, animated games and quiet room sounds to both 3D boards.

Also included: [Player Arena, sounds and photo folders](V1_7_PLAYER_ARENA.md) lets you play your installed engines in 2D or 3D with clocks, saved PGNs and separate personal ratings.

Engine Arena includes a live Game moves scoresheet, optional wooden 3D board,
Quick match, Cute Chess/Banksia UCI imports and a tournament completion summary.
See [the new workflow guide](V1_2_WORKFLOWS.md) for controls and limitations.
It also includes the [simultaneous tournament manager](SIMULTANEOUS_TOURNAMENTS.md).
Private candidate 1.9.2. Designed by Mark Young; coding and implementation by OpenAI Codex. The public release remains 1.2.14. This candidate still needs owner and laptop acceptance.

Version 1.2.14 keeps 3D board letters and rank numbers upright from the current
viewing direction, including after rotation and board flip. They remain on the
wooden frame and disappear behind nearer pieces instead of overlapping them.

Version 1.2.11 keeps the KO results compact. Expand **How KO standings work**
for the complete explanation; it stays open during live updates. Exported reports
retain the full wording. Pairings & tiebreaks now omits the unused Round 1 heading
for fixed schedules such as round robin. Actual game rounds remain unchanged.

Version 1.2.10 added two saved visibility preferences:
- **Display & layout → Hover help** (beside Apply appearance) turns explanatory
  control pop-ups on or off for both mouse hover and keyboard navigation.
  Apply appearance saves the choice. Native control tooltips are also suppressed
  when disabled; accessible labels and descriptions remain available.
- **Focused game → Hide 3D controls / Show 3D controls** hides or restores the
  zoom and height sliders without changing your camera. The **2D / 3D** dialog
  also has **Show 3D controls**. Dragging, scrolling and keyboard camera controls
  remain available while the overlay is hidden.

Both preferences survive restarting the app.

The 3D board includes vertical framing: use the Height slider, down/up buttons,
or the center button beneath Zoom. Shift-drag or Shift+Up/Down also moves the
board without changing its viewing angle or zoom. The 2D / 3D dialog accepts a
signed vertical position percentage. Positive values raise the board.

Traditional red crown marks identify the original kingside rook and knight of
each color. They follow moves, castling and recorded replay; captures remove the
mark and promotions do not acquire it. Turn them off in 2D / 3D if preferred.
Marks require verified history from the standard initial position. Arbitrary
FEN-only openings and nonstandard Chess960 starts remain unmarked; no origins
are guessed. The accepted sculptures and wood maps are unchanged.

The focused board retains direct 3D zoom controls. Use the minus/plus
buttons or slider, scroll over the board, or focus it and press +/−. Zoom ranges
from 60% to 240%. Click the percentage to restore 100%, or press Home to reset
the complete camera. The view is saved across restarts and works in docked,
floating and expanded windows. The 2D / 3D dialog also accepts a zoom percentage.
Select **3D board**, then choose **1849 Staunton** or **Tal 1962 · Soviet
Championship** under **3D piece set**. The set is saved for both Focused Game
and Player Arena. In Player Arena, use **Appearance…** while in 3D mode to
change it. Red kingside crown marks apply only to 1849 Staunton.

## Install or update

1. Copy `EngineArenaSetup-1.9.2-win-x64.exe` to your Windows 11 x64 laptop.
2. Close every Engine Arena window, letting saving finish. Run the installer and
   keep the existing installation folder to upgrade. Saved tournaments, profiles,
   settings and PGNs are preserved outside the program folder.
3. Leave **Run Microsoft WebView2 setup again** unchecked for a normal update.
   Setup detects an existing runtime and installs its bundled offline runtime when
   needed. Python and .NET are also included.
4. Launch Engine Arena from the Start menu. Check the **1.9.2** version in the
   sidebar. Add your own UCI engines, networks, books and tablebases; these are not
   included.

The program normally lives in `%LOCALAPPDATA%\Programs\Engine Arena`; saved data
normally lives in `%LOCALAPPDATA%\EngineArena\Data`. A separate workspace can use
`EngineArena.exe --data "D:\Arena tests"`. Open each workspace in one window.
Uninstall preserves saved data and shared WebView2/PawnIO components.

## Your first comparison

1. In **Engine library**, add executables, test connections, and save profiles.
   Select the profiles to compare. Cloning makes an independently configurable
   profile, including engine options, Threads, Hash and optional per-engine controls.
2. Create a **New tournament**. Review format, scheduled game count, opening source
   and policy, time control, retry settings, concurrency and CPU/memory/GPU budgets.
   The number of participants is independent of simultaneous games.
3. Save the tournament paused. **Edit setup…** remains available until its first
   start. Choose **Start / resume**, or add saved tournaments to the automatic queue.
4. Review standings, time-forfeit counters, head-to-head, focused game, search
   history and graphs. Change **Concurrent games** while running to raise the limit
   or let excess games finish. Resource budgets still apply.
5. Use **Results & exports** for reports and PGNs. **Clean games** is a concise PGN;
   **Complete archive** includes diagnostic and configuration headers. Text exports
   provide aligned plain text, forum code blocks and Markdown for sharing.

**Pause & drain** lets active games finish. **Stop active games** archives unfinished
attempts and requeues those games from their recorded openings. Reopening after a
crash retains committed results; resume the recovered tournament when ready.

## Running several tournaments

Open **Tournament manager**, add saved tournaments, and click the **Run together**
card to review and save shared limits. Both execution choices are visible at the top. **One at a time** preserves the existing sequential queue; **Run
together** shares a CPU thread budget, memory allowance, game limit and GPU groups
across tournaments in this workspace. For one Lc0 instance across all tournaments,
assign every GPU profile to **gpu0** and use **gpu0:1**. Individual tournament
limits still apply.

Search, filter or sort the manager list. Start and pause entries individually or
select several for bulk actions. **Options…** changes priority and each tournament's
game limit. Lowering limits drains existing games; it does not abort them.
**Pause all & drain** pauses every running tournament. In Live boards, choose
**All running tournaments** to view combined cards with tournament names.

Upgrades retain **One at a time** mode. Restart preserves results and settings and
requires explicit resume. Separate application workspaces do not share budgets.
Linked events and leagues keep their ordered stage controller; suites and benchmarks
wait until the tournament worker is idle.

## Continuing seasons and fresh starts

In **Events & leagues**, choose **Create season competition…**. Start from a saved
tournament's engine list and conditions, then choose qualification, independent
divisions or a progressive championship. Division sizes, promotion/relegation,
clocks, books, paired cycles and the final are configurable. Preview the schedule,
save, review the roster and choose **Run event**. Individual stages appear in
Tournament manager. Independent divisions share one event resource budget;
progressive divisions wait for their qualifying engines.

Choose review windows between seasons or stages to approve registered engine
upgrades. Keep new binaries in separate version folders. Earlier results retain
their original engine snapshots. At a season boundary, add or withdraw entrants,
and review division assignments. Championship ties continue in opening pairs.
See [the season-manager guide](V1_4_SEASONS.md) for policies and limits.

**Fresh copy** starts an empty competition from its saved setup. **Delete event…**,
**Delete selected…**, and **Delete all events…** preview the complete record set
before confirmation. Pause and drain first. Cleanup includes linked stages,
attempts, managed PGNs and recovery backups, then returns database space to disk.
Engine installations, books, source templates and separately exported files remain.

## Season overview, careers and sharing

Open a competition in **Events & leagues**. The new **Season overview** follows
live division races, championship scores and recorded promotion/relegation.
Choose **Latest** to follow the current season or select an earlier season.
**Engine careers** follows entrant identities across approved version upgrades,
showing titles, stage conditions and rivalry results without combining Elo across
incompatible conditions. **Season summary** produces a short forum recap or full
season tables, with plain-text, forum-code and Markdown copying and Save TXT as.
Existing records remain accessible under **Stages & records**. See the
[competition desk guide](V1_4_2_COMPETITION_DESK.md) for scope and interpretation.

## Books, clocks and results

The tournament's shared opening book supplies starting positions for both sides.
Optional per-profile move books choose moves on each engine's own turns. For
engine-plus-book comparisons, clone the engine, assign different profile books,
and leave the shared starting position at the initial position. Disable profile
books when only the shared tournament opening suite should apply.

Pure nodes sends `go nodes N` with no chess-clock limit. Startup, readiness and hang
watchdogs are separate. Fractional seconds are supported. Per-profile controls
override tournament controls, including in handicap comparisons.

W–D–L and points include official games. With color reversal enabled, Elo, confidence
intervals and LOS use completed opening pairs. Unpaired tournaments use individual
games. LOS is relative to the sampled opposition or selected head-to-head opponent;
it is not the probability of winning the tournament. Pool ratings are a separate
opponent-adjusted estimate anchored to a reference. Read [statistical methods](STATISTICS.md).

To replay a failure, pause and drain, select games in **Games & attempt history**,
then choose **Diagnostic replay** or **Replace official result**. Original attempts
remain. A replacement changes official statistics once; later Swiss/KO dependencies
must be resolved explicitly. Time-forfeit counters retain the original failures.

## Workspace and hardware

**Display & layout** controls theme, font size, board materials, SVG pieces and saved
panel layout. Drag, resize, float or hide panels. **Boards across** sizes live boards
to their docked width independently of the number displayed. **Board & clocks**
controls focused-game clock placement and sizing. Language choices include English,
Spanish, French, German, Portuguese, Italian, Dutch and Polish.

**Hardware display…** selects readings and refresh rate. GPU telemetry supports
NVIDIA. CPU temperature and live fastest-core readings use the optional signed
PawnIO driver and bundled sensor reader. Choose **CPU sensor setup**, install the
signed driver if needed, then **Enable CPU readings for this session** and approve
Windows permission. Enable the reader again after reopening. Games work without it;
unsupported sensors show Unavailable.

**Worker & recovery** controls backup count, interval, storage estimates and
optimization. Deleting a tournament removes its records from recovery copies and
reclaims managed database space. Export anything you want to keep before deletion.

## Final laptop check and feedback

Confirm that the update preserved your profiles and settings. Run a small match,
an automatic queue and your preferred tournament format. Resize boards, switch
themes, inspect clocks and hardware, export a report and PGN to a chosen folder,
then close/reopen and confirm the results remain. Report any unexpected behavior
before public release.

Include version, Windows version, engine versions, time control, opening policy,
concurrency and exact steps. Screenshots or a small PGN help. Review shared files for
private paths or settings. The app sends no feedback automatically.

### Explicit engine CPU budgets

Engine profiles use explicit positive thread counts. Importing an automatic thread setting (zero) proposes one thread and explains the change in the preview before you import. Review the proposed setting and assign the GPU group for GPU engines. Saved option names are matched without regard to capitalization. Old automatic-count tournament snapshots conservatively reserve all logical CPUs; their original settings are preserved.


## Setup and bulk editing (1.4.1)

See [Setup and bulk engine settings](V1_4_1_SETUP.md) for named gauntlet candidates, durable unsaved setups, bulk UCI/book options, clock tolerance and tablebase configuration.
