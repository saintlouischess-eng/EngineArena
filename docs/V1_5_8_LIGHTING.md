# Engine Arena 1.5.8 — softer 3D lighting

The 3D board uses a satin wood finish with reduced reflections, so a pale glare
no longer spreads across the squares and frame as the viewing angle changes.
The lighting balances a softer reflection environment with a restrained main
light and fill. The pieces keep broad highlights that describe their shapes
without the previous sharp white streaks. The dark wood is slightly lifted to
keep carved contours readable, and the frame retains its walnut color.

The existing sculptures, wood color and normal textures, crown markings,
knight-facing choices, board coordinates and camera controls are preserved.
The knight stamp retains its original head-relative orientation; only the rook
stamp reads upright from its owner's side. This visual adjustment is automatic
and requires no new setting. The 1.5.7 full move-history scrolling is included.

The lighting uses the existing renderer and shadow-map budget. Static boards
continue to draw only when something changes. No animation loop, extra engine
processes, game-rule changes, or tournament data migrations are introduced.

Validation includes before/after renders at several camera angles in both
themes, a packaged-app visual check, camera and replay controls, crown marks,
context-loss fallback, and renderer disposal/idle checks. These are isolated
display checks, not a new tournament endurance run or clean-machine install.

Private update. Designed by Mark Young; programming by OpenAI Codex. Pause and
drain, close normally, install 1.5.8, reopen and resume. Not published to GitHub.
