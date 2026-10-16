# Engine Arena 1.9.9 — backup status display

Private update for the startup error `backupHealth is not defined`.

The worker can respond while the interface is still loading its scripts. The
backup status renderer and its helper now load in the same script, removing
the dependency on a later script. Saving and backup behavior are unchanged.

Includes the 1.9.8 improvements for slow startup, closing during initialization,
startup diagnostics and readable error messages.

Close Engine Arena and install over the existing version. Engines, tournaments,
games, PGNs, ratings and settings are retained. No reimport or reset is needed.

Designed by Mark Young. Coded with OpenAI Codex under his direction.
