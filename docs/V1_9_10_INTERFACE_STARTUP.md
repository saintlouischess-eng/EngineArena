# Engine Arena 1.9.10 — reliable interface startup

Fixes `renderStandings is not defined` when a saved tournament loads before
the standings script is ready. All interface API calls now wait for the page's
scripts to finish loading. This also protects other panels from the same
startup ordering problem, including preferences and backup status.

The wait ends at DOMContentLoaded; it does not wait for 3D models, textures,
or other images. Normal polling continues after initialization. Worker-side
game execution, clocks, scheduling, statistics and saving are unchanged.

Use **Pause & drain**, wait until no games are active, then close Engine Arena
and install this update over the existing version. Saved engines, tournaments,
games, PGNs, ratings and settings are retained. Resume the tournament afterward.

Designed by Mark Young. Coded with OpenAI Codex under his direction.
