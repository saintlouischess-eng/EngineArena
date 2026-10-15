# Standalone live chess club — architectural study

This is a separate, local visual prototype, **not a release candidate**. It does
not load Engine Arena's database, preferences, engines, worker or tournament APIs.
Its room artwork is integrated into private 1.7.4; this standalone
preview remains separate from the working application. Rebuilding sources are
included with the installer.

The old photographic-room/live-character hybrid was rejected by the owner. This
study replaces it with a fully modeled room: continuous geometry, furniture,
window openings, materials and lighting. It reuses the accepted detailed Staunton
sculptures and board, and existing CC0 scanned material maps. No photographic
room panorama or MakeHuman head asset is loaded.

The default architecture preview is unpopulated. Add `?cast` to inspect four
separately morphed, clothed and rigged players and eight rotating visitors.
Six visitors are artistic chess-player cameos, including IM Levy Rozman.
At most two visitors join the four seated players. Each person appears only
once at a time, with a different face, build, hair and clothes. The app and
preview share coordinated piece/hand/clock motions and visitor
walking, watching and arrival/exit routines. Room motion demonstrates curtains,
foliage, a pendulum and legal illustrative opening sequences. Clocks sit beside
each board, with sloped displays and two push buttons. All preview clocks are
illustrative; the integrated app's main clock uses actual game readings.

Run from the project root:

    .venv\Scripts\python.exe prototypes/live-club/serve.py

Open http://127.0.0.1:8769/prototypes/live-club/ . Drag to orbit, scroll to zoom,
use camera presets or the tour. H hides controls. Motion stops on hidden tabs;
the first preview targets at most 30 FPS and starts still under reduced motion.

This is a geometry/material/lighting proof, not a claim of photoreal characters,
finished gameplay integration or validated tournament-performance overhead.
Static furniture and foliage are batched by material. Distant chess meshes use
a geometry-only reduction of the original sculptures (21,312 vs 327,958
polygons for the six models); the detailed main board is retained. Three.js
0.186.1 MIT-licensed post-processing addons add screen-space contact shading.
Their package checksum and source hashes are recorded under addons/.

Further work: character art and rigging, exterior window views, fine material
work, camera collision limits, accessibility/control polish, and measurements
on integrated graphics before public release.
