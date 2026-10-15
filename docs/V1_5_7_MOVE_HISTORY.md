# Engine Arena 1.5.7 — long-game move history

The Game moves panel now scrolls through the entire recorded game. Reaching an
edge loads earlier or later moves automatically, keeping the current reading
position steady. The **Beginning** button jumps directly to the opening moves.
The arrow buttons still offer explicit navigation, and a visible move range
shows which part of the game is loaded.

Scrolling back pauses automatic scrolling. Incoming moves do not pull the list
back to the bottom. Click a move to review its board and recorded statistics;
**Return to live** restores the current position and follows new moves again.
For completed games, the button is **Final position**. Browsing an earlier page
does not replace the saved final board, and browsing history prevents automatic
switching to the next game when the current game finishes.

With the move list focused, **Home** goes to the beginning and **End** returns to
the latest move. Earlier/later navigation remains available while a read is
pending; stale responses cannot overwrite the newer selection.

The interface keeps at most 400 searched half-moves, plus the opening when at
the beginning, in its scrolling window. Older and later moves remain available
in the database and load as needed. No moves are deleted or omitted from exports.
No game rules, clocks, ratings or stored tournament data change in this update.
The rook-only crown correction and all knight directions from 1.5.6 remain.

Validation: a synthetic long game with 805 recorded half-moves (including four
opening moves) was traversed in both directions in the packaged app. Separate
live checks covered incoming moves, selected replay positions, completion,
pending reads, and automatic following across page boundaries. Large text and
all eight language layouts were checked. The targeted suites passed 58
JavaScript and 29 Python tests. This update does not claim a new endurance run.

Private update. Designed by Mark Young; programming by OpenAI Codex. Pause and
drain, close normally, install 1.5.7, reopen and resume. Not published to GitHub.
