# Component notices

Engine Arena application source is GPL-3.0-or-later; see LICENSE and NOTICE. Third-party packages retain the terms listed in their supplied licenses. No engine binaries, private game histories or opening books are redistributed.

- python-chess 1.11.2, by Niklas Fiekas and contributors: GPL-3.0-or-later. The portable distribution includes the installed Python source and license in `ThirdParty/python-chess`.
- The Classic vector chess pieces and recolored Walnut variant are by Colin M. L. Burnett, as distributed with python-chess. Its [SVG documentation](https://python-chess.readthedocs.io/en/latest/svg.html) identifies the pieces as triple licensed under GFDL, BSD and GPL. This distribution uses the GPL option and retains the source SVG definitions in `chess/svg.py`.
- Studio, Outline, Geometric and Modern piece paths are original definitions in `scripts/generate_pieces.py`. Tournament, Nordic, Art Deco, Rounded, Monoline and Pixel are original definitions in `scripts/piece_designs.py`. Regal, Heirloom and Porcelain are original shaded vector designs in `scripts/premium_pieces.py`. The six static wood textures are original procedural vector artwork in `scripts/generate_wood.py`. This Engine Arena artwork is included under GPL-3.0-or-later, requires no external download or separate purchase, and contains no third-party stock images or fonts.
- Classic Sculpted, Aurora and Citadel are original static vector drawings in `scripts/sculpted_pieces.py`, also GPL-3.0-or-later. Classic Sculpted is a newly drawn Staunton interpretation; it is separate from the bundled Burnett Classic set. All shading uses vector paths and gradients, with no embedded raster artwork or external resources. Together with Regal, Heirloom and Porcelain these form the six detailed SVG collections.
- Classic Refined, Classic Bold and Classic Heritage are shaded redraws of the Burnett Classic family. Their silhouettes are defined in `scripts/classic_variations.py`, with added vector surface modelling, bevels and engraving in `scripts/raised_classic_variations.py`. The Burnett design reference is credited in each SVG. These variants are GPL-3.0-or-later and contain no raster artwork, filters or external resources.
- .NET and the WPF runtime: Microsoft and .NET contributors, MIT. Runtime distribution notices accompany the self-contained publish output.
- Microsoft Edge WebView2 SDK: Microsoft. The beta setup includes the unmodified, signed offline Evergreen Runtime installer under Microsoft's distribution terms. It installs separately only when needed or when repair is selected, and remains installed after Engine Arena is removed.
- Python runtime, aiohttp, psutil and their transitive dependencies retain their upstream licenses. Pinned versions are recorded in `requirements.lock.txt`; installed package metadata and runtime notices are retained with the worker bundle where supplied.
- Python 3.12 runtime license text is retained under `ThirdParty/Python`. PyInstaller's bootloader license and distribution exception are under `ThirdParty/PythonPackages/pyinstaller-6.19.0.dist-info/licenses`.
- NetworkX 3.6.1, NetworkX developers, BSD-3-Clause, supplies minimum-weight maximum-cardinality matching for engine Swiss pairings. Its installed license metadata is included in the worker bundle.
- Validation Stockfish and Berserk executables are not redistributed in this application package.

- LibreHardwareMonitorLib 0.9.6: MPL-2.0 and retained third-party notices. Its pinned source archive, license and notices are under `ThirdParty/LibreHardwareMonitor`.
- Optional PawnIO 2.2.0: GPL-2.0-or-later with the upstream interface exception. The signed installer is unmodified and optional. Its exact tagged driver source and pinned PawnPP submodule, license and README are under `ThirdParty/PawnIO`.
- Inno Setup 6.7.3 supplies setup/uninstall infrastructure. Its license is retained under `ThirdParty/InnoSetup`. The compiler is only a build tool.

`package-manifest.json` records installed payload files and hashes. `installer/prerequisites.json` in the source snapshot pins prerequisite binaries and publishers. License and metadata files for Python packages are retained under `ThirdParty/PythonPackages`; runtime notices remain with their corresponding components.

- Three.js 0.186.1, Three.js authors: MIT. Eight official modules are bundled for offline 3D rendering, with local import paths and a renderer-owned DFG lighting lookup texture disposal correction. The lifetime patch is reproduced by `scripts/three_lut_patch.py`. The archive is SHA-512 pinned by `scripts/vendor_three.py`; `ThirdParty/Three` contains the upstream license and provenance. Original 1849-inspired GLB models and baked wood textures are authored in Blender by `scripts/build_staunton1849.py` and included under GPL-3.0-or-later. Historical photographs were visual references only; none is embedded or redistributed. Blender is an authoring tool, not a runtime requirement.

## MakeHuman graphical data (1.7.2)

The standalone live club uses twelve separately morphed, clothed, skinned visitors
derived from CC0 MakeHuman graphical data: base mesh, targets, skeleton/weights,
skin maps, outfits, shoes, eyes and hairstyles. The MakeHuman application code
is not incorporated or executed. `vendor/MakeHuman/club-cast/provenance.json`
records pinned source URLs and SHA-256 hashes; `derived.json` identifies the
twelve outputs. `scripts/build_club_cast.py` implements fitting and pose creation.
Four seated players and at most two roaming visitors are visible. Eight visitor identities rotate without duplicates. The six cameo face maps are original generated artwork projected and baked by the project, under GPL-3.0-or-later; their generation prompts and photo-reference links are in `prototypes/live-club/art/README.md`. Reference photographs are not redistributed. Cameos are artistic interpretations, with no claimed endorsement. The underlying CC0 assets retain their original license. MIT Three 0.186.1 compositor and light
addons are pinned in `vendor/Three/club-addons.json`; only imports are rewritten.

### Legacy background head (1.7.1, no longer used by the renderer)

The optional live rooms include an adapted CC0 MakeHuman base head, a skin map,
and short02 hair. Copyright holders at the CC0 release: Data Collection AB,
Joel Palmius and Jonas Hauquier. Asset licensing is explicitly recorded in the
source OBJ/MHCLO headers and the bundled CC0 text; this package does not embed
or run the MakeHuman application.

Sources: [MakeHuman asset licensing](https://github.com/makehumancommunity/makehuman/blob/master/LICENSE.md)
and [CC0 asset mirror](https://github.com/s20220526/makehuman-assets/tree/8cf9645b975a98eea056b140df11a1d278da0d10).
`ThirdParty/MakeHuman/provenance.json` records each source URL and SHA-256.
`scripts/build_room_characters.py` crops the base mesh to its head, fits the hair
through its MHCLO anchors, adds eye details and a cropped scalp, reduces the
maps to 1024px, and exports `ui/room-head.glb`. The original inputs and Blender
build script are included in Source. The CC0 assets retain CC0 status.

All live-room data is bundled for offline use; the application makes no asset
requests to these websites. Background people are lightweight scene figures,
not photographic actors or simulations of actual tournament participants.
