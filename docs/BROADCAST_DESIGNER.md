# Broadcast Designer — Engine Arena 1.12.6

Open Broadcast → Open Broadcast Designer. Choose an event above the preview or in Show, start with a
preset, then select Apply to output when the private preview is ready. This does
not start a YouTube stream or alter a tournament. OBS uses the same program URL.

## Presets and layouts

Twelve starting scenes demonstrate different layouts and looks: Tournament
classic, Head-to-head studio, Small league, Swiss/open event, Marathon TV,
Daylight magazine, Board first, 3D showcase, Live chess club, Analyst desk,
Statistics overview and Intermission. A thumbnail explains the layout. Set the
expected player pool before adding/resetting a scene: small fields use fewer
rows, while large fields use paged lists. Presets are editable starting points.

Drag panels and resize with the selected panel's corner. Percentage geometry
keeps layouts proportional. Grid snapping, safe-margin guides, keyboard nudging,
panel locking, duplication, stacking order and undo/redo are included.
Text, color and numeric edits preview immediately. Expand preview hides both
sidebars; Escape restores the workspace. Inspector section buttons jump directly
to related settings. Ctrl+S saves a draft; Ctrl+Enter applies; Ctrl+Z/Shift+Ctrl+Z
undo/redo outside an input. Pending switches and disconnection are shown below
the preview. The 2D board stays square.
Tables and labels reduce type size to fit; avoid very small panels for TV/phones.

Each named scene has panels, duration, an optional event assignment and appearance
overrides. Duplicate, rename, reorder or delete scenes. Save drafts locally or
export/import a show with staged images. Exports omit credentials and OBS URLs.
Drafts also save automatically after edits, undo/redo and dragging. Restore a saved
draft after reopening. Revert restores the last applied configuration. Scene appearance overrides take
priority over Show defaults.

## Information and graphs

The combined game panel shows the move number and side to play, both engines'
tournament rank and score, six recent plies, a short principal variation, depth
and engine-reported NPS. Compact K/M speed labels have exact values in tooltips;
unreported speed shows a dash. Long engine names shorten while depth and speed
remain visible. The embedded graph and opening-book information line have been
removed to make room for larger text; dedicated graph panels remain available.
The finished position and official result remain until the next selected game.
Shared thread configurations can move into the table heading; full names remain
in tooltips and stored results. Evaluation-bar scores are horizontal.

Close-game preference uses the smallest available exact-profile Elo gap among
fresh games, falling back to standings proximity when no comparable estimates
exist. It does not switch away from the current game. Completion estimates prefer
a contiguous 30-minute-to-two-hour observation window when available, and hold
their displayed estimate for five minutes; progress counts remain live. Pausing,
disconnection or stale data immediately replaces the estimate with its status.

The 23 panels include board/clocks/ratings, match scoreboard, standings, Rating
Center, moves, engine PV, engine-statistics graph, recent results, results strip,
progress/pace, conditions, hardware, decisive/drawn results, recorded score and
rating progression, opponent comparisons, upcoming pairings, text and images.

Set separate standings/rating entry limits and rows per page; zero means all.
Rotation completes all selected standings pages before all selected rating pages.
Independent tables can appear together. Ratings can cover all recorded engines
or the exact profiles in the selected event. Opponent comparisons show the first
50 recorded opponents; upcoming pairings are the next 20 materialized entries,
not a guarantee of execution order. Result, opponent and upcoming panels have
independent entry limits and rows, using the Show tab page duration.

Engine graphs support evaluation, depth, nodes, nodes/second and remaining clock.
Show both engines on one shared axis, or either engine alone. Choose lines,
lines with dots, bars, area, steps or dots. Each engine name can have its own
color/style, retained when board colors swap. Evaluations use White's perspective;
large values/mates are capped at the bar range. Missing values are omitted.

Score/rating progression uses real observations saved every five minutes while
those panels are enabled, retaining up to 720 observations. These show the top
five from the latest saved top-20 snapshot. They do not reconstruct earlier
ratings. Pace/ETA uses observed progress, including pauses. No extra analysis
engines or expensive confidence fits are started.

## Opening OBS at verified priority

In **OBS program output & switching**, select **Open OBS · Normal priority**.
Engine Arena opens OBS with explicit Normal Windows process priority and checks
the actual process after startup, even if Arena inherited Below Normal priority.
It reuses an already-running copy and verifies/applies Normal priority without
restarting it. **Check OBS priority** only reads the current process state.

Standard Windows installations are detected automatically. For a custom install,
enter its full `obs64.exe` path; a successful launch remembers it locally, outside
exported show layouts. Portable installations with OBS's portable-mode marker
use their own preferences. Before a fresh launch, only the saved priority setting
is changed, with a backup of the old settings file. Existing scenes and profiles
are retained. If permissions prevent verification, the designer reports it.

Streaming and recording are still started manually in OBS. This launcher does
not change their state, microphone/desktop audio, stream key, encoding, or game
resources. OBS remains independent of Codex. Use this launch control for future
sessions instead of a custom Windows task that might launch at Below Normal.
Normal priority addresses launch inheritance; it cannot guarantee zero dropped
frames from unrelated rendering, encoding or network problems.

## Ticker and appearance

Official result and upset headlines include both engines' cached Rating Center
estimates beside their names, including entries outside the displayed top 20.
The labels use the same exact-profile mapping as the featured board. Missing or
ambiguous estimates show `Elo pending`. Ratings are the snapshot available when
the headline was created, not a before/after rating change. Upset text describes
the opponent's rating advantage explicitly. Headlines remain unchanged while
their scrolling pass is on screen. All standings/rating rows use bold type.

Ticker presets: Warm TV, Results in color, Quiet headlines and Daylight ticker.
Set pass duration (higher is slower), or use Slower/Faster. In the Ticker tab, select
"This scene" (the default) to change the visible ticker, or "Default for all
scenes" to edit inherited defaults. Existing scene overrides are identified.
The preview responds immediately; Apply to output updates OBS. Speed changes
preserve the text's current position. Faster/Slower are disabled in stationary
headline mode, where headline duration controls the change interval.
Choose scrolling or
stationary headlines, text size, headline duration, label, separators, spacing
and custom messages. Result scores and endings such as checkmate have independent
colors, alongside text, label, separators and background. Choose official results,
upsets, leader changes and milestones in the Ticker tab. Scrolling stories update only
between complete passes; version numbers are not highlighted as result scores.

All 15 themes, 21 2D sets, six wood finishes/plain colors, both 3D sets, three 3D
boards and five rooms are available. Copy the normal workspace board as a starting
point, then edit independently. Lighting, camera, tours, saved views, knight
orientation, coordinates, trays, crown stamps and room activity are configurable.
Thinking-arrow color and 0–10 second added delay work in both board modes. Zero
removes the extra stability delay, not normal incoming-data latency.
The 2D thinking arrow uses a slimmer shaft and head with soft transparency.

Move sounds and room ambience are separate choices; private preview is silent.
3D stays capped at 30 FPS (15 optional), using the shared GPU frame gate and 2D
fallback after context loss. Retry 3D in preview, or refresh the OBS source to
retry Program. One featured board is allowed per scene.

## Complete games and event selection

Layout changes retaining the board preserve the current game and move history.
Event changes and scenes hiding the board wait for the game and final-result
hold. Cut to selection now asks for confirmation before cutting away; it changes
presentation only. Event playlists rotate among selected running events after
the minimum duration and a game boundary. Explicit scene event assignments win.

If no selected event is running, the last snapshot remains. Intermission/statistics
scenes do not silently select unseen games. Returning to the board waits for a
fresh game. An event changed only in private preview shows a waiting placeholder
until applied, avoiding another event's data under its name.

## Installation and OBS

Drain and close Engine Arena before installing. End a live broadcast before
updating its helper. The workspace detects an older helper and offers a separate,
confirmed restart of that helper only. Its keys/configuration are retained, so
the OBS URL stays stable. This control never restarts the tournament worker.

Remove old OBS Custom CSS after transferring equivalent native settings; CSS can
override designer colors. Match the OBS source dimensions to the output canvas
(default 1920×1080). A 60 FPS browser source with a 30 FPS stream is supported;
3D retains its own 30 FPS cap. Disable microphone/desktop audio for board audio only.

The helper is local and independent of ordinary workspaces. It caches tables,
polls incremental moves and reads only the worker API. Disconnection retains the
last board with a reconnecting notice.

## Readable text in 1.12.2

Select a panel to adjust its **Text size**. Standings, Rating Center and rotating
statistics panels also have **Column heading size**. **Detail text size** controls
notes such as search depth, nodes/sec, page information and graph legends. Values
are pixels at the broadcast output resolution, independent of the designer preview
zoom. Set either secondary size to 0 for automatic sizing: column headings match
the main text; header progress also matches it, while other details use 85%.
Explicit sizes remain fixed.

**Auto-fit main text to panel** keeps content inside the panel. The designer now
reports the actual output sizes and warns when text shrinks or content does not
fit. Enlarge the panel, show fewer rows or lower a size if needed. Turning auto-fit
off preserves the chosen main size; the private preview warns about overflow.
These messages are operator-only and do not appear in the OBS output.

Heading/detail sizes, auto-fit choice and layout are saved with the show and
retained through export/import. Earlier layouts load with automatic sizes and
auto-fit enabled. The 2D board grid also keeps square cells regardless of the
piece artwork, fixing a clipped bottom rank in some layouts.

The featured game status (Live, Final result or waiting) now shares the last-move
footer, freeing the former status row above the board for larger squares.
Engine Elo badges beside the names are larger and bold for television viewing.
Completion percentage and engine count in the header are also larger, with
stronger text weight and contrast. Select the header panel and use **Detail text
size** to adjust this line independently.

Under **Board & 3D**, adjust **Evaluation bar width** (16–80 output pixels) and
**Evaluation number size** (10–40 pixels). These can inherit the show defaults
or be set per scene. The bar height follows the board, and the board uses the
remaining width automatically in both 2D and 3D. Existing layouts retain the
previous 27-pixel bar and 16-pixel evaluation text until changed. The score text
is capped to fit when the bar is narrower than the requested text size.

## Header and final result in 1.12.3

The header groups the larger Engine Arena crest and tournament identity on the
left, game totals/field size and a live completion bar in the middle, and estimated
time remaining on the right. Select the header panel to change **Logo size limit**, or
hide **Show tournament progress** and **Show estimated time remaining**. The logo
fits within the header height; increase that panel's height to use a larger crest.
The header adapts to narrower layouts. Long titles and subtitles truncate cleanly.

ETA uses Engine Arena's current official-game pace when available. If the GUI is
not supplying a continuous estimate, the broadcast can use its own bounded recent
observations after at least five minutes and two completed games. Detected pauses,
schedule changes, replay count decreases and long gaps break that sampling segment.
This is an estimate at recent pace, not a deadline. Paused, draining, stale,
disconnected, replaying and completed tournaments show explicit status instead.
The separate progress panel uses the same calculation.

Final results appear in a ribbon below the player bars, outside the chessboard.
It shows the score, winner/draw and ending reason. Every square of the final
position stays visible, and the board retains its size while the result is held.
The existing result-hold duration and start-to-finish game-selection rules are
unchanged. Unofficial attempts are clearly labeled and do not claim a winner.
