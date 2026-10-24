# Engine Arena 1.10.3 — independent engine reply timestamps

This update includes all 1.10 workflow features and the fair round-robin
replacement/retained-ratings options from 1.10.2.

## Clock correction

Previously, UCI output was read and timestamped on the application's asyncio
event loop. If another operation stalled that loop, an engine could have its
on-time reply processed after the deadline and receive an incorrect time loss.
An isolated three-engine test reproduced this behavior.

Independent pipe readers now record each complete reply's monotonic receipt
time. Search timing starts when the command is written. Game logic uses those
timestamps, even when the application processes the reply later. It does not
trust the engine's own reported thinking time or grant extra clock tolerance.

Actual late replies still lose on time. Silent-engine and ponder-stop watchdogs,
illegal-move checks, and clock-debt rules remain enforced. Ponder receipts are
associated with their own search. Reader buffers are bounded; excess stale
thinking output can be discarded while protocol replies are preserved.
Noticeably delayed reply processing is recorded in the attempt's UCI diagnostics.

This protects against an application event-loop delay. It cannot guarantee
receipt timing through a whole-system freeze, suspension, or a delay that also
prevents the independent reader from running. The exact external trigger for the
October 23 overnight incident was not established from the retained evidence.

## Update an existing installation

Pause and drain your tournaments, close Engine Arena, install the update over
the current version, and resume. Existing settings, games, ratings, and roster
revisions are retained. Installing does not replay games or revise past results.

Designed by Mark Young. Coded with OpenAI Codex.
