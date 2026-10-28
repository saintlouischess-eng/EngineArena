# Broadcast studio

This page describes the original studio workflow. For the current 1.12.6
Designer, all 2D/3D options and configurable table limits, use the
[Broadcast Designer guide](BROADCAST_DESIGNER.md).

Open **Broadcast** in Engine Arena and select **Open broadcast studio**. Choose
the tournament, appearance, and game preference, then select **Apply to broadcast**.
This opens an independent local show. Your tournament workspace, normal focused
game, and other applications remain available without changing the broadcast.

## OBS setup

Add a **Browser Source** using the studio's **Copy source URL** button. Set its
width to **1920**, height to **1080**, and custom frame rate to **60**, with the
encoded stream at **30 FPS**. This is the lightweight 2D source, not a 3D room. Leave
**Shutdown source when not visible** and **Refresh browser when scene becomes
active** off. Enable **Control audio via OBS** if you want the optional move sounds.
Capture this source rather than the desktop. Do not share the local control URL.

OBS and YouTube setup do not start the stream. Review the local preview first.
When ready, select the intended YouTube stream and its matching key in OBS.
Keeping YouTube Auto-start off lets you inspect the incoming encoder preview
before choosing Go live. Use a recording folder that exists and is writable.

## Complete games

The director waits for a newly starting game, plays its opening moves, and shows
every committed move through the official result. A game briefly discovered
after its first move still replays all its moves from the opening. It never cuts
to a game deep into play. Very fast moves are spaced out for viewing, so the show
can briefly trail the live position. Clocks count down only when caught up.

The final result stays visible for 15 seconds by default (configurable from 5 to
60). Then the director waits for the next fresh game. Leader, similar-rank, and
engine-name preferences choose among fresh candidates; they do not interrupt the
current game or guarantee that a preferred engine will be available. Changing
the tournament intentionally starts a new show.

The current output uses a 2D board, four piece sets, four broadcast color themes,
optional board rotation and sounds, clocks, evaluation, played moves, and a
clearly labeled engine principal variation. Evaluation comes from the playing
engines; no extra analysis engine is launched.
The evaluation number sits at the favored color's end of the bar, following board
orientation, with dark text on White's end and light text on Black's end. Missing
evaluations show a centered dash instead of implying an equal position.
The studio also offers a separate evaluation range, independent of the main
workspace's evaluation settings.

Choose wood finishes independently for light and dark squares, or use the theme's
plain colors. Dark-square lightening preserves the grain while improving contrast
on darker displays. The Warm TV preset selects charcoal, ash, lighter rosewood,
Classic Bold pieces, a ±4-pawn range and a slower 150-second ticker. It fills the
controls for review; choose Apply to broadcast to save it. Existing saved setups
retain their appearance unless changed. OBS custom CSS can override these controls.

Optional cyan thinking arrows show the active engine’s first legal PV move,
with a one-second stability delay by default (adjustable from zero to ten).
They are distinct from yellow highlights marking the last played move. Arrows
only appear when the broadcast has caught up to the exact search position, and
clear during opening replay, between searches, on disconnect, and at the result.
Engines that do not report a usable PV simply show no arrow.

An Elo badge beside each player's name shows that exact recorded profile's rating
in the selected Rating Center category, rounded to a whole point. It refreshes
with rating snapshots, independently of which standings page is visible. Hover
over a badge for the category and snapshot time. An unrated or ambiguous profile
shows a dash rather than borrowing another engine version's or configuration's
rating. These are Rating Center ratings, not the tournament's performance scores.

## Information panels

The right panel shows standings 1–10, standings 11–20, Rating Center 1–10, then
Rating Center 11–20 before repeating. The panel interval applies to each page,
so it completes a category's top 20 before switching categories. Standings rank tournament
points and tiebreaks. Ratings account for opposition and include the selected
category's recorded history; these are different lists. Games played are shown
because the field can be uneven during a running tournament.

Standings refresh about every 30 seconds. Ratings refresh at most every three
minutes, retain the last successful snapshot, and display its time. The broadcast
rating view uses the same estimates without expensive per-row confidence-interval
calculations. The ticker can scroll or alternate stationary headlines and can
include official results, leader changes, thousand-game milestones, and wins over
an opponent rated at least 200 Elo higher in the latest matching rating snapshot.
An upset headline describes that estimate, not statistical proof of superiority.
Scrolling text stays unchanged for its entire pass. New results are queued and
the latest snapshot is displayed on the next pass, after the old text has left
the screen. Stationary headlines continue to rotate normally.
Result scores and game endings use the theme's accent color; engine names retain
the normal text color, with clear spaces around the diamond separators.
Scroll duration accepts 20–600 seconds; increasing it slows the current line.

## Reconnection and resources

Keep the tournament worker and broadcast service running. A worker disconnection
retains the last saved position and visibly marks reconnection. Reopening the
preview does not reset the selected game. An interrupted attempt is labeled as
having no official result. The service only reads tournament APIs; it cannot
start, stop, edit, or score games. Broadcast settings are saved separately in the
data folder's `broadcast` directory. Closing the main workspace does not change
the independent OBS source, but stopping its worker suspends new game data.

The service binds only to localhost. The viewer and controller use separate local
keys. Keep the URLs private and never substitute the worker credential in an OBS
source. Normal operation uses local code, not ongoing AI calls or a paid narrator.
