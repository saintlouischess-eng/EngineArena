# Engine Arena 1.10.1 — withdraw from an ongoing round robin

Designed by Mark Young. Coded with OpenAI Codex.

This update includes all ten 1.10.0 workflow features and the 1.9.13 large-list
Rating Center fix. It adds withdrawal from a paused, fully drained standalone RR.

## Workflow

1. Pause and drain the tournament. Wait for every active game to finish.
2. Open **RR roster…**, then **Withdraw engines from future games**.
3. Select one or more entrants. Optionally select new profiles to add.
4. **Preview roster changes** shows retained results, canceled unplayed games,
   any added games, the active field size and the revised scheduled total.
5. Save, review the standings, and resume when ready. Saving never restarts play.

Completed games keep their original moves, results, points, engine snapshots,
PGNs and Rating Center history. Withdrawn entrants remain marked in standings,
and their opponents keep all points earned against them. Future games involving
withdrawn entrants are canceled without forfeits or awarded points. No placeholder
results are created. Game totals may therefore differ between entrants.

Both already queued and not-yet-generated matchups are covered. Interrupted
attempts remain in the attempt history, but unfinished games involving withdrawn
entrants are not resumed. A completed game queued for a replay keeps its existing
official result and the replay is canceled. Replay commands skip withdrawn
entrants. If only one color of an opening pair was completed, that game remains
recorded; the canceled return game does not become a draw or a complete pair.

New entrants play only currently active entrants and one another, with the chosen
catch-up/interleave/after-existing setting. Existing game IDs, openings, results
and schedules between active entrants are preserved. At least two active entrants
must remain after applying the changes. The engine-library profile and files are
not deleted. Re-entry under the same participant identity is not supported.

Completed-RR withdrawal retains the existing, explicitly previewed behavior:
revised standings exclude the selected entrant's games for both sides, while
historical Rating Center evidence and original roster revisions remain available.
The dialog distinguishes this from ongoing withdrawal, which keeps all played
results in the current standings. Event stages and other formats are excluded.

## Installation

Pause/drain and close Engine Arena, install 1.10.1 over the existing version, and
resume the saved tournament. No reset is needed. The candidate is provided for
owner testing and is not published or installed automatically.
