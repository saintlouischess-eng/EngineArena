# Engine Arena 1.9.0 — custom competition designer

Private testing update, designed by Mark Young and coded with OpenAI Codex.

## Best version in Ratings Center

Choose a single time category, then **Version display → Best version per engine
family**. Each family retains separate CPU thread counts or verified GPU
model/count/backend and CPU-support-thread configurations. Fixed node/depth/time
limits and clock handicaps also stay separate. Unverified configurations are
not collapsed into known hardware. This display choice is remembered.

The highest current point estimate supplies each row; it is not proof that this
version is stronger. Tied estimates prefer more samples, then more games, then
name and ID for stable ordering. If none has an estimate, one representative
remains unranked. All versions and games remain in the fitted rating model;
Elo, CI, LOS, evidence and anchors are unchanged. Ranks are recalculated within
the displayed selection before search, sorting and pagination. Text, CSV and
JSON exports follow the selected view. All-categories comparison uses all
versions because different time categories have different winners and scales.

Families are inferred conservatively by removing a separated version/build
suffix while retaining multi-word engine names. Click an engine, open **Engine
family**, and enter a correction when needed. Use the same family name for
related versions; leave blank to restore automatic naming. Family names affect
display only and do not imply shared source code or merge results. Anchor and
predecessor pickers always show all versions, including hidden entries.

## Create a competition

Save a normal tournament setup with the engines, opening book and other game
conditions you want. In **Events & leagues**, choose **Custom competition…**
and select that setup. Its participants and conditions are copied into the
competition; later changes or deletion of that source do not change the event.

Choose a quick structure or add, remove and move stages. Each stage supports
round robin, Swiss (club pairing) or knockout. A stage may have several groups
playing concurrently under one shared CPU, memory, game and GPU budget. There
is no fixed entrant limit; groups need at least two engines. Preview uses
mathematical counts, and child tournaments schedule games incrementally.

For each stage, set:

- Group count and seeding: spread incoming seeds, consecutive seeds or seeded
  shuffle. The initial incoming order is the source tournament's entrant order.
- Opening pairs per matchup, plus rounds for Swiss.
- A count or percentage advancing from each group; percentages round up.
  Knockout groups advance their winner. The final stage must be one group
  crowning one winner.
- Conditions from the source or another saved tournament: book, engine-book
  policy, clock tolerance, watchdogs and adjudication. Explicit clock and
  adjudication overrides let stages use different conditions.
- Played placement playoffs or existing standings tiebreaks. The latter use
  the normal deterministic standings ordering and may ultimately use initial
  seeding. Choose played playoffs when a tied boundary should be played out.
- Pairs and optional time control for additional tiebreak games. Knockout
  matches always continue with extra pairs until a winner.

When several groups feed the next stage, qualifiers are interleaved by
finishing place. Raw points from different groups are not compared. A knockout
stage uses bracket finishing order, not accumulated points, to pick its winner.

The preview shows entrants, group sizes, qualifiers, clocks, book inventory and
the regular scheduled game count. Tiebreak games are additional and potentially
unbounded. Preview again after changes, then **Save event**. The dialog closes
to the competition overview. **Approve plan**, then **Run event** to begin.
Review can be required between stages, between seasons, or only initially.

## Openings and adjudication

Custom stages use reversed-color pairs and a seeded shuffled opening sequence.
Parallel groups share that sequence for comparable conditions. Later stages
and seasons continue beyond the longest group, including its tiebreak games.
Different books have independent cursors. Repetition is possible when an
inventory is exhausted; the preview warns when the regular plan already needs
more positions than available. Tiebreaks may require additional positions.

The new controls from 1.8.9 apply in every stage: resignation threshold and
window, draw threshold and window, minimum played plies before a draw, and
maximum plies. They use the same tournament worker. Windows count successive
played plies from both engines; minimum draw length excludes imported opening
history. Zero centipawns disables its rule. A pure node control sends only
`go nodes N`; readiness and hang watchdogs remain separate.

An explicit stage time control applies to all entrants. Without an override,
source-profile handicap clocks remain effective and the preview labels them
as per-engine controls. Selecting a different saved setup for a stage applies
that setup's common clock while retaining this competition's engine roster.

## Review, editing and reusable templates

The overview shows the competition path, current stage, next action, progress,
champions, careers and stage records. Each child tournament retains its normal
standings, rating estimates, reports and PGN exports. Elo from different stage
conditions is not averaged into a competition Elo.

**Pause and drain** before **Edit future stages**. Created and completed stages
in the current season are locked. Remaining stages can change, and those
definitions apply to future seasons. Each completed decision retains its
original conditions and standings. The competition seed and scheduling order
stay locked. Saving changes requires another approval before continuing.

**Save competition template…** saves structure and condition snapshots without
binding the template to that event's roster. Start a new custom competition
from another source tournament to reuse the template with different engines.
Deleting a template does not change existing events. The deletion confirmation
explains that an open draft returns to source conditions.

Custom competitions repeat the full original roster through their chosen
stage sequence each season. Use the existing configurable league/season modes
for promotion/relegation, admission challenges and between-season roster
upgrades. This designer adds a linear stage sequence, not arbitrary branching
brackets or a replacement for those league modes. Configure the number of
seasons up front; a completed custom competition can be copied with Start fresh.

## Recovery and corrected results

Stage creation and advancement are transactional. Recovery retains committed
games and decisions, archives unfinished attempts and waits for an explicit
resume. Official replacement requires confirmation of affected dependencies;
later stages and dependent placement playoffs are archived before advancement
is recalculated. Every original attempt remains in history. Placement playoff
points do not inflate the original stage's standings.

Existing event deletion, rating-retention and disk reclamation workflows apply.
Templates are independent saved designs and must be deleted separately.

## Validation scope

Tests cover mixed formats, successive seasons, exact regular counts, seeding,
percentage advancement, repeated placement ties, official replacement and
dependencies, future-stage edits, independent templates, opening cursors,
transaction rollback and a 1,000-entrant incrementally scheduled competition.
The existing event, season, admission and adjudication suites are also run.

Native acceptance uses a new disposable workspace and controlled UCI engines.
It checks different stage clocks and draw windows in actual games, forced app
termination and recovery, completed opening pairs, four PGN presets, reports,
career totals and settings after restart. Browser checks use software rendering
for the designer, eight languages, two widths/themes and completed reports.
Evidence is saved under `test-output/v190-*`; final installer hash and payload
verification live beside the installer as `.validation.json`.

No production tournament is changed and this candidate is not installed or
published automatically. Graphics behavior and FPS choices are unchanged.
The owner's physical GPU endurance test at 60 FPS remains separate.
