# Engine Arena 1.9.4 — private test update

Designed by Mark Young. Coding and implementation by OpenAI Codex.

## Add engines to a completed round robin

Open Tournament workspace, select a completed standalone round robin and choose
**Add engines…**. Select new profiles, using search and Previous/Next as needed.
Selection survives search and paging. Existing participant profiles are disabled.
**Preview added games** shows retained results, additional games, total games,
participant count and the recorded cycle/pair policy. **Save extension paused**
commits the extension without starting it. Use Start/resume when ready.

Every new engine meets every incumbent and every other new entrant for the same
number of cycles. Paired games retain color-reversed openings; unpaired repeated
matchups alternate colors. Old games, attempts, opening records, participant
snapshots, ratings and anchors are not rebuilt or duplicated. Each later
extension adds only its own missing matchups. New profiles retain their saved
thread, hash and per-engine clock settings; review the library before selecting.
Changed existing executable/network fingerprints block continuation until the
recorded files are restored. A new version should be a separate new profile.

Eight engines with one paired cycle have 56 games. Adding a ninth engine adds
16 games, for 72 total. Schedules remain implicit and materialize only bounded
windows, including for thousands of new participants. Saving is transactional;
an abrupt exit keeps either the old tournament or the committed extension.
Existing queue entries are held so saving cannot silently launch the extension.

Opening presets remain explicit:

- Pair/legacy: continue the saved sequence after earlier pairs/games.
- Round: new extension rounds continue after the recorded rounds.
- Shared cycle: new opponents use the same saved cycle suite as incumbents.
- Fixed position: keep the intentionally repeated position.
- Seeded random selection and exhausted books can repeat, as before.

This feature is for completed independent round robins. Finish all outstanding
replays first. Event stages, Swiss, knockout, gauntlets and other formats cannot
be extended in this update. Event entrants belong in the next season workflow.
While extension games are in progress, engines can have unequal sample sizes;
live Elo remains relative to each engine's sampled opposition.

## Draw-rule progress

Focused Game displays half-moves since the last pawn move or capture, plus the
remaining half-moves. Two plies equal one full move. With draw claims enabled,
the threshold is 100 plies (50 moves). With claims disabled, it displays the
automatic 150-ply (75-move) limit instead. Pawn moves/captures reset it; checkmate
and other endings take precedence. This is not a wall-clock estimate.

The counter reads the actual displayed FEN, including imported starting positions
and recorded move review, in either board mode. It does not poll engines or change
adjudication. It is enabled by default; hide it using **Board & clocks → Show
draw-rule counter**. The choice is saved with the workspace display preferences.

## Included corrections

- Custom season overview stage panels no longer duplicate on unchanged polling;
  expanded details and keyboard focus survive refreshes.
- Includes the private 1.9.3 CPU rating-pair correction: compatible CPU pairs
  spanning only Windows maintenance/display-driver updates can remain in the fit.
  Original conditions are retained; GPU pairs and exact filters stay strict.

## Validation and installation

Automated coverage includes all opening presets and schedule orders, paired and
unpaired repeated extensions, color balance, unchanged original attempts and
rating records, rollback/stale-preview guards, 2,002 participants with an implicit
4,006,002-game schedule, resource admission, forced process termination/recovery,
PGN legal replay, GUI paging/search/selection, all eight languages, and both draw
thresholds in the worker. Packaged acceptance and checksums accompany the installer.
Tests use disposable data and controlled UCI engines. They do not claim another
full long-duration real-engine endurance run or physical GPU validation.

Pause and drain active games, close Engine Arena, install, then reopen and resume.
This cumulative update does not require installing 1.9.3 first. No games need to
be replayed for the rating correction. It is a private candidate for owner review;
the public GitHub release has not been changed.
