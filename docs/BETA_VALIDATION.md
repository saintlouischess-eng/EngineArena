# Beta validation scope

Beta 2 fixes the optional WebView2 setup path: Microsoft's `-2147219416` (`0x80040828`, already installed) is accepted only after the SDK loader detects an available runtime. Setup uses the same detection API as the desktop app; all four registry views are logged for diagnostics. Ten compiled installer-policy cases passed, including the reported repair failure, missing/broken runtime, launch failure, unknown errors and restart-required. Real SDK probes passed with the installed runtime and with an empty per-process runtime override. These tests do not claim that an arbitrary damaged Windows installation has been repaired.

The pre-installer 0.2.0 application passed 194 backend tests and 21 JavaScript checks. Independent reference calculations checked 1,408 score/Elo/confidence cases at eleven confidence levels, 144 SPRT cases and 180 pool-rating estimates. These verify the implemented models, not universal statistical calibration. Normal intervals can under-cover small samples; independence assumptions and sequential-stopping limitations remain.

The portable application completed 16 full Stockfish/Berserk node-only games at four concurrent games, eight opening pairs and eight benchmark cases. All four PGN formats parsed legally and retained unique attempt IDs. Restart retained results, exact automatic-PGN bytes and preferences.

A separate 52,306-result / 5.52 GB history measured 16.79 seconds for a fresh verified backup and 0.15 ms for reusing an unchanged verified copy. These were local warm-cache measurements. Changed data still requires a full copy. Native shutdown progress and repeated-close protection were observed.

The Beta 1 single-EXE installer was installed into a separate development-host test folder. The installed app completed four additional full Stockfish/Berserk games, two opening pairs at two concurrent games, in 18.31 seconds. All 428 recorded searches used exactly `go nodes 150000`; four PGN formats parsed legally with unique attempt IDs. An in-place installation and restart retained four official results, exact automatic-PGN bytes and the saved 99% confidence preference.

Setup and uninstall both refused to proceed while the app was open. Uninstall removed the program while preserving the test database (SQLite integrity check passed), exact PGN bytes and an unrelated file in the installation folder. A per-process empty WebView2 runtime override produced the intended repair message before a worker or data folder was created. The shared WebView2 runtime and CPU driver were not removed or reinstalled during these checks.

Development-host installation is not a clean-Windows certification. Actual WebView2 installation on a Windows machine without the runtime, laptop sensor compatibility, long unattended testing, additional CPUs/GPUs, mixed-DPI displays and all native dialog permutations remain open.
