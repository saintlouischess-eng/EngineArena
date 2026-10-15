# Engine Arena 1.5.6 — rook-only crown correction

Private correction to 1.5.5. Designed by Mark Young. Programming by OpenAI Codex.

Only the **rook** crown stamp reads upright from its owner's side. The knight's
stamp is restored to its previously accepted orientation, size and position on
the forehead. It turns naturally with the knight; it is not independently rotated
to face the player.

All six knight-facing options remain available in **Focused game → 2D / 3D →
Knight direction**, with **Toward the king** as the default. The 1.5.4 graphics
cleanup correction remains included. No chess rules, clock handling, results,
ratings or database formats change in this correction.

Pause and drain, close Engine Arena normally, install 1.5.6, then reopen and
resume. This supersedes the 1.5.5 installer and has not been published to GitHub.

Validation: the packaged app passed checks of the original knight stamp UVs and
surface footprint, upright rook stamps, both colors, all six knight directions,
saved preferences, replay, idle rendering and eight language dialogs. Rendered
starting positions and flipped views were inspected. Nine focused JavaScript
cases and 14 release/resource cases passed. This correction did not repeat engine
matches, crash recovery or endurance testing, and did not touch the owner's data.
