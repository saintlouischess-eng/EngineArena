# Engine Arena 1.9.8 — startup and closing reliability

Private test update; not yet published.

Large workspaces no longer fail solely because the worker needs more than one
minute to finish opening. The startup window shows its current step and elapsed
time, with a Close button. Database integrity checks and recovery remain enabled.

Closing during incomplete startup now cancels initialization, sends a graceful
shutdown when the worker has become ready, or stops this window's own worker if
it has not connected. Normal shutdown still waits for saved records and verified
backups. The window no longer waits forever for a worker that did not receive a
shutdown request.

Startup errors use a readable panel with details and a Close button. WebView2 is
shown after its first successful navigation, avoiding a blank startup surface.
Readiness files are written atomically, and each window validates its worker's
fresh session token. Startup stages and errors are retained in `startup.log` and
`startup.log.previous` in the data folder; diagnostic file size is bounded.

Install over the existing version after closing Engine Arena. Saved engines,
tournaments, games, PGNs and ratings are retained. No reset or reimport is needed.

Designed by Mark Young. Coded with OpenAI Codex under his direction.
