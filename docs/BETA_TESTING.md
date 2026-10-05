# Engine Arena 0.2.0 Beta 3 RC 2

## Install on your laptop

This RC 2 installer includes the new queue, tournament formats and studio design.
See [what changed](BETA3_RELEASE_NOTES.md) and the
[current validation record](RELEASE_CANDIDATE.md).

1. Download **EngineArenaSetup-0.2.0-beta.3-rc.2-win-x64.exe** from the local release folder. This candidate has not been published.
2. Run the installer on Windows 11, 64-bit Intel/AMD. Install for your Windows account; Python, .NET and the full offline WebView2 installer are included.
3. Keep the default installation folder unless you need another location. Choose a desktop shortcut if wanted.
4. Launch Engine Arena and add your own UCI engines. Engine binaries, networks, books and tablebases are not included.
5. Start with a small paired match. Check live results, the focused board, reports and PGN export. Close and reopen the app to check retained results before starting a long tournament.

The Engine Arena installer is unsigned. The bundled Microsoft and PawnIO installers retain their verified publisher signatures. Use the locally supplied candidate until it is published on the official repository. Do not disable Windows security protections.

Beta 2 fixes the Beta 1 error `-2147219416` when the optional WebView2 setup box was checked. Microsoft uses this code for an already-installed runtime. Setup now verifies availability and continues when that runtime can be detected. Leave **Run Microsoft WebView2 setup again** unchecked for ordinary installation. If Beta 1 is already working, you can continue testing it; an immediate reinstall is not required.

## Optional CPU sensors

The installer includes the official signed PawnIO 2.2.0 setup. Its final-page checkbox is optional and off by default. You can also open it later from **Hardware display → CPU sensor setup → Open CPU driver setup**. Choose the signed edition and approve Windows permission yourself. Restart Windows if the driver asks for it.

Afterward, use **Enable CPU readings for this session**, select CPU temperature and/or Fastest CPU core, and save the hardware display. The separate reader needs permission each session. Games work without the driver. Sensor availability varies by laptop and processor; missing readings show Unavailable.

## Updates and removal

Close every Engine Arena window before installing another version. Setup waits for the app to close; it does not force-stop tournaments. Install the next release over the existing installation.

The program is normally installed in `%LOCALAPPDATA%\Programs\Engine Arena`. Tournament data is normally in `%LOCALAPPDATA%\EngineArena\Data`. Updates and uninstall preserve databases, PGNs, engine profiles and settings. You can choose a separate workspace with `EngineArena.exe --data "D:\Arena tests"`.

Uninstall through Windows Installed apps or the Engine Arena Start menu shortcut. Shared WebView2 and PawnIO installations are retained. Never put your only tournament-data copy inside the program folder.

## Feedback

Use [GitHub Issues](https://github.com/saintlouischess-eng/EngineArena/issues). Include version, Windows version, CPU/RAM, engine names/versions, time control, opening policy, concurrency, exact reproduction steps, expected behavior and observed behavior. A screenshot or a small PGN helps. Review attachments for private paths or settings before posting. The app sends no feedback automatically.

This is a beta for functional testing and suggestions. The completed 76,500-game run is historical endurance evidence. The combined candidate, clean-machine setup and additional hardware still need their own acceptance records. See [validation scope](BETA_VALIDATION.md) and [statistical methods](STATISTICS.md).
