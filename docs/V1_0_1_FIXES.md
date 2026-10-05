# Engine Arena 1.0.1 — endurance-test corrections

Designed by Mark Young.

This local update addresses findings from the long-running Version 1.0 tournament audit. Public release remains pending final approval.

## Installing and continuing an existing tournament

1. Pause and drain active games, then close Engine Arena.
2. Run `EngineArenaSetup-1.0.1-win-x64.exe` and use the existing installation folder. The program files are updated; the separate tournament data folder is retained. Optional WebView2 repair remains unnecessary when the runtime already works.
3. Open Engine Arena and confirm **1.0.1** in the sidebar. Your tournament opens paused with its completed results intact.
4. To reduce existing database and backup sizes, open **Worker & recovery → Storage & backup settings → Reclaim disk space** before resuming. This optional maintenance preserves every stored diagnostic line, move, result, attempt, opening and setting. Large histories can take several minutes or longer. Progress stays available; interrupted maintenance resumes safely. Keep the app open until cleanup completes.
5. Resume the same tournament. Completed games are retained; only unfinished work resumes/restarts from recorded openings. No past timeout or illegal-move result is silently replaced.

Newly completed games automatically use the improved diagnostic packing. Existing completed games receive that packing when storage maintenance runs. The size forecast is based on the workspace's observed history and updates after cleanup; it is not a promised final size.

## Changes

- Chess deadlines are checked against the high-resolution elapsed clock. An early Windows event-loop timer wakeup cannot immediately cause a time-forfeit loss. Failure evidence records measured elapsed time and the allowance. Chess clocks, pure-node/depth searches and hang watchdogs remain distinct.
- Invalid engine telemetry is excluded consistently from live/replay displays, graphs, technical summaries and detailed PGN annotations. Raw historical records and diagnostic logs are preserved. Negative speed readings and zero reported time during a measured search are not substituted with invented values.
- Known legacy thread options (`Number of Threads`, `MaxThreads`, `Max CPUs`) are recognized alongside `Threads` in engine setup, resource budgets, reports, PGN headers and thread-scaling benchmarks. The exact observed option remains visible in reports.
- Routine live standings requests omit the unchanged opening inventory. Setup and exports retain access to the full saved openings.
- Completed-game diagnostic blocks are packed together using lossless compression, retaining original line IDs and timestamps. Maintenance applies the same optimization to historical games and recovery copies. Interrupted batches roll back and can be retried.
- The storage panel displays the effective adaptive backup interval, which may be longer than the configured minimum when backups are slow.
- The sidebar and installer information include **Designed by Mark Young**.

## Validation scope

The local regression suite, targeted deadline/telemetry/legacy-resource/storage tests, and packaged acceptance checks accompany this update. Validation includes early timer wakeups, on-time and late bestmoves, clock-free hang limits, atomic rollback during log packing, historical export filtering, large opening inventories, PGN preservation and reopening existing tournament data.

The earlier `V1_REVIEW.md` records the original Version 1.0 review; it does not supersede these corrections. Installer checksum and validation receipt are supplied alongside the installer. The continuing endurance tournament will be audited again after completion.
