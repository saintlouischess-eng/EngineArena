# Focused clocks and live concurrency

Local development update, September 26, 2026. The public installer is unchanged.

## Focused game

Choose **Board & clocks** in the Focused game header. The settings include:

- Both clocks above or below the board, at its left or right, or one above and one below.
- Side-by-side or vertically stacked clocks above/below the board. Side placements stack the clocks.
- White first, Black first, or order following board orientation. For orientation-following order, the far-side player appears first; flipping changes the order.
- Minimum clock-box height, clock number size and side-clock width. Long times shrink to fit narrow clocks.
- Automatic board fitting, or a maximum board size in pixels. The maximum never forces the board beyond the available space.
- Optional engine names and clock details. White/Black labels remain visible.
- Compact, Large clocks, Board between clocks and Reset layout presets, with a live preview.

Save applies these presentation settings to the current workspace. They live under the focused panel's preferences, so existing named-layout save/restore also includes them. Panel docking, floating, resizing and evaluation-bar settings continue to work. Narrow panels put side clocks above the board; very small spaces scroll internally instead of overlapping content. Clock projection, game timing, move saving and engine settings are unchanged.

## Now running

Set **Concurrent games** and press **Apply** (or Enter) while running or paused.

- Increasing permits additional starts on the scheduler's next pass, subject to pending pairings and the CPU, memory and shared GPU budgets.
- Decreasing does not stop, requeue or restart active attempts. No new game starts while the active count is at or above the new limit. The status explains when existing games are finishing toward a lower target.
- This controls simultaneous games, not an engine's UCI Threads option. A GPU group configured for one process stays limited to one process. Queued tournaments and Swiss/KO round dependencies retain their existing scheduling rules.
- Paused or draining tournaments retain their state. The new limit applies when resumed. Completed tournaments cannot change their limit.
- The limit and an audit event commit together in SQLite. An unchanged value produces no duplicate audit event. Scheduler dispatch and setting changes share the lifecycle lock, so an acknowledged change cannot be followed by a start using the old limit.
- ETA sampling resets on an actual limit change. HTML/TXT tournament reports include UTC change time, previous/new limits and active count. Resource summaries label the current limit; per-session technical evidence labels the initial session limit. Performance samples may span different loads.

## Verification

The focused regression run passed 26 tests, including a real fault-engine RR that changes 1 → 4 → 1 → 8 while CPU budget remains four and GPU group gpu0 remains one. The completed fixture retained all 24 official results and 12 pairs, with no concurrency-induced interrupted attempts. A separate subprocess exits abruptly after committing changes; recovery retains the final limit and exactly two audit entries. API tests cover invalid inputs, paused behavior and completed-tournament rejection.

The complete backend suite passed **348 tests**; all **42 JavaScript checks** passed. Existing aiohttp AppKey warnings remain.

Automated browser checks cover 30 placement/arrangement/window-width combinations, non-overlapping square boards, saved preferences after reload, board flips, evaluation bars, board-size limits, visible color labels with names hidden, and applying a live limit without overwriting an input being edited. All eight languages were checked at 24 px UI text. Evidence: `test-output/live-controls-ui.json`, `focus-clock-layout.png`, `focus-clock-options.png`, `live-controls-focused.xml`, and `live-controls-full.xml`. Fixture and browser scripts are `scripts/preview_live_controls.py` and `scripts/validate_live_controls.cjs`.

No production tournament was opened or modified during development or testing. The development desktop and sensor companion were rebuilt together; the existing NuGet vulnerability-feed warning remains, with no dependency changes.
