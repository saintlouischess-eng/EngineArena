# Custom matchups, multi-stage events and league seasons

These features are in the local development build. The previously delivered
laptop installer and GitHub release have not been replaced.

## Custom matchups

Select engines in Engine library, create a tournament, and choose **Custom
matchups**. Expand **Participant numbers and names** to identify each engine.
Add matchups with the three input boxes or paste lines such as:

```text
1 2 100
1 3 50
2 4 25
```

The columns mean first participant, second participant, and count. With color
reversal enabled, counts are opening pairs: this example schedules 350 games.
Otherwise counts are individual games, and colors alternate within each
matchup. Odd counts have one extra game with the first engine as White.
Each opponent combination appears once; reversed duplicates and self-pairings
are rejected. Selected engines without a matchup retain zero games.

Choose a fresh opening for each pair/game, a shared opening suite by repetition,
or an intentionally fixed position. Custom matchups have no shared rounds.
The normal total-game preview, opening capacity, resource budgets, retries,
statistics, recovery, queue, setup editing and PGN export all apply.

Repetitions are stored as counts and decoded with cumulative ranges, rather
than expanding the complete game list. CPU games can run ahead of a blocked GPU
matchup. The sampled opponents and game counts may differ, so raw game points
and score-based Elo do not imply equal opposition; use head-to-head results and
the connected pool-rating model with its documented assumptions.

## Multi-stage events

1. Save a tournament containing the desired engine profiles, openings, clocks,
   resources, retry rules and standings tiebreaks. It supplies the conditions;
   it does not need to run.
2. Open **Events & leagues → Create event** and select that source tournament.
3. Choose **Groups → final stage**. Assign all participants exactly once, with
   at least two engines in every group. Automatic distribution uses participant
   order; edit the numbered lines to control membership.
4. Choose round robin or club Swiss for the group stage, qualifiers per group,
   and round robin or single-elimination KO for the final stage. One group can
   provide Swiss → KO or round robin → superfinal.
5. Set the matchup lengths, optionally override all finalists' clocks, then
   **Preview schedule → Save event → Run event**.

Qualification uses game points, the source's configured standings tiebreaks,
then the recorded initial seed as a deterministic fallback. Tied qualifying
places therefore resolve automatically by the displayed rule. Qualification
does not currently create extra playoff matches. KO match ties use continuous
additional games until a winner; inherited KO tiebreak control sequences apply.
Finalists are initially listed by qualifying place, then group; the source's
seeding policy applies within each child tournament.

The final clock override supersedes individual engine clock overrides only in
the final stage. Without it, all original independent controls are retained.
Each stage uses a recorded copy of the source opening pool and order/seed.
Matchup lengths are common within a stage; the ordinary standalone KO editor
still supplies the separate per-round length feature.

The event snapshots the source conditions at creation. Later library/source
changes do not change it. Event definitions and child setups are immutable;
create another event to change them. Live concurrency controls apply to the
selected child tournament; later children retain the event's saved budget.

## League divisions

Choose **League divisions · promotion / relegation** in the event builder.
The first division is the highest. Give each division a unique name, assign
every engine once, and choose the number of seasons and pairs per matchup.
Each division plays its own round robin in every season.

The movement list has one number for each adjacent division boundary. For
three divisions, `2, 1` means two engines move each way between divisions 1 and
2, and one each way between divisions 2 and 3. The top division cannot promote
and the lowest cannot relegate. A division's promotion and relegation places
cannot overlap. Division sizes may differ, but remain constant between seasons.

After **all divisions** finish, the same points/tiebreak/seed order determines
promotion and relegation. The saved decision names every moving engine and its
destination. The next season starts automatically until the chosen season count
is reached. **Add another season** prepares one more season using the last
saved movement decision and waits for **Run event**. Engine versions and all
test conditions remain those recorded for the league; a new version needs a
new event. The top division's first-place engine is the season champion.

## Operation, recovery and corrections

- One event and one child tournament run at a time. Game concurrency within the
  child follows its own budget. The independent tournament queue and event
  runner cannot both dispatch automatically.
- Pause & drain stops new games and lets current games finish. Computer/app
  restart pauses automation; resume explicitly. Committed results, unfinished
  attempts, active stage, groups and qualification/movement decisions survive.
- Games remain ordinary tournaments: live boards, clocks, standings, TF counts,
  head-to-head, PGNs and technical reports are available through **Open stage**.
- Diagnostic replays require pausing the event and can be started separately
  from the stage. They never change official results or advancement.
- Official replacement in an earlier stage requires explicit invalidation of
  later stages, plus normal round/playoff dependency handling. Old stage
  tournaments retain all attempts and results as **Archived / superseded**;
  current event totals exclude them. Resume the event to replay the selected
  games and recreate subsequent stages from corrected qualifications.
- Retire an event before deleting its current stages. They can then be deleted
  individually using ordinary crash-safe deletion and backup compaction. When
  the last stage is deleted, the retired event record and decisions are removed
  from affected databases/backups too. Exported copies remain the user's files.
- Text event reports include all saved qualification/season standings and
  movement outcomes. JSON includes the complete stage list. Individual stage
  reports include event membership and current/archive status. No combined Elo
  is fabricated across stages with different opposition or conditions.

## Validation scope

- First custom/format/resource pass: 53 backend tests passed.
- First event/custom/queue pass: 31 passed, followed by GUI completion of a
  24-game group-to-final event. Forced worker termination retained committed
  results and archived the interrupted attempt before successful resumption.
- League/group backend pass: 17 passed. The league GUI completed three divisions
  over three seasons, then an added fourth season (24 fixture-engine games).
- Full regression checkpoint: 426 passed; final focused hardening also checks
  diagnostic replay, transactional rollback during stage creation, deletion and
  10,000 participants / 100 groups with no games materialized at creation.
- Six installed CPU engines completed 51 short, pure-node games: six custom,
  24 group-to-round-robin-final, 12 league, and nine group-to-KO. All PGNs parsed
  legally with unique attempt IDs; no engine failures; 13 tournament reports.
  These use a 12-ply cap or a mate-in-one position to test orchestration, and
  are not strength measurements or another endurance test.
- 42 JavaScript regression checks; all eight languages, 16 layouts at 20 px.

Evidence: `test-output/events-*.json`, `leagues-ui.json`, `events-full-suite.xml`
and the preserved `events-ui-*` / `events-real-*` fixture folders.
