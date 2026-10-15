# Engine Arena 1.8.1 — season admission and 3D recovery

Designed by Mark Young. Coded with OpenAI Codex.

This private installer includes the complete 1.8.0 season-admission update and
the graphics recovery fix. Install 1.8.1 directly; installing 1.8.0 first is not
necessary. See [Season admission](V1_8_SEASON_ADMISSION.md) for qualification,
challenger pools, configurable division sizes, and simulation results.

## If the graphics driver resets

Focused Game and Player Arena fall back to the 2D board. A message beside the
board explains the interruption. After three seconds, a visible board makes one
automatic attempt to recreate its 3D renderer with the saved view and room.
Hidden boards defer that attempt until visible.

If graphics remains unavailable or fails again immediately, the board stays in
2D with a **Retry 3D** button. This prevents repeated recovery loops. A minute of
successful 3D availability rearms automatic recovery for a later interruption.
Selecting 2D cancels pending recovery. Leaving Player Arena cancels its pending
recovery and releases its graphics resources.

The graphics notice disappears after a successful frame. Saving and worker
errors use their own display and are not cleared by recovering the board.
Player Arena remains playable with mouse input in the 2D fallback. A graphics
interruption does not pause chess clocks or change the game result.

These changes address application recovery after losing a graphics context.
They cannot prevent or diagnose a Windows graphics-driver reset. If the browser
cannot create any graphics context, continue in 2D and retry after the graphics
system is available.

## Validation

The recovery tests simulate context loss with WebGL's `WEBGL_lose_context`
extension in a separate software-rendered browser and disposable worker data.
They do not reset the owner's GPU or access the active event. Checks cover
automatic recovery, repeated failures, explicit retry, unavailable graphics,
camera/room preservation, graphics-warning dismissal, unrelated-error
preservation, 2D selection, Player Arena legal moves during fallback and disposal.

The season-admission simulations and packaged checks remain documented in the
1.8.0 notes. This installer combines those features with the new recovery path.
An actual Windows driver reset has not been deliberately induced for validation.

Pause and drain active testing, close Engine Arena, and run the 1.8.1 installer.
Existing events retain their saved format, results and qualification rules.
