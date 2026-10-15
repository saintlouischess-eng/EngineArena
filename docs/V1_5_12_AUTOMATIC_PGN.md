# Engine Arena 1.5.12 — automatic official PGN files

Private development update for Mark Young’s testing. Not published to GitHub.
Suggested by Jean-Paul (Ipmanchess), approved by Mark Young.

## Workflow

In **New tournament → Automatic PGN file**, enable **Save official games
automatically to my file**, choose a destination, file mode and export preset.
The same controls are available later through **Results & exports → Automatic
PGN…**, including while games are running and for completed tournaments.

- **New file** refuses to overwrite an existing nonempty PGN or managed export.
- **Append / continue** adds this tournament to an existing file. Several
  tournaments can share one destination, including simultaneous tournaments and
  separate tests run on different days. Existing completed official results are
  included when a tournament is connected.
- **Remember this destination for new tournaments** selects it automatically for
  subsequent setups. Saved destinations make switching between rating lists easy.
- Each destination has one formatting preset: Clean, Annotated, Engine testing
  or Complete archive. Select another file to use a different preset.
- Turning the setting off leaves the exported file intact. Turning it on again
  reconciles official games completed while it was disabled.

The existing one-time **Save PGN as…** export continues to replace its chosen
destination after an overwrite confirmation. Use **Automatic PGN…** for the
continuing, shared-file workflow.

## Integrity and recovery

Automatic output contains current official results. Diagnostic and interrupted
attempts remain in Engine Arena’s original history and internal journals.
Replacement results replace the previous exported result for that GameId.
Explicit result resets and invalidated dependent rounds remove their obsolete
official records. Original attempts inside the tournament are never changed.

Automatic PGNs always include GameId, TournamentId and AttemptId, even with the
Clean preset. An adjacent **.arena-pgn.sqlite3** export index keeps exact PGN
records and recovery state. Keep it beside the destination for safe continuation;
share a copy of just the PGN. The index stores one current export per game,
not moves, logs or an additional tournament-history database. It therefore adds
roughly another PGN’s size plus SQLite indexing overhead. A small lock file also
prevents different Engine Arena workers from writing the same destination.

Existing UTF-8 PGNs can be adopted. Their exact game text is retained. GameId
records can be matched; games without identifiers are retained as external
records and **cannot be deduplicated against tournament records**. Do not first
export a Clean PGN without IDs and then connect that same tournament to it if
you want one copy per game. Use a fresh automatic destination instead.

The writer commits its intended changes to the export index, writes and flushes
the PGN, then acknowledges the file fingerprint. Restart recovery repairs partial
appends and handles an atomic replacement completed before acknowledgement.
Ordinary new games append incrementally; replacements stream an atomic rewrite.
Work runs separately from the game/clock event loop and database actor, in bounded
batches. A large initial export can take time; subsequent new results do not
re-render existing games.

File errors appear in **Worker & recovery**, with **Retry saving**, and the
Automatic PGN menu button shows that attention is needed. Official results remain
committed in the tournament database and games continue. External edits are
detected; the writer stops touching that destination rather than erasing them.
Choose another file or restore its matching PGN and index before retrying.

Deleting a tournament first flushes its connected outputs. The separately chosen
PGN and index remain in the owner’s chosen folder, including when internal game
records are deleted. Manage/delete those external files yourself after disconnecting
their tournaments; Engine Arena’s managed-storage cleanup does not delete them.

## Installation

Pause and drain the current test, close Engine Arena normally, and run
**EngineArenaSetup-1.5.12-win-x64.exe**. Reopen and resume the existing event.
This update includes the accepted ebony finish and all preceding fixes. It does
not enable external exports on existing tournaments until a destination is selected.
