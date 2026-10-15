# Engine Arena 1.6.2 — 3D board presentation

Private update for Mark Young to review. Designed by Mark Young; coded with
OpenAI Codex. This package has not been published or installed automatically.

## Where to find it

Open a focused game, select **2D / 3D**, and choose **3D · 1849 Staunton**.
The same dialog now contains these saved preferences:

- **Setting & lighting:** original, Drueke walnut/maple, or Jaques purpleheart/maple board; Chess club, Championship hall, Daylight study or
  Studio; natural wood, felt or leather tabletop; daylight, warm evening or tournament
  lighting; brightness, warmth and move-highlight strength.
- **Motion & performance:** instant, quick or smooth moves; economy, balanced
  or high graphics; 15, 30 or 60 FPS animation limits. These are ceilings, not
  promises of achieved frame rates.
- **Table details:** captured-piece trays, engine nameplates and an Engine
  Arena plaque. Nameplates show only the engine name.
- **Camera views:** White, Black, Overhead, Broadcast, Room view and Piece close-up presets, plus three
  personal saved camera slots. Save a slot, then Apply to retain it.

The default **Testing** mode holds the camera still and renders when the
position, view or displayed information changes. **Presentation** adds an
optional continuous cinematic tour, slow orbit or tour of saved views. The
cinematic path changes height, angle and distance smoothly; speed is adjustable
from 50% to 150%. Camera angles now reach down to 12 degrees. Camera interaction stops the tour
at its current view. Hidden boards stop drawing and pause the tour clock; reduced-motion preferences
disable animations. Live game cards remain 2D.

Consecutive moves animate, with a small lift for knights, capture transitions,
castling and promotions. Jumps in history or switches between games are
instant. Unrecognized transitions safely show the final recorded position.
All animation is visual and does not change chess clocks or engine commands.

Captured trays reconstruct actual recorded captures, including verified opening
moves, en passant and promotions. Missing pieces in a custom starting FEN are
not guessed to have been captured. Replays use their own attempt history.

## Photos

The **Photo…** button freezes the focused position for a preview. Choose the
current camera or a preset, optionally soften the distant background, and
select **Save 4K PNG…**. The desktop app asks where to save a 3840 × 2160 image
without interface controls. Canceling leaves the game unchanged. The browser
version uses its normal download workflow. Graphics hardware must support the
required render size; failures are reported instead of silently saving a
smaller image. Live viewing resumes when the photo dialog closes.

## Appearance and performance

The yellow last-move marker has a modestly brighter fill and a thin gold edge.
The existing carved Staunton models, ebony/boxwood finishes, crown placement,
knight directions, coordinates, zoom and height controls remain available.
Four photographed 360-degree interiors replace the plain geometric rooms:
- Chess club: a furnished warm lounge with stone, wood, sofas and lamps.
- Championship hall: a grand ballroom with decorative plaster, paintings and parquet.
- Daylight study: a rustic sunlit interior with curtains, rugs and natural materials.
- Studio: a spacious loft with tall windows, brick and aged plaster.

A ground-projected photographic dome surrounds the fully 3D table and pieces.
Distant furniture is photographic scenery, not independently modeled geometry;
this is a seated board experience, not a walk-through room simulation. Foreground
tables have real wood scans, normal/roughness detail, beveled edges, brass inlay
and full-height supports. Leather uses a scanned grain material. Matching HDR
illumination supplies room reflections; board lighting remains adjustable.
Use Room rotation to choose the backdrop independently of your board angle.

Everything is bundled offline. Poly Haven assets are CC0, with individual
credits and provenance under ThirdParty/PolyHaven. The original chess models
remain Engine Arena artwork. The room textures are 2K in Economy, 4K in Balanced,
and 8K in High (subject to the graphics device's texture limit). Only the current
room's GPU textures are retained; old textures are released after switching.
Loading a replacement may temporarily retain both rooms to avoid a blank screen.
The additional offline room/material files total about 52 MB before packaging.

Continuous presentation and high graphics quality consume additional graphics
resources. Testing mode is the default. GPU chess engines and the display share
hardware; for the lightest display load use the 2D board or hide the focus panel.
Packaged acceptance recorded the RTX 5080 via Direct3D 11. These functional
checks are not a sustained GPU performance benchmark.

## Updating

Pause and drain running tests, close Engine Arena normally, then run the
installer. Resume your existing event after reopening. No tournament, profile,
rating or engine settings are changed by this presentation update.
