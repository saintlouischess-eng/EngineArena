# Simultaneous tournaments — Engine Arena 1.2.14

Engine Arena includes an optional shared tournament scheduler. Existing
workspaces and queues remain in **One at a time** mode after upgrading.
This guide applies to stable release 1.2.14.

## Getting started

1. Create and save your tournaments as usual. Open **Tournament manager**.
2. Use **Add selected tournament** or **Add all unstarted tournaments**.
3. Click the **Run together** card at the top of the manager, then review and save a shared
   CPU thread budget, engine memory allowance, total game limit and GPU groups.
4. Click **Run tournaments**, or select particular entries and choose
   **Start / resume selected**. A row's Start action starts that tournament now,
   even when the automatic manager is paused or has a future start time.
5. Open a tournament by clicking its name. Its usual standings, focus board,
   history, clocks, reports and exports remain independent.

For one GPU that must run only one Lc0 process, use **gpu0:1** and assign the
same GPU group to every relevant engine profile. This limit applies across all
running tournaments in this workspace. Unlisted GPU groups default to one
process; zero disables a group. Two GPU engines using that same group in one
game require two process slots, so that pairing cannot run with a limit of one.
This is a process reservation, not a guarantee that engine software obeys a
physical memory or thread cap. Different workspaces/app instances are separate
schedulers; their budgets are not coordinated across the whole operating system.

## Resource sharing

Global limits and each tournament's own limits both apply. Raising the global
budget does not silently raise individual tournament limits or engine Threads.
Memory reserves both engine profiles' Hash and additional-memory allowances.
Nonpondering games reserve the greater of the two engine thread settings;
pondering games reserve their sum. Each running game's cost is retained until
its engine cleanup finishes. Hardware utilization is measured separately.

Low, Normal and High priority use relative weights of 1, 2 and 4. Scheduling
accounts for reserved resource time, rather than treating a one-thread and a
sixteen-thread game as equivalent. Weights guide sharing; they do not promise
exact percentages or completion order. Existing games are never preempted.
Large waiting games can reserve capacity as games finish, while unrelated work
uses the remaining capacity. Differing game lengths and resource constraints
can produce temporary imbalances.

Change global limits in **Shared resources…**, and per-tournament priority
or game limits through **Options…** or the bulk selection controls. Reducing a
limit lets already running games finish; new games respect the revised limit.
Changing between sequential and simultaneous mode requires pause and drain.

## Managing the list

Search names, filter statuses, and click headers to sort. The list uses pages
of 50; page size does not limit the number of tournaments. Tournament population
and scheduled games remain independent of engine-process concurrency.

- **Pause selected** stops further games for those entries. Others continue.
- **Pause all & drain** stops automatic advancement and pauses every running
  tournament in this workspace, including separately started tournaments.
- **Finish active, then pause** finishes the tournaments already running and
  leaves waiting entries unstarted.
- **Remove** removes the manager entry after it drains; it preserves all results.
- **Clear finished entries** clears the list without deleting tournament data.

A tournament that cannot fit any remaining game is held with a resource
explanation; other eligible tournaments continue. Resolve the constraint and
resume that entry. Pairing dependencies also require explicit resolution.
Saving/worker failures stop new dispatch globally. Original/retry/diagnostic/
replacement attempts and opening-pair rules are unchanged.

## Viewing and reporting

In Live boards, choose **Selected tournament** or **All running tournaments**.
Combined cards show their tournament names and retain the existing board-size
and display-count controls. Focus, search, graphs and standings retain their
selected-tournament scope.

Reports record shared scheduling limits and priority changes in run-session
evidence. Simultaneous tournaments contend for the same hardware; conditions
and measured performance can change as other games start and finish. A priority
change never changes chess clocks, engine strength settings or official scores.

## Recovery and scope

Queue membership, priorities, individual holds, execution mode and global limits
are transactional and included in backups. Restart retains committed results
and archives interrupted attempts. No engines launch automatically on recovery;
review the manager and explicitly resume. Transient fairness accounting restarts;
saved schedules and opening identities do not.

All ten independent tournament formats can use the shared scheduler. Linked
Events & leagues retain their existing ordered stage controller; they are not
independent entries in this manager. Suites and benchmarks still wait for the
tournament worker to become idle, protecting their existing execution model.

## Installing or updating

Close Engine Arena. Run `EngineArenaSetup-1.2.14-win-x64.exe` and use the same
installation folder. Existing tournament data is stored separately and is
preserved. Leave optional WebView2 repair unchecked when the runtime works.
Confirm **1.2.14** in the sidebar. Your existing tournament remains paused until
you resume it. No new sensor-driver installation is required for this feature.

Validation results for this release are recorded in its accompanying
validation receipt. Short acceptance games establish lifecycle correctness;
they are not a replacement for the owner's long-duration tests.

## Saving and managing entries

Saving shows **Saving…**, then closes the editor and selects the saved tournament.
A confirmation names it and gives its scheduled game count. It remains paused.
The database commit is acknowledged immediately; rotating recovery backups run
in the background, coalescing setup changes. Saving failures remain visible in
Worker & recovery and stop scheduling. Closing the app waits for pending copies.

Both execution modes remain visible in the manager. Changing mode requires pause
and drain; shared limits can be adjusted during play. Expand **Start time & stop
options** for timed starts or finishing active tournaments before pausing.
Select rows to reveal bulk controls. In Run together mode, each row’s **Options…**
contains priority, game limits, setup editing (until first start), and removal from
the manager. Removing an entry keeps its tournament, settings and results.
