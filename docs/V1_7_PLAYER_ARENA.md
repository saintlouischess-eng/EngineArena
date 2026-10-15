# Engine Arena 1.7.0 — Player Arena

Private development installer for owner and laptop testing. Designed by Mark Young;
coded with OpenAI Codex. Pause and drain testing, then close Engine Arena before updating.

## Sit down and play

Open **Player Arena → New game / series…**. Choose an installed engine, your color
and clocks. Save, then press **Start game**. A single game or a challenge series
uses your existing engine profiles, including their engine-specific options.
Set an optional UCI strength limit when the engine advertises it. Threads, Hash
and clock tolerance are explicit; ponder is off. Player Arena reserves its engine
against the shared testing CPU, memory and GPU budgets. If resources are occupied,
it explains the shortage; resume once capacity is available.

Click a piece and its destination, or hold and drag it, on either the 2D or 3D
board. Promotion offers queen, rook, bishop or knight. Optional automatic queen
promotion and legal destination markers are in **Player settings**. The 2D board
also supports arrow-key focus and Enter/Space selection. The optional move-entry
field accepts UCI coordinates, such as e2e4 or a7a8n. Castling is supported in
standard chess and legal Chess960 starting positions.

Use the board's lower edge to resize it vertically. **Flip** affects this board
only. In 3D, right-drag rotates the camera, Shift + right-drag raises it, and the
wheel zooms. **Camera controls** shows/hides sliders. **Appearance…** uses the
existing piece sets, wood boards, rooms and lighting. Rendering stops when idle
and the Player renderer is disposed when leaving the workspace.

**Game moves** includes move numbers, elapsed move time and engine depth. Browse
from the first position without losing the live game, then select **Live board**.
**Show analysis** reveals evaluation (White's perspective), numbered PV, depth,
selective depth, nodes, NPS, search time, hash use, tablebase hits, WDL when supplied,
best-move changes and the last 256 engine communication lines. Hints show a legal
suggested move. Missing engine information stays unavailable rather than invented.

## Clocks, endings and competition

Independent human and engine controls include sudden death, increment, simple
delay, Bronstein delay, staged/repeating controls and fixed time per move. Engines
also support fixed depth and pure fixed nodes. Untimed human practice is available.
Startup/readiness and hang watchdogs are separate from chess clocks.

**Resign** confirms before recording a loss. **Claim draw** is available when the
chess rules allow it, including repetition or the fifty-move rule. Automatic
chess endings include checkmate, stalemate, insufficient material, fivefold
repetition and the seventy-five-move rule. Timeout results account for an
opponent with insufficient mating material. Engine failures pause the game and
retain the position rather than awarding a fabricated win.

UCI has no negotiated draw-offer command. **Offer draw** therefore uses an explicit
Player Arena policy: offer on your turn and play your move; the next engine search
can accept if an exact evaluation is within the configured range at depth 8 or
greater, after the minimum move number. Otherwise play continues. You can disable
offers, or always accept in casual games. This is labeled as an application policy,
not a claim that the engine communicated agreement.

**Match / challenge series** plays the human against each selected opponent,
alternating human colors on successive cycles. The number of scheduled games is
shown before saving. Start the next game when ready. Abandoned rounds retain their
unfinished record and receive no score; they count toward the scheduled rounds.
This is a human gauntlet, not an engine-versus-engine round robin.

## Personal ratings and saved games

Rated games use a separate local practice Elo, starting at 1500 with K = 32,
against the opponent rating you assign. These opponent ratings are estimates;
the app does not certify engine handicap strength or a federation-equivalent
human rating. The first 20 results in each category are marked provisional.
Bullet, blitz, rapid, classical and handicap categories remain separate. Pausing,
recovery, hints or visible analysis makes the current game casual. Rated games
require the standard starting position and a human clock. Personal results never
enter engine-testing standings or Rating Center.

Moves and clocks are committed to the existing transactional database. During a
turn the active clock is checkpointed every five seconds. After a forced shutdown,
the committed position returns paused and casual; restart only the engine, then
continue that position. Time after the last checkpoint is not reconstructed.
Takebacks are for casual games and preserve removed moves in the database history.
An unsuccessful database write pauses play, restores the committed position and
shows a saving error. Resolve it before continuing.

PGNs save automatically under **Data/PlayerArena/PGN**; interrupted/in-progress
records are separately checkpointed under **Data/PlayerArena/In progress**.
Each game has a stable filename, so retries and restarts do not append duplicates.
PGN failures remain visible and retry automatically or through **Retry PGN saving**.
**Additional PGN folder** creates a further copy at your chosen location.

**Export PGN…** offers the existing Clean, Annotated, Engine testing and Full archive
presets, individual header/comment controls and text output. Export one game, a
whole series or all saved human games, choosing a file in the desktop save dialog.
Remembered Player export choices also control the additional automatic copies.
Roles and time-control metadata distinguish the human from the engine. Exports
contain the current main line; takeback alternatives and session diagnostics stay
in the database. Finished games remain browseable. **Reset personal ratings**
resets the named player's future rating and keeps saved games and the result ledger.

## Sound and photos

Player Arena has original, locally generated wooden move/capture/castling sounds,
with softer cues for check, promotion, low time and results. **Sound on/off** and
volume are remembered in Player settings. No downloads or background audio loop.
The tournament **Focused game → Sound…** has its own enable and volume controls,
off initially. Only new moves on the visible focus board sound; browsing history,
changing focused games and hidden boards stay quiet.

Both **Photo…** dialogs now provide **Choose folder…**. The desktop remembers a
dedicated photo folder, initially Pictures/Engine Arena, independently of opening
book and PGN folders. Save As can choose another location, remembered next time.
Player photos capture a frozen, control-free 3840 × 2160 PNG. A regular browser
uses its own download-folder settings.

## Validation

Checks include the backend regression suite, real Stockfish play to checkmate,
all PGN presets with legal replay, draw policies/claims, promotion, Chess960,
node-only engine search, clocks, resource refusal, rating idempotency, takebacks,
injected save failures and PGN retry. Browser acceptance exercises 2D and 3D click
and drag, replay, analysis, photos, audio decoding, preferences, promotion and
light/dark layouts. Packaged acceptance forcibly terminates an isolated native app,
restarts it and verifies the committed position, clocks, continuation and PGNs.
Production testing records are not used or changed by these tests.

Owner/laptop acceptance remains necessary, especially audio balance, 3D interaction
on the laptop GPU and the native folder/save dialogs.
