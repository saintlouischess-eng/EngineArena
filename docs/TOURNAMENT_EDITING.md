# Editing a tournament before starting

Available in the local development build after Beta 3 RC 1. The previously
delivered installer does not contain this update.

Select a saved tournament and choose **Edit setup…** beside the tournament
selector. Change its name, format, match lengths, time controls, openings,
resource budgets or other setup options, check the scheduled game count, then
choose **Save changes**. It stays paused and retains its tournament ID and
creation time. Closing the editor without saving leaves it unchanged.

**Keep saved engines and settings** is the default. To replace the field or
refresh profiles from the engine library, select the desired profiles in
Engine library first, return to the tournament editor, and select **Use current
Engine library selection**. Selecting a resource preset explicitly updates the
participants' thread and hash allocations as well as the displayed controls.

**Keep recorded opening positions** retains the saved opening pool and source
name, even if the original opening file has moved. Choose another source to
replace it. Unchanged shuffle settings keep the same order; changing seed or
order applies the new ordering to the original pool rather than shuffling an
already-shuffled list again. New opening sources replace the old source metadata.

Editing is allowed only before the first Start action, with no materialized
games, attempts or round/pairing history. Pausing, recovering or resetting games
does not unlock an already-started tournament. The backend enforces this rule,
including when another window starts a tournament while its editor is open.
An editor opened before another setup or concurrency change must be reopened.

Saves are transactional, audited and included in recovery backups. Standings,
seeds and report revisions are rebuilt for the revised empty field. No games
are expanded during editing, even for large participant lists. Backup copying
runs outside the scheduler's lifecycle lock so other tournaments can proceed.

## Validation — September 26, 2026

- Full Python suite: 384 passed before adding the final edited-game execution
  test. The expanded editing suite has 19 passing tests, including six completed
  UCI fixture games and PGN verification; 42 JavaScript regressions passed.
- Guard coverage includes start/pause before any dispatch, pending games,
  attempts, invalidated attempts, completed tournaments, pairing records,
  historical schema migration, stale editors and concurrent limit changes.
- Invalid settings and an injected transaction failure retain the original
  setup. Forced process exit retains committed edits. A recovery backup contains
  the revised setup. A delayed-backup test verifies the scheduler is unlocked.
- Editing a 10,000-engine field produces its 99,990,000-game count without
  creating game records. User tournament data was not opened by these tests.
- Edge acceptance: cancel, name-only preservation, schedule recalculation,
  engine and opening replacement, KO per-round lengths and tiebreak controls,
  legacy tie policy, start/edit conflict, and new-tournament regression passed.
- All eight supported languages passed at 20px text with no missing messages,
  horizontal dialog overflow or JavaScript errors. Screenshots were inspected.
- Desktop and sensor development builds succeeded. Installer unchanged;
  publication remains on hold.

Evidence: `test-output/tournament-edit-ui.json`,
`test-output/tournament-edit-languages.json`, `tests/test_tournament_edit.py`.
