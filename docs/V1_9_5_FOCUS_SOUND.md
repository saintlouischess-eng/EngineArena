# Engine Arena 1.9.5 — focused-board sound and resizing

Private cumulative test update. Public release remains 1.2.14.

Resizing a panel or the application could make the browser clamp the move list's
scroll position. The list interpreted that automatic scroll as history browsing,
which also suppressed focused-board sound until a different game was selected.

The move list now preserves live following when its viewport changes. Focused
board sounds follow the displayed position: new live moves remain audible while
the independent move list is scrolled. Selecting a recorded position keeps replay
quiet. Return to live resumes sound on the next move, without replaying old sounds.
Hidden boards and disabled sound remain quiet; resizing itself makes no sound.

Includes all 1.9.4 tournament extensions, draw-rule counter, season overview, and
rating-pair corrections. No tournament replay or data migration is required.

Pause and drain active games, close Engine Arena, and install the update normally.
