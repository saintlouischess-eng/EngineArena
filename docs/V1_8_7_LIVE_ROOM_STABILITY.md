# Engine Arena 1.8.7 — live room stability

Private owner build. Not published or installed automatically.

## Evidence and scope

The owner reported repeated display recoveries while watching the expanded
live room, including while GPU temperature and utilization were low. Windows
recorded NVIDIA TDR recovery and LiveKernelEvent 141 on October 12, 2026 at
approximately 22:15 local time, with earlier events at 14:53 and 19:43.
The saved room settings selected High quality and 60 FPS on an RTX 5080.
These records establish a graphics timeout, not its exact underlying cause.
No conclusion about overheating, overclocking or insufficient hardware is drawn.

## Changes

- The shared board renderer no longer assigns canvas width/height every frame.
  It resizes only after an actual viewport or resolution change, with one
  drawing-buffer resize instead of separate pixel-ratio and size allocations.
- Nonblocking WebGL2 fences allow only one unfinished frame per renderer.
  Busy frames are coalesced to the most recent position/camera. The interface
  never spins waiting for completion or calls `gl.finish()`.
- Live-room resolution has an aspect-preserving pixel budget: Economy 921,600,
  Balanced 2,073,600 and High 3,686,400 pixels (720p/1080p/1440p equivalents).
  Fullscreen and high-DPI windows retain their CSS size and mouse coordinates.
  Explicit photos still render at 3840 × 2160.
- Ambient occlusion renders at half color resolution, with a 1280-pixel longest
  dimension cap. Color buffers retain two-sample antialiasing. The room shadow
  map is bounded at 2048; decorative moving shadows refresh at most 15 Hz.
  Board moves still refresh their shadows immediately. Fine hair/beard strands
  no longer render into shadow maps; their solid foundations still do.
- Room disposal explicitly releases the ambient-occlusion noise texture and
  shader material omitted by the pinned upstream pass's disposal function.
- A lost live-room graphics context stays in usable 2D until **Retry 3D** is
  selected, including after navigating away and reopening the workspace. It
  does not automatically recreate the same animated scene three
  seconds after a driver reset. Other rooms retain one automatic retry.
- Local graphics diagnostics record context losses and WebView2 process failures.
  Native logs are `graphics-diagnostics.jsonl` plus one rotated file, each up to
  1 MiB, in the app's data folder. Browser diagnostics retain the last 20 entries.
  They record graphics state, not engine secrets or game data. Logging failures
  cannot interrupt play.

Tournament state, engine execution and clock rules are unchanged. No driver,
clock/voltage, Windows TDR registry or system setting is modified.

## Validation and remaining limitation

Validation uses a disposable data folder and software WebGL. It covers real
fullscreen/high-DPI targets, repeated-frame canvas writes, busy-frame coalescing,
stable warm resources, 4K photos, both workspaces and simulated context loss.
Regression coverage includes ordinary-room recovery, visibility handling,
localization and release resources. Final evidence is recorded in HANDOFF.md
and the installer's validation sidecar.

These are verified rendering corrections and stability safeguards, not proof
that every physical-driver failure is solved. Sustained use on the owner's
affected GPU remains the final acceptance test. No physical reset or deliberate
GPU stress is performed during automated validation.

Pause and drain testing, close Engine Arena, then install the private update.
