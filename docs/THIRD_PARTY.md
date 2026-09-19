# Component notices

Engine Arena application source is GPL-3.0-or-later; see LICENSE and NOTICE. Third-party packages retain the terms listed in their supplied licenses. No engine binaries, private game histories or opening books are redistributed.

- python-chess 1.11.2, by Niklas Fiekas and contributors: GPL-3.0-or-later. The portable distribution includes the installed Python source and license in `ThirdParty/python-chess`.
- The Classic vector chess pieces and recolored Walnut variant are by Colin M. L. Burnett, as distributed with python-chess. Its [SVG documentation](https://python-chess.readthedocs.io/en/latest/svg.html) identifies the pieces as triple licensed under GFDL, BSD and GPL. This distribution uses the GPL option and retains the source SVG definitions in `chess/svg.py`.
- Studio, Outline, Geometric and Modern piece paths are generated from the original definitions in `scripts/generate_pieces.py`.
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
