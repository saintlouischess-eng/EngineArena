# Engine Arena 1.8.8 — Cameo hair and shirt details

Private owner update. Magnus's hair is lighter blond, with slightly darker
roots and subtle lighter strands. Front, side, rear, daylight and evening
views are reviewed from the actual 3D model using software rendering.

Levy's green shirt carries "The ROOK!" and an original rook illustration.
Nakamura's black shirt has a small, visible pineapple on his left chest
(the viewer's right in a front view). Front, angled, rear, walking and watching
poses were reviewed. Prints stay on the front and deform with the clothing.

The source color values live in `scripts/club-cameos.json`. The Blender
generator now supports optional root and fine-strand colors. The original SVG
shirt artwork is rasterized locally and baked into existing clothing UVs.
Only Magnus, Levy and Hikaru are regenerated; the other nine people retain
their existing assets. All geometry, skinning and animation accessor payloads
are identical to the installed 1.8.7 models. The shirts use 2048-pixel cloth
atlases in place of the prior material inputs; image counts stay unchanged.
There are no added meshes, transparent decals or rendering passes.

Frame-rate options and rendering safeguards are unchanged. This is not a
graphics-crash fix; the owner's 30-versus-60 FPS comparison remains separate.
No production tournament or preference is changed, and installation/publication
is not automatic.

Existing checks passed: 17 Python release/asset/resource tests, 22 JavaScript
graphics/motion/recovery tests, and all eight translation catalogs. Compared
with the installed 1.8.7 assets, only the three requested GLBs changed.
Final native/package
verification is recorded beside the installer in its validation JSON.
