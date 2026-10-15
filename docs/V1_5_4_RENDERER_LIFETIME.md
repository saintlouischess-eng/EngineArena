# Engine Arena 1.5.4 — long-session 3D renderer correction

Private test update, 2026-10-10. Includes the rating defaults from 1.5.3.

The focused board now keeps its canvas and renderer when following another game.
Player names, clocks, move review, crown marks and the Replay button follow the
new game without rebuilding the 3D scene. Game-specific board annotations clear.

We also corrected the bundled Three.js 0.186.1 renderer's lighting lookup texture
lifetime. Previously its shared DFG texture retained disposal listeners from
retired renderers, keeping old WebGL contexts reachable. The lookup texture is
now owned and disposed by each renderer. Lighting and piece geometry are unchanged.
The pinned dependency and MIT notice remain; scripts/three_lut_patch.py reproduces
the small local correction whenever the dependency is regenerated.

Diagnosis came from the owner's paused 1.5.2 session: no engine searches, roughly
15–19% total CPU on 32 logical processors, 960 major garbage collections in a
14.86-second trace, and hundreds of retained WebGL contexts. A heap retention
path led from the shared lighting texture through its disposal listener to the
retired context. An isolated regression exercise reproduced one retained context
per destroyed board (5 after warmup, 85 after 80 additional boards).

The corrected build retains zero retired contexts in the same exercise. The
regression also checks 200 game switches on the same canvas/renderer, updated
player names and Replay targets, 20 2D/3D switches, two independent renderers,
and no redraw while idle. The existing camera/zoom/crown/coordinate quality
checks and context-loss fallback pass. This is targeted validation; another
multi-day run has not yet been performed on this build.

This is a display-resource correction. Tournament execution, completed results,
timekeeping, rating formulas and database schema are unchanged. Existing ratings,
anchors and the main list's automatic collection setting are preserved.

Install after pausing and draining active games and closing Engine Arena normally.
The current process must be closed to release contexts retained by the old code.
Open the new version and resume the existing event. This private candidate has
not been published on GitHub.
