# Automatic tournament queue

The private 1.3.1 update adds an all-tournaments progress view to Tournament
Manager, including event/league stages. The **Source** filter selects all current
tournaments, the independent queue, or events and leagues. Search, status filters,
sortable headers and live completion counts work in both queue execution modes.
Event rows link to their parent event; they are never enrolled in the independent
queue or selected by its bulk controls. **Event resources…** edits the active
event's shared budget. See [league update notes](V1_3_LEAGUES.md).

Version 1.1.0 adds **Run together** in Tournament manager. See
[Simultaneous tournaments](SIMULTANEOUS_TOURNAMENTS.md). The sequential mode
described below remains the default for existing workspaces.

Available in the local development build after Beta 3 RC 1. The previously
delivered installer is unchanged.

1. Create and save tournaments as usual. In Tournaments, select a paused test
   and click **Add to queue**. Alternatively, open **Tournament queue** in the
   sidebar and choose **Add all unstarted tournaments**.
2. Use the up/down arrows to arrange waiting tournaments. **Edit setup…** remains
   available until a tournament actually starts. Adding a tournament to the
   queue does not freeze its setup or create game records.
3. Select **When the worker is free**, or **At a chosen time** and a local date
   and time. Click **Run queue**.

The worker finishes one tournament before starting the next, using each test's
own engine snapshots, openings, clocks, retry rules, CPU/memory/GPU budgets and
concurrency limit. Already-running manual tournaments or experiments finish
first. No extra engines are launched just because more tournaments are queued.
Timed starts require Engine Arena to stay open and the computer to stay awake;
this is not a Windows wake-up or background scheduled task.

**Pause & drain queue** stops new games and lets active games finish. Resume
with **Run queue** to continue the same tournament before later entries.
**Finish current, then pause** instead completes the entire current tournament
and stops before the next entry. Pausing or stopping the current tournament
from its normal controls also pauses automatic advancement.

Pairing dependencies, resource-admission problems, worker errors and saving
failures stop advancement for review. Ordinary engine losses and automatic
retries follow the tournament's existing rules. A frozen SPRT decision is a
successful endpoint: its running games drain before the next tournament starts.

The queue order, planned start and current tournament are transactional data
included in workspace backups. After an application crash or restart, committed
results and queue order remain; unfinished attempts are archived normally.
Review the recovered workspace and click **Run queue** to resume. The queue does
not unexpectedly launch engines on application startup.

**Remove** removes only a queue entry, retaining the tournament and its results.
Pause and drain before removing the current entry. **Clear finished entries**
cleans the list without deleting tournaments. Actual tournament deletion also
removes its queue references from the database and recovery copies. Waiting
entries are paged in groups of 50 without imposing a queue-size limit.

## Validation — September 26, 2026

- Full Python regression suite: **398 passed**. Final queue/deletion refinements
  were covered by the expanded focused queue suite; JavaScript regressions:
  **42 passed**.
- Queue tests cover deduplication, transactional bulk addition, stale actions,
  order changes, editing while waiting, timed starts, manually active work,
  pause/resume, finishing the current tournament, blocked jobs, SPRT draining,
  paginated lists, deletion and empty timed queues.
- A forcibly terminated worker retained queue order, its completed result and
  an archived interrupted attempt. Resume selected the same tournament; the
  later tournament remained unstarted and editable.
- Runner integration completed **12 UCI fixture games** across three reordered
  tournaments with no overlapping tournament dispatch and intact PGN.
- Edge acceptance completed **18 additional UCI fixture games** through the UI:
  reorder, queued setup editing, timed start, browser reload, pause-and-drain,
  finish-current, automatic advancement, and clearing finished entries.
- Eight languages passed **16 layouts at 20px text**, with no missing messages,
  page-width overflow or JavaScript errors. English and German screenshots were
  inspected. Catalogs have 2,906 messages each.
- A regression caught during development was corrected: `/api/status` now uses
  cached queue summary data and stays responsive while storage recovery occupies
  the database writer. The storage-maintenance responsiveness test passes.
- Desktop and sensor development builds succeeded. Tests used disposable
  workspaces; personal tournament data and the delivered installer were unchanged.

Evidence: `tests/test_tournament_queue.py`,
`test-output/tournament-queue-ui.json`,
`test-output/tournament-queue-languages.json`.
