# Building Engine Arena

Build on Windows 11 x64 with Python 3.12, .NET SDK 10, ripgrep (`rg` on PATH) and Inno Setup 6.7.3. Node.js is needed for JavaScript checks. The application bundles runtimes; these development tools are only needed to build it.

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.lock.txt
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\build.ps1
```

The ordinary build runs backend tests, freezes the worker and publishes a self-contained desktop app in `release\EngineArena`. Run JavaScript checks with `node --test tests/*.cjs`. Statistical-reference tools additionally use `requirements-statistics.txt`.

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
