# Engine Arena Beta 3 RC 2 — local testing candidate

Version: **0.2.0-beta.3-rc.2**, September 27, 2026. This candidate is supplied
locally for testing. It has not been published to GitHub.

## Changes since the earlier laptop candidate

- Edit a tournament's setup before it has started. Queue prepared tournaments
  for automatic sequential execution, immediately or at a scheduled time.
- Custom matchups, linked group/Swiss-to-final events, and league divisions with
  promotion and relegation. Event stages preserve their own results and ratings.
- Clearer two-engine SPRT controls, candidate identification and stopping status;
  completed results are admitted in scheduled order. Corrections preserve the
  original evidence and identify invalidated statistical conclusions.
- More reliable suites and benchmarks, paged result histories, clearer timing,
  failure and accuracy reporting, and verified effective engine thread counts.
- Refined workspace design, original knight logo, clearer panels, responsive
  graph labels and Appearance shortcuts. The sidebar follows the chosen theme;
  the Running button stays steady during refreshes.
- Fixes to translated rating exports and large-text dialog layouts.

Beta 3 also includes the earlier improvements to knockout matches, independent
engine move books, live time-forfeit counts, adjustable concurrency, focused
clocks, PGN presets, reports, large-history startup and managed-storage cleanup.
Shared tournament opening positions remain available alongside profile books.

## Installing and testing

Close Engine Arena before running **EngineArenaSetup-0.2.0-beta.3-rc.2-win-x64.exe**.
Use the existing installation folder to upgrade. Tournament data is stored
separately; updates preserve it. Keep the optional WebView2 repair checkbox off
for an ordinary upgrade. The optional sensor driver does not need reinstalling
when readings already work.

The single installer includes the application and required runtimes. Engines,
networks, books and tablebases are supplied by the user. Setup is unsigned;
bundled prerequisite installers retain their original publisher signatures.

For the laptop check, confirm the RC 2 version, reopen existing tournaments,
run a small queued comparison, export a report and PGN to a chosen folder,
close/reopen, and check the retained results. Then run a longer tournament while
watching memory, disk use, clocks and interface responsiveness. Check light/dark
themes, larger fonts and resizing at the laptop's normal display scaling.

## Validation scope and remaining work

See [the candidate validation record](RELEASE_CANDIDATE.md) for actual results.
The completed 76,500-game tournament belongs to an earlier build. It does not
establish multi-day reliability of this exact candidate. Clean Windows setup,
extended second-machine testing, physical mixed-DPI behavior and native-speaker
translation review remain open. This is a beta candidate, not a stable release.

When reporting an issue, include the RC 2 version, engine/version, format, time
control, opening settings, concurrency, steps and expected/actual behavior.
Review reports and PGNs for local paths before sharing them.
