# Engine Arena 1.5.5 — 3D display polish

Private test update. Designed by Mark Young. Programming by OpenAI Codex.

Open **Focused game → 2D / 3D → Knight direction** to choose:

- **Toward the king** (default): each knight faces its king at the starting position.
- **Away from the king**: the opposite of its starting orientation.
- **Forward**: toward the opposing army.
- **Backward**: toward its own side.
- **Left** or **Right**: from the owning player's perspective.

The choice is saved with display preferences. Original knights keep their chosen
orientation as they move, including crossing the centre of the board. Recorded
moves and resumed games reconstruct the same identity from existing move history.
Chess960 starts use the king's actual starting file. Promoted knights and positions
without verified starting history face forward for the toward/away choices.

The red crown stamps on the original kingside rook and knight now read upright
from their owner's side. They stay attached to the carved surface, with lighting
and proper occlusion. Changing a knight's direction does not turn its stamp
sideways. Stamps turn naturally with the board; they are not screen overlays.

This changes appearance only. Existing models, chess rules, timekeeping, tournament
settings, saved results and ratings are retained. No database migration or extra
per-move database record is needed. The 1.5.4 graphics cleanup fix is included,
and static boards continue to render only when something changes.

To install: pause and drain running games, close Engine Arena normally, run the
1.5.5 installer, reopen the app and resume. This update is not published to GitHub.

## Validation

31 targeted Python cases and 58 JavaScript cases passed. Display checks cover all
six directions, both colors, board rotation/flip, saved non-default preferences,
replay, eight translated dialogs, narrow layouts, and light/dark themes. The
crown's projected orientation is checked against its owner's side for every
knight direction, and the rendered pieces were inspected visually.

The graphics regression retained zero retired contexts after 80 renderer-disposal
cycles; 200 game switches reused the focused renderer, and 20 2D/3D switches
remained bounded. Static boards did not redraw. Camera, zoom, height, crown
visibility and graphics-context-loss fallback checks also passed.

The packaged app completed six short Stockfish/Berserk games (three opening
pairs), with legal PGNs in all four export presets. A forced shutdown in this
isolated test preserved the committed result and interrupted attempt, then
resumed and completed the remaining games. This is a focused acceptance check,
not another endurance run or a fresh-machine installation test.
