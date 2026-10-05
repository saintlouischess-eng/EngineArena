# Engine Arena 1.2.10 — 1849 Staunton view

The optional focused 3D board now uses original Blender models informed by
close-up photographs of early Jaques sets. Select **Focused game → 2D / 3D →
3D · 1849 Staunton**. Drag to orbit, use the arrow keys, or press Home to reset.
Viewing angle and zoom remain adjustable. The default board and live cards are 2D.

The six new forms have broad turned bases, distinct piece heights, a flared king's
cross, a cut queen's coronet, deep bishop mitre, notched rook turret and carved
knight. The knight has an open mouth, recessed nostrils and eyes, cheek/neck
grooves, small ears and a ribbed mane. This is an original interpretation of the
historical style, not a scan, exact replica, or endorsed Jaques product.

The materials use original 4096px color, normal and roughness maps, polished
boxwood/ebony finishes, environment reflections, key/fill lighting and cast
shadows. Both sides remain illuminated in light and dark application themes.
No purchased model, photograph or stock texture is embedded.

## References and authoring

The main visual reference was [Alan Fersht's 1849–50 Entered No. 8 gallery](https://www.britishchesssets.com/chess/No8/index.html), particularly its knight side views, complete piece lineup and king's cross close-up.
The [Jaques historical reproduction](https://www.jaqueslondon.co.uk/products/luxury-chess-set) supplied an additional proportion/material reference.

`scripts/build_staunton1849.py` and `scripts/sculpt_staunton_knight.py` author the geometry, pack UVs, bake all three
maps and export `ui/staunton1849.glb`. It was run in Blender 5.2.0 LTS:

```
blender --background --factory-startup --threads 8 --python-exit-code 1 --python scripts/build_staunton1849.py
```

Generated authoring files are under `media/staunton1849`. The script and final
asset ship in the source snapshot; Blender is not required to run Engine Arena.
The `--no-bake` option only reuses maps for unchanged geometry/UVs.

## Rendering and resource behavior

Three.js 0.186.1 and its GLTF loader are bundled locally under MIT, with a pinned
SHA-512 archive and a repeatable `scripts/vendor_three.py` fetch recipe. No CDN,
account or internet connection is needed. Licenses accompany the installer.

The renderer and model load only after 3D is requested. One focused board owns
one WebGL2 context and disposes its GPU resources when returning to 2D. Geometry
and textures are shared between pieces within that view. Rendered frames update
on board/camera/size/theme changes; there is no continuous animation loop or
extra engine analysis. Shadow maps are reused for camera changes. Unsupported
WebGL2 or a lost graphics context falls back to the 2D board.

This higher-detail view costs more GPU memory and drawing work than 2D. It is
optional and not enabled on the live game cards. Laptop graphics performance
still needs the owner's device test; software-rendered validation is not a
hardware benchmark.

## Validation

Automated checks cover embedded model integrity and local dependencies,
all existing JavaScript tests, targeted workflow/release/artwork/localization
Python tests, all eight translation catalogs, actual-app visual inspection,
idle rendering, controls, context-loss fallback and packaged viewing/setup
workflows in all eight languages. Exact outcomes accompany the installer in its
validation sidecar. No production tournament data or installed application is
modified by these checks. This candidate is prepared locally, not published.

## Earlier knight reconstruction

The earlier round-form knight was replaced with a continuous sculpted contour,
full neck cross-sections, shaped cheek/jaw and a narrower muzzle. Inset eyes,
nostrils, tapered lips, an open mouth with a small carved tooth row, leaf-shaped
ears, deeper facial folds and a continuous comb mane are part of the model.
Boolean cuts are validated and the surface is polished before UV mapping.
The final mesh targets 125,000 triangles, shared by every knight in the view.
Wood maps include restrained baked cavity shading. The larger texture maps
use more GPU memory than the earlier 2K atlas; they load only with the optional
3D view. Default 2D viewing does not load these model/material resources.

Four-angle clay inspection is reproducible with `--clay-preview`, or with
`scripts/render_knight_study.py` after a complete build. The scripts
`review_staunton_knight.cjs` and `validate_board3d_quality.cjs` inspect the actual
GLB/materials and focused-board renderer on isolated workflow fixtures.
The close-up study changes camera and arrangement, not the exported sculpture.

Additional multi-angle form reference: [Royal Chess Mall's 1849-style reproduction gallery](https://royalchessmall.com/en-ch/products/1849-jaques-cook-staunton-chess-pieces-only-collectors-set-ebony-wood-3-75).
The original No. 8 photographs remain the principal historical reference.


## 1.2.4 multi-angle proportion review

The owner identified an over-wide frontal head, a pinched head-to-neck join,
and an excessively deep queen crown. These were geometry issues, not texture
resolution problems. The new sculpture narrows and rounds the knight’s head,
widens its throat in profile, blends its frontal taper over a longer neck region,
and refines the muzzle, ear folds and upper mane. The queen has a solid convex
cap and shallow pointed rim, with a lower overall height. The king has a smaller
cross and domed crown; the bishop has a wider cut and attached knop; the rook
has a deeper turret recess; all pieces have more defined turned foot profiles,
and the pawn has a flatter collar.

The original No. 8 gallery remains the main silhouette reference. The additional
[House of Staunton / Camaratta 1849 Cooke gallery](https://www.houseofstaunton.com/products/the-1849-cooke-luxury-chess-pieces-4-4-king-from-the-camaratta-collection)
was inspected for close and elevated views: photographs 02 (king), 03 (queen),
04 (bishop), 05/16/19 (knights), 06/18 (rook), and 07 (pawns). These modern
reproduction photographs help explain surfaces hidden in the historical side
views; their marketing claims are not a substitute for measured originals.

The reference checklist also documents differences between early hand-carved
pieces and production runs: [Alan Fersht’s collector checklist](https://www.britishchesssets.com/checklist.html).
Proportions here are estimated from photographs, with perspective limitations.
This remains an original 1849-style interpretation, not an exact measured replica.
No reference photograph, maker stamp or third-party mesh is included in the app.

`study_staunton_set.py` adds true-front and elevated whole-set clay views and a
queen crown close-up. The actual exported GLB is also inspected as boxwood and
ebony lineups, front/side/three-quarter knights, and crown close-ups using the
application’s material and lighting settings. These studies are geometry reviews;
they do not claim that automated checks establish artistic fidelity.


## 1.2.5 queen crown correction

The owner accepted the knight but requested a substantially rounder central
queen dome and a recessed channel inside taller coronet points. The earlier cap
blended into its rim and read as a flat scalloped surface. The queen now has a
raised rounded dome supporting the ball, an annular recess, and taller pointed
rim geometry. Side and elevated close-ups are saved in the review directory.

Only the queen sculpture changes. The `--reuse-other-pieces` build option reads
the five accepted sculptures from the existing authoring blend; it does not
regenerate the knight. The shared 4K atlas is repacked and fully rebaked for the
new geometry. `--queen-preview --reuse-other-pieces` provides a quick clay review
without changing the production GLB or final authoring blend. Do not use
`--no-bake` after changing the crown geometry.


## 1.2.6 nine-point flared coronet

The owner requested exactly nine points, slightly shorter and more flared out.
The coronet now uses nine equal lobes with 28 angular samples per lobe. The
point-height contribution is reduced from 0.065 to 0.049 model units; the outer
tips extend farther outward. The raised dome, ball, recessed annular channel,
lower queen body and other five sculptures are retained. Side, elevated and
true overhead reviews make both the silhouette and point count inspectable.
The shared 4K wood maps are fully rebaked for the revised crown geometry.


## 1.2.8 stem and bishop-finial refinements

Re-examined the original Entered No. 8 [piece lineup](https://www.britishchesssets.com/chess/No8/PiecesandBasesLR.jpg)
and [bishop close-up](https://www.britishchesssets.com/chess/No8/Bishops1.jpg).
The king and queen now have slimmer concave stems with a more gradual outward
curve into the upper collar. Their bases, heights and crown designs are retained.
The bishop’s finial is enlarged and raised above the mitre instead of being
mostly buried in its tip. These proportions remain an interpretation of photos.

`--reuse-pieces n r p` preserves the accepted knight, rook and pawn exactly.
`--proportion-preview --reuse-pieces n r p` renders clay silhouettes and a bishop
finial close-up without replacing the final model. All three 4K maps must be
rebaked after the geometry changes. The direct 60–240% zoom controls introduced
in 1.2.7 are retained.

## 1.2.9 framing and traditional crown stamps

The Height slider, down/up buttons and center button adjust screen-relative
vertical framing independently of zoom, tilt and orbit. Shift-drag and
Shift+Up/Down offer direct adjustment; Home resets the complete camera.
Position is saved and follows docked, floating and expanded windows.

Original red crown artwork follows the supplied reference: the knight forehead
and recessed rook turret top. A small surface-conforming mesh sits on the
existing sculpture, using the same scene lighting. It adds 288 triangles per
marked piece, at most four pieces; source geometry and wood maps are unchanged.
The projection is prepared once with the lazily loaded assets, not each move.

Historical reference: [Regency Chess crown markings](https://www.regencychess.co.uk/blog/2026/02/kings-crown-markings-explained/),
and the owner's accompanying photograph. No third-party image is embedded.
The crown is an original ornamental motif, not a Jaques maker's wordmark.

The worker tracks the four original pieces using verified opening history and
legal moves. Scoresheet pages reconstruct identity within that attempt, so old
records, castling, captures, promotions, restarts and diagnostic replays agree.
No additional database records are stored. Unknown origins (FEN-only midgames,
invalid history, or nonstandard Chess960 starts) are left unmarked.
The 2D / 3D dialog provides a saved crown-mark toggle.

## 1.2.10 unobstructed viewing

The focused-game header has Hide 3D controls / Show 3D controls. This hides or
restores the zoom/height overlay, preserving the saved camera. The 2D / 3D dialog
has the same saved checkbox. The header button remains accessible when the
overlay is hidden, and disappears when viewing 2D. Mouse and keyboard camera
adjustments still work. Display & layout separately controls Hover help.

## 1.2.12 board coordinates respect scene depth

Files and ranks are now lettering on the wooden frame, instead of HTML labels
over the rendered image. The letters follow the board's perspective and scale;
nearer pieces hide them through the same depth buffer used for the scene.
The two camera-facing frame edges retain eight files and eight ranks when
rotating or flipping. A single atlas and 32 triangles add one draw call; geometry
changes only when the selected frame edges change. Idle views do not redraw.
The accepted sculptures, crown stamps, textures and lighting are unchanged.

## 1.2.13 coordinate orientation

Letters and rank numbers now face the current viewing direction, rather than
orienting rank numbers toward a side rail. Their quads rotate within the board
plane with the camera's orbit, keeping both sets of labels upright and readable
after board flip. They remain on the frame and depth-tested. Quad extents stay
inside the frame even at diagonal angles; glyph size is retained. Geometry is
updated when orientation changes, with no idle rendering or extra draw calls.
