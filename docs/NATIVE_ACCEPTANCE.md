# Desktop acceptance record — updated September 27, 2026

## Beta 3 RC 2 additions

- September 27: owner reports "Laptop test looks good" following RC 2 delivery.
  Positive laptop feedback recorded; duration and individual native workflows
  were not specified, so the detailed checklist below remains scoped as written.

The packaged RC 2 desktop passed real-engine CPU/GPU integration, forced
termination/recovery, failed-game replacement, write-failure recovery and
interrupted-backup recovery in isolated workspaces. All formats, queued runs,
events/leagues, experiments, report/PGN exports and storage cleanup were exercised
through its API. Browser checks used the packaged assets in all eight languages.
These checks do not close the physical native-picker/DPI items below. The exact
installer's upgrade/uninstall results and SHA-256 are recorded in the accompanying
`.validation.json`; earlier RC 1 installer evidence remains historical.

## Beta 3 RC 1 additions

- Owner-confirmed laptop installation and basic operation passed on September 26: "The laptop test install fine is seem to be working normally." A fresh Windows image and detailed laptop tournament/export/restart checks were not reported.
- Native launch used an isolated 84-game test workspace and displayed the correct candidate version.
- PGN preset preview was inspected in the native WebView2 window. Cancelling the Windows Save As dialog restored enabled export controls and reported cancellation. Saving to a chosen Unicode filename in a path containing spaces produced 24 legally replayable games.
- Real Lc0 GPU admission, fractional-increment and node-only feature tests ran through the packaged worker. GPU activity was serialized within `gpu0:1` while CPU games overlapped. This does not cover every GPU, network, NUMA arrangement or affinity configuration.
- Forced termination of the actual native app was tested both during active games and while a backup was partly written; committed results recovered. See `RELEASE_CANDIDATE.md` for scope and evidence.
- All eight languages passed browser report/export/storage checks at 1,100/1,550 widths with enlarged text. Physical DPI and all native dialog permutations remain separate checks below.
- Normal native Close showed its saving/backup status, then the desktop and worker exited. No precise total window-close latency was recorded.
- Real Beta 2 installation, candidate upgrade, manifest verification, restart and uninstall passed on the development host. Results/preferences/PGN and an unrelated installation-folder file were preserved. This does not close the clean-Windows checklist.
- The real WebView2 loader was exercised with a per-process empty runtime-folder override; ten installer policy cases passed in both present and simulated-absent environments. A genuinely absent shared runtime on a clean machine remains unverified.

The following earlier observations retain their original scope; they are not
all newly repeated against this candidate.

Native Windows automation is now available and was used on isolated validation instances. Checked entries below represent observed workflows. Unchecked entries are unverified, not known defects. These checks supplement the regression, real-engine, recovery and load evidence in VALIDATION.md.

## Observed Windows workflows

- [x] Preview 0.2.0 native HTML Save writes a report to the chosen folder; 16 official results and the selected 99% confidence level match the preview.
- [x] Preview 0.2.0 large-history shutdown displays copy percentage and verification progress, rejects a repeated Close while saving, and closes after the verified backup completes.
- [x] Preview 0.2.0 clean restart preserves 16 completed real-engine games, exact automatic-PGN bytes and display preferences.
- [x] Launch the complete portable folder with an explicit validation data directory.
- [x] Native executable picker discovers Berserk 14 and its 10 UCI options.
- [x] Native working-directory picker selects the engine directory and saves the profile.
- [x] Native batch-folder picker discovers Stockfish 19.
- [x] Native Save export writes valid profile JSON; Import profiles selects that file and restores the profile in a fresh library.
- [x] Cancelling the folder picker leaves the library unchanged; cancelling Save export restores an enabled export button and usable library.
- [x] Native standings CSV download parses both rows of the 52,304-game tournament.
- [x] Final portable build completes node-only and Chess960 smoke runs and recovers after killing the actual application.
- [x] Portable build loads its bundled .NET/Python DLLs with development runtime paths removed and an unrelated working directory.

## Remaining native workflow coverage

- [ ] Cross-window executable drag-and-drop. The WebView native-object bridge is implemented and compiles; the available drag tool requires both endpoints within one source window and cannot perform this physical gesture.
- [ ] Exercise each path-browser placement for an engine network, engine tablebases, referee tablebases and opening files. Shared file/folder selection is tested; every placement has not been visually exercised.
- [x] Official PGN native save, cancellation, custom paths and failure protection were checked in the September 18 PGN pass (see VALIDATION.md).
- [ ] Exercise remaining native export placements: experiment JSON, graph SVG/CSV, opening CSV, pool CSV/JSON and standings JSON. Browser/API export checks exist; the full native dialog/download permutation is not recorded as passed.
- [ ] Verify keyboard traversal and picker cancellation across every setup dialog at the intended display scaling.

## Clean Windows installation

- [ ] Extract the ZIP to a separate Windows installation without development Python/.NET and launch it. The isolated search-path test on this development host does not replace this check; Windows Sandbox is unavailable here.
- [ ] Verify clear startup behavior when Microsoft Edge WebView2 Runtime is absent.
- [ ] On that installation, discover two engines, complete a paired node-only tournament, export PGNs, close/relaunch and verify retained results.

## Physical display and additional hardware scope

- [ ] Exercise the physical ultrawide display at normal scaling and across monitors with different DPI.
- [ ] Measure physical input-to-display latency. Existing browser frame/Event Timing measurements are not that measurement.
- [ ] For GPU engines or multiple NUMA nodes, validate actual engine memory/network usage, GPU admission and CPU-affinity behavior on the intended hardware.

Record the environment, exact workflow and observed outcome when closing an item. Do not mark all acceptance passed merely because the portable candidate launches or the automated suite passes.
