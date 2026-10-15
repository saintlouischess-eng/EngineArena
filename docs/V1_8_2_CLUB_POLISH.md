# Engine Arena 1.8.2 — Club cast and camera polish

Private test update requested by Mark Young. Design: Mark Young. Implementation:
OpenAI Codex. Install after pausing/draining games and closing Engine Arena.

## What changed

- Eight footwear styles across the twelve club characters: loafers, court
  sneakers, trainers, flats, Oxfords, ankle boots, Derbies and Chelsea boots.
  Colors, toe shapes, lacing, soles and trim vary by person. Socks retain their
  ankle deformation; the lower shoes and soles follow the feet together.
- Small independent hand shifts, finger curls and arm adjustments, with
  individual spectator resting poses. Gestures ease away during a piece or
  clock reach. Room pause, reduced motion and hidden views still stop animation.
- Rebuilt cameo hair with solid foundations, shaped locks and fine strands;
  removed the old sparse wire curls and long blocky sideburns. Adjusted Fabiano's
  face proportions and Levy's glasses. Nakamura and Rozman have fitted opaque
  beard surfaces and fine growth around the face rather than only a frontal
  painted beard. These remain artistic interpretations, not scanned likenesses.
- Consistent 3D input in both workspaces: **right-drag** or **Alt+left-drag**
  rotates the camera; hold **Shift** at the start of that drag to change height;
  the wheel zooms. Normal left-click/drag remains chess input in Player Arena.
- Player 3D canvas also supports the focused board's camera keys: arrows,
  Shift+Up/Down, plus/minus and Home. The canvas must have keyboard focus.
  2D arrow-key square navigation remains available.
- Shared wheel-unit handling, drag threshold and camera sensitivity. Updated
  camera guidance in English, Spanish, French, German, Portuguese, Italian,
  Dutch and Polish.

## Three review passes

1. Compared front/side portraits and footwear with the prior models. Added
   varied shoes, opaque grooming, bounded idle gestures and common camera input.
2. Fixed coarse beard edges, excessive smooth-cap shine, hidden shoe details
   and inconsistent wheel-unit handling. Verified walking palms face inward,
   feet stay planted and hands meet pieces and clock buttons.
3. Refined beard surface continuity, reduced hair geometry, closed sole seams
   and corrected the seated ankle attachment. Exercised actual mouse/keyboard
   workflows, eight-language guidance and the delivered room/recovery behavior.

The preview art and software-rendered acceptance evidence live under
`test-output/cast-before`, `cast-pass1`, `cast-pass2`, `cast-pass3` and the final
review folder. Build and validation logs use the `v182-` prefix. Tests use only
disposable databases; no production tournament or settings are changed.

Public portrait references were inspected only as modeling guides and are not
shipped in the app: [Caruana](https://tatasteelchess.com/nl/masters-2025/players/15/caruana-fabiano),
[Rozman](https://worldchess.com/profile/7118), and the Nakamura reference listed
in `prototypes/live-club/art/README.md`. Original portrait textures retain their
existing artwork license and provenance.

The 1.8.1 graphics-recovery changes remain included. Software WebGL tests check
recovery behavior; they do not reproduce or establish the cause of a Windows
GPU-driver reset. Final appearance and hardware performance remain part of the
owner's test on the installed build.
