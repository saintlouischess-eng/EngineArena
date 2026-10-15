# Engine Arena 1.5.9 — tournament workspace refresh

Private test update. Designed by Mark Young; programming by OpenAI Codex.

The tournament selector now checks for additions, renames, removals and state
changes every five seconds. Event stages created automatically, or from another
window, appear without reopening the application. This also works when the
workspace initially contains no tournaments.

Your selected tournament stays selected while it exists, including completed
qualification results. Choose a new division from the list when ready. Unchanged
options are kept in place, and older list responses cannot replace newer ones.
Failed list requests are rate limited and do not mark working hardware readings
as disconnected.

This changes display synchronization only. Scheduling, clocks, engine processes,
results, ratings and stored event conditions are unchanged. The softer 3D lighting
and move-history improvements from 1.5.8 are included.

Install after pausing and draining the event, then closing Engine Arena normally.
Reopen and resume the existing event afterward. This build is not published.
