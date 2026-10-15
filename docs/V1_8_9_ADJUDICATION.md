# Engine Arena 1.8.9 — Configurable adjudication windows

The Adjudication & SPRT section now exposes the three existing worker settings
that were missing from tournament setup:

- Resignation window: default 6 consecutive plies.
- Draw window: default 12 consecutive plies.
- Minimum played plies before a draw: default 80.

One ply is one move by either side. Windows consider successive played plies
from both engines, not a separate number of full moves per engine. A missing
evaluation or one that no longer satisfies the rule breaks the sequence.
For resignation, qualifying scores must favor the same side.

The minimum draw length starts at the tournament's selected opening position.
Imported opening history is excluded, even when preserved in the PGN. Zero
removes this minimum but does not bypass the draw window. A zero evaluation
threshold disables its evaluation-based rule. Draw claims, the maximum-ply
cap and referee tablebases remain separate settings.

Controls support new tournaments, persisted unsaved drafts and editing a saved
tournament before its first start. Existing saved values and completed results
are retained. Started tournaments remain locked to their recorded conditions.
Hover help and report wording clarify counting, with all eight UI languages.
Invalid windows, minimum lengths and thresholds are rejected before saving.

Validation exercises actual worker/UCI fixture games at exact boundaries for
both winners, sign disagreements, missing evaluations, draw thresholds,
minimum lengths, disabled rules, legal PGNs and imported opening history.
GUI checks cover defaults, non-default values, draft reload, edit/save,
invalid input and eight-language layout. Packaged checks include native
startup, a color-reversed pair, reports/PGNs, restart and database integrity.
Detailed results are recorded in the installer validation JSON.

This private installer includes the prior 1.8.8 blond-hair and shirt artwork
updates. It does not change graphics settings or claim to resolve the owner's
separate physical GPU/60-FPS investigation. Not installed or published automatically.
