# Engine Arena 1.7.2 — standalone live chess club

Private review build. Designed by Mark Young; coded with OpenAI Codex.

Also fixes a Player Arena visibility race that could leave the board blank after
switching from 2D to 3D. The board now rechecks its actual visible bounds when an
older visibility callback describes the empty intermediate layout.

The rejected combination of photographic rooms and added people is replaced by
a separate **Live chess club · full 3D** environment. Its room, windows, ceiling,
parquet, bookshelves, tables, chairs, analysis board and furnishings have modeled
depth. The existing four photographic environments remain available and still.

Choose the new environment in Focus → 2D / 3D → Environment, or Player Arena →
3D board → Appearance. Selecting it enables room movement. People, illustrative
background games, subtle environmental movement and distant sounds have separate
controls. Quiet shows two visitors; Club and Busy show the four distinct visitors
at different activity speeds. Each visitor appears once, with different face,
build, hairstyle, clothing and pose. Sound remains off by default.

The main chess clock sits beside the board along the h-file, beyond the optional
captured-piece tray. A sloped face, separate White and Black displays and two
top push buttons make it recognizable as a working chess clock. It projects
the same committed clock state used by Focus or Player Arena; it cannot alter
the game. Node/depth searches show **ELAPSED**, not a chess-clock deadline.
Unknown readings remain blank; stale Focus readings stop advancing and show
WAIT. Reviewing moves uses the saved clocks. Background clocks are illustrative.

The main game and background illustrations are independent. Scenery creates no
engine processes, tournament results, ratings or PGNs. The two background boards
follow a verified legal opening, including both castles. No external downloads
or online service are used at runtime. Graphics share the GPU with any GPU engine.

The existing quality and 15/30/60 FPS limits apply. Economy omits ambient-occlusion
postprocessing and reduces shadow resolution. Hidden/offscreen boards stop
rendering. Reduced motion pauses scenery; actual game clocks can still update.
4K photos use the same compositor, with optional depth-aware background blur.
The live club has a fixed coordinated table layout: photographic room rotation
and table-surface controls are disabled for this environment; the camera and
board design remain adjustable.

This is one new live room. The visitors are textured background game characters,
not photoreal actors. Artistic approval and performance on the owner's laptop
remain part of private review; do not describe functional tests as AAA acceptance.

## Validation

`scripts/validate_club.cjs` exercises the actual renderer on disposable data:
separate photographic and modeled rooms, lazy character loading, four distinct
visitors, actual clock projection, motion controls, repeated room changes with
stable warmed GPU resources, Focus and Player Arena visibility, frame limits,
eight UI languages and 3840 × 2160 PNGs with and without depth blur.

`tests/test_ui_table_clock.cjs` covers clock projection, stale updates, delay,
node-only clocks, untimed practice, recorded review and nonmutation of game time.
`tests/test_club_assets.py` checks pinned source hashes, self-contained clothed
models, distinct cast inputs, local addon imports and legal illustrative moves.
Existing Player Arena workflow regression covers mouse movement, promotion,
game completion and PGN export. Test databases are under `test-output`; production
tournaments are not opened or modified by these checks.

## Rebuilding artwork

All third-party graphical inputs are CC0; Three addons are MIT. See
`vendor/MakeHuman/club-cast/provenance.json`, `derived.json` and
`vendor/Three/club-addons.json`. Original modeling/fitting code is included.
Run Blender with `scripts/build_club_cast.py` for the cast, and
`prototypes/live-club/build_lod.py` for distant pieces. Then run
`scripts/sync_club_assets.py` to copy the room, cast, distant pieces and pinned
addons to the offline UI. No MakeHuman program is required.
