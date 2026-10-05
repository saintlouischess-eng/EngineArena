# Building Engine Arena

Build on Windows 11 x64 with Python 3.12, .NET SDK 10, ripgrep (`rg` on PATH) and Inno Setup 6.7.3. Node.js is needed for JavaScript checks. The application bundles runtimes; these development tools are only needed to build it.

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.lock.txt
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\build.ps1
```

The ordinary build runs backend tests, freezes the worker and publishes a self-contained desktop app in `release\EngineArena`. Run JavaScript checks with `node --test tests/*.cjs`. Statistical-reference tools additionally use `requirements-statistics.txt`.

## Review current development changes

Run `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\start-development.ps1` to build the desktop and CPU reader together in `build\development` and open the current source worker/UI. This uses the normal saved workspace; `-Data "D:\Engine Tests\Preview"` selects another workspace and `-BuildOnly` prepares the files without opening the app. Close an existing app using that workspace before launching. This framework-dependent build requires the installed .NET 10 desktop runtime and repository `.venv`.

Use this launcher instead of directly opening an old executable under `desktop\bin`: a desktop-only build can lack the CPU sensor reader or its dependencies. The worker uses the reader alongside the launched desktop, so it cannot mix in an older release helper. CPU readings still require the normal per-session Windows permission. This development workflow does not rebuild the installer or publish anything.

## Original appearance assets

`python scripts/generate_pieces.py` recreates all bundled SVG pieces; the three shaded collections are defined in `scripts/premium_pieces.py`. `python scripts/generate_wood.py` recreates deterministic wood SVGs and their 512×256 PNG display copies. The latter needs Pillow in the development environment only. All generated assets are checked in, so application builds and end users do not need an image library or asset download. The live GUI uses cached PNG grain to avoid repeatedly drawing many SVG paths across thousands of squares; the chess pieces stay SVG at every size.

## Single offline installer

Install the official [Inno Setup 6.7.3 compiler](https://github.com/jrsoftware/issrc/releases/tag/is-6_7_3), checking its Pyrsys signature and SHA-256 against `installer/prerequisites.json`.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\build-installer.ps1 -Compiler "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" -SkipPortableBuild
```

The script downloads missing WebView2/PawnIO installers only from their pinned official locations, checks SHA-256 and Authenticode publisher signatures, prepares an explicit source/runtime payload and compiles one EXE. Preserve the pinned binary if an evergreen URL expires; review and update the pin before accepting a new upstream binary. Original prerequisite signatures do not sign Engine Arena itself.

The payload includes corresponding application/Python source and third-party notices. It excludes development databases, personal PGNs, recordings and internal handoff notes. `package-manifest.json` records each installed payload file's hash. The separately installed compiler is a build dependency and is not needed by testers.

The exact optional PawnIO 2.2.0 source archive, including its pinned PawnPP submodule, is in `vendor/PawnIO`. LibreHardwareMonitor's pinned source archive is in `vendor/LibreHardwareMonitor`. Other dependencies retain upstream notices in the installed `ThirdParty` directories.

## Installer regression checks

The installer build also resolves the WebView2 SDK's x86 loader for the 32-bit Inno Setup process. The application continues using its x64 loader. `installer/WebView2Policy.iss` is shared by setup and the compiled `installer/WebView2Tests.iss` regression harness. Compile that harness with ISCC after preparing the installer, then run it with `/VERYSILENT /SUPPRESSMSGBOXES /LOG="test-output\webview-tests.log"`. It intentionally exits without installing anything; verify the `WEBVIEW_REGRESSION_PASS: 10` log marker. To test absent-runtime detection without changing Windows, set `WEBVIEW2_BROWSER_EXECUTABLE_FOLDER` to an empty folder for that process only and pass `/EXPECTAVAILABLE=0`. Never remove the machine's shared runtime for these tests.

## Local Version 1.1.2 acceptance

The preceding candidate was **1.1.2**, not a published release. The manager and save-feedback update is
described in `docs/V1_1_2_FIXES.md`; `validate_hover_help.cjs` exercises real browser
input and automatic manager refresh. `validate_setup_save.cjs` covers saving,
repeat clicks, edit/remove and rejection recovery. `test_setup_acknowledgement.py`
checks delayed/failed backups and shutdown durability. See
`docs/V1_1_REVIEW.md` for current results and `docs/V1_REVIEW.md` for the preceding
full review. The owner will install and test the new candidate before publication.
`validate_shared_package.py` checks the 1.0.1 data migration, simultaneous CPU/Lc0
play and forced recovery in disposable workspaces. `rc_formats_acceptance.py
--parallel` checks every tournament format with the shared scheduler.
`installer/public-docs.txt` and `installer/source-scripts.txt` define the public
documentation and reproducibility scripts for both packages. Private operational
scripts, handoff notes and test workspaces are excluded. The portable package
includes the application license, notices and corresponding dependency sources.

`scripts/rc_acceptance.py` runs the packaged desktop with Stockfish/Berserk from
`validation-engines`, optional explicitly supplied GPU-profile JSON, and an
isolated directory below `test-output`. It force-terminates only its own test
application. `rc_failure_acceptance.py` checks faulty UCI peers, original attempts,
replacement, retries, a real PGN write-sharing failure and interrupted backup
recovery. Never point these scripts at a real tournament workspace.

`rc_load_acceptance.py --node PATH` compares full legal games at 32 concurrency
with and without a headless Edge dashboard containing 32 boards and 16 graphs.
The UI sampler asserts both board and graph counts. Playwright is a validation
dependency, not part of the distributed application. Physical display latency is
not measured by this check.

`--exercise-exports` also generates reports and PGNs during live games and records
worker memory and test-workspace storage samples. `rc_formats_acceptance.py --data
test-output/NEW_FOLDER` exercises all formats through the packaged API, automatic
queue advancement, linked events, leagues and experiments. Its short games test
lifecycle, not strength or long-term reliability.

`rc_installer_acceptance.py` installs the old Beta 2 in a named test directory
(`--previous-setup PATH` selects another older candidate; `--setup PATH` selects the new installer),
creates results, upgrades to the candidate, verifies all installed payload hashes,
then uninstalls while checking data preservation. It refuses to run over any
existing registered installation. This tests the real setup on the development
host, not a clean Windows image. No script publishes to GitHub.

## Local Version 1.2.0 acceptance

See `V1_2_WORKFLOWS.md`. Run `tests/test_workflow.py`, the complete Python/JavaScript suites and `scripts/validate_workflow.cjs` against `scripts/preview_workflow.py`. All workspaces remain under test-output. Package and validate the matching 1.2.0 worker, desktop, sensors, UI and catalogs together. The installed owner workspace must remain untouched.
