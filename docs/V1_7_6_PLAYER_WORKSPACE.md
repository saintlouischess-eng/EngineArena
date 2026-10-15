# Engine Arena 1.7.6 — Player Arena workspace

Private update for owner testing. Designed by Mark Young; coded with OpenAI Codex.
Close Engine Arena before running the installer. Tournament and Player Arena data
remain in the existing data directory. This update has not been published.

## Opening books for the opponent

In **Player Arena → New game / series → Engine opening book**, choose:

- **Use each engine’s saved book** (default): use the book attached to that profile.
- **No Arena opening book**: have Arena send each turn to the engine. An engine’s
  own internal book options still belong to its saved UCI configuration.
- **Choose a book for this game / series**: select an imported PGN or Polyglot BIN,
  or import one there. Set weighted, uniform or highest-weight selection and a
  maximum number of plies from the starting position; 0 means unlimited.

You choose your own moves. The book supplies only the opponent’s legal moves.
The first missing position or ply limit switches the opponent to search for the
rest of the game. A pending draw offer also requires engine search. Book moves
receive increment and consume no search time, matching tournament book behavior.
Book choice, content hash and policy are snapshotted per game/series; stored
moves retain source attribution. Pausing and recovery preserve this; taking back
moves restores the earlier mainline’s book state. Original variations remain.

Book moves are marked **Book** in the move list. Detailed PGN presets retain book
name, SHA-256, policy, ply limit and move comments; clean presets stay clean.
Older Player Arena games do not acquire a retroactive book claim. Books referenced
by saved Player Arena games/series cannot be deleted. Import/delete requires a
paused Player game so indexing cannot interfere with its clock.

## Arrange your playing desk

Each of the six panels (board, moves, thinking, ratings, series and saved games)
can be arranged independently. Drag the dotted handle between columns or before
another panel. **Float / Dock** switches between a free window inside the app and
the dock. Drag a floating heading to move it. The corner grip resizes panels;
keyboard arrows also resize, with Shift for larger steps. The center divider
changes docked column widths. Floating windows leave the app navigation visible.

The **…** menu provides exact height, floating width, text scale and dock position,
and can hide a panel. **Workspace…** restores hidden panels, changes column width
or resets the layout. Layouts and sizes are saved independently of tournament
workspaces. Floating panels disappear on leaving Player Arena.

**Expand** maximizes a panel. **Full screen** on the playing board gives the board,
clocks and game controls the app viewport; browser fullscreen is requested where
supported. Use **Restore** or Escape to return. Promotion, resignation and other
dialogs remain usable. Undocking is within the Engine Arena window, consistent
with its other workspaces; it does not create a separate OS window.

The move list scrolls within its panel. First position returns to the top; Live
board follows the newest move. Reading older moves is not interrupted by updates.
Move time, depth and book attribution use compact rows. Black-to-move custom
positions align under Black. Long PVs wrap and scroll in a fixed-height region;
metrics, best-move changes and engine output stay within the thinking panel.
Panel text can be scaled from 80% to 150%, in addition to the app font setting.

Both Player Arena clocks now show tenths at all times, including pause and review.
The 3D room clock already uses the shared tenth-second formatter. Camera settings
in Player Appearance now affect the Player camera rather than the tournament
camera, and camera-control visibility is remembered. Repainting controls no
longer briefly blanks the clocks. Review analysis follows the selected move,
and a reviewed board is restored after returning to a hidden browser tab.

## Board audio

Replaced the short tonal impacts with original modeled wooden-piece sounds:
rounded contact, damped wood resonance, a light felt settle and restrained room
reflections. Captures have lift/place accents; castling has two separate contacts.
Move, capture, castling, check and promotion each have three variations, with no
immediate repetition and slight pitch variation. Four quiet notification cues
remain for results and low time. The 19 WAV assets are bundled locally; no network,
paid sound service, microphone or continuous synthesizer is needed.

Player Arena and Focus board use the improved audio with their existing separate
sound switches and volume controls. Hidden boards remain quiet. These are original
synthesized Foley effects, not recordings of a physical chess set.

## Three workflow review passes

1. **Play and data:** book selection and real UCI moves, click/drag in 2D and 3D,
   underpromotion, challenge series, takeback/resume, legal PGNs and book snapshots.
   Fixed initial panel reparenting before continuing the complete play-through.
2. **Workspace and long games:** 500-ply display fixture, very long PVs, drag/dock,
   floating movement, resize, text size, persistence, fullscreen and game dialogs.
   Fixed camera scope, stale review analysis, first-move scroll, clock repaint and
   floating panels covering navigation. Checked laptop layout and both themes.
3. **Delivery and recovery:** all eight languages, final source/UI regressions,
   packaged workflow repetition, actual Stockfish moves, forced native-app exit,
   committed-position recovery, continued play, all PGN presets and exactly-once
   personal ratings. Fixed missing translation keys, reviewed-board restoration and a late
   opponent-lookup response after setup was closed.

Validation uses disposable test-output databases and fixture engines, plus local
Stockfish. Long synthetic lists test presentation only, never official results.
See test-output/v176-validation.json for the final checks and installer digest.
