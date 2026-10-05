# Engine Arena 1.1.1 — hover-help correction

Local update prepared October 3, 2026. Designed by Mark Young.

The Tournament manager restores the focused control when live updates replace
table rows. In 1.1.0, that automatic focus event could display help even when the
mouse was stationary elsewhere. Replacing controls under the pointer could also
trigger a new hover boundary event without any deliberate mouse movement.

The shared help system now distinguishes actual pointer movement, keyboard
navigation and automatic focus restoration. Live refreshes retain focus without
opening help. Genuine hover and Tab navigation still display it. Help is cancelled
when the target disappears, moves away, loses focus or the window becomes inactive.
Clicking, opening a dialog, scrolling and Escape continue to dismiss help.

The original failure was reproduced in an isolated manager fixture. Fourteen
targeted browser checks cover stationary-pointer refresh, polling, programmatic
focus, keyboard help, real hover, leaving before the delay, opening dialogs,
accessible descriptions, replaced/moved controls, boundary events and window blur.
The final packaged validation is recorded alongside the installer. Existing 1.1.0
functional validation is documented separately in [the review](V1_1_REVIEW.md).

This update changes interface help behavior and version labels. Tournament
scheduling, engine communication, clocks, results and database formats are unchanged.
No production workspace is used for development checks. The owner installs the
update when convenient; nothing is published by this task.

Pause and drain running tournaments before closing Engine Arena. Run
`EngineArenaSetup-1.1.1-win-x64.exe` into the existing installation folder. Leave
optional WebView2 repair unchecked if it is already working. Reopen and resume
the tournaments when ready.
