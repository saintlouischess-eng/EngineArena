# Engine Arena 1.3.2 — private league test update

Designed by Mark Young. Programmed with OpenAI Codex.

This candidate is for owner testing. It has not been published. The public release
remains 1.2.14; the full 64-engine league is underway and laptop acceptance is pending.

## Game scheduling (1.3.2)

All tournament setups now have a separate **Game scheduling** section:

- **Balanced round order** (default for new GUI setups) spreads round-robin
  matchups across the field before repeating cycles. Each engine appears once
  per matchup round, with a bye for odd fields; color-reversed legs stay paired.
  Rounds may overlap as resources become free. This balances the planned order,
  not completion counts or measured CPU time. Resource restrictions may cause
  eligible games to run ahead of blocked ones.
- **Matchup order** runs each matchup's repetitions together in participant order.
- **Seeded shuffle** permutes opening pairs (single games when unpaired) without
  duplicates. Its seed is separate from the opening seed. It varies the order,
  but does not guarantee even participation.

The order changes launch priority only. Canonical game numbers, opponents, colors,
opening assignments and result accounting are unchanged; game numbers can start
out of numerical order. Scheduling is incremental even for very large lists.
Two-engine matches have no field to balance. Gauntlet candidates necessarily play
more often; custom lists interleave repetitions of their configured matchups.
Swiss, knockout, double elimination and ladder apply the order inside each saved
round/tiebreak batch and retain all dependencies before the next round is paired.
SPRT retains its statistical sampling order; shuffled starts can delay a decision.

New events can inherit source scheduling or override it in the event editor.
Every division, season and final inherits that recorded choice. Individual
tournament HTML/text reports and event text/JSON exports identify the choice
and, when used, the scheduling seed. Recovery/retries retain exact game identities
and launch priorities. Replacement preserves attempts and archives dependent games.

Existing tournaments/events keep their recorded order after updating; installing
1.3.2 does not rearrange the running 64-engine league. Edit an unstarted tournament
or select the desired order when creating a new tournament/event. Started setup
remains locked. No games start automatically after installation or recovery.

## Tournament Manager progress (1.3.1)

Tournament Manager now opens with **all current tournaments**, including league
divisions and championship stages. Each row shows official/scheduled games,
completion percentage, active games and the tournament's game limit. Source and
status filters, name search and sortable headers apply in either execution mode.
Superseded stages are available through an explicit archive filter.

Linked stages have **View** and **Open event** controls. Their scheduling remains
owned by the event, keeping championship and promotion dependencies intact.
An active league displays its own shared resource budget and **Event resources…**
button. The independent queue cannot misleadingly show the whole event as
completed or pause league stages through unrelated queue controls.

The progress refresh uses compact counters and an indexed metadata view. It
caches only game limits, with invalidation when settings change; it does not load
game logs or repeatedly parse opening inventories. Existing events appear without
recreation. This update does not change their engines, clocks, openings or rules.

To update during a test, use **Pause & drain event**, wait for all games to finish,
close Engine Arena, install over the existing version, then use **Run event** to
continue the same league. Committed results remain in the existing data folder.

## New league choices

- Optional championship final after **every season**: first versus second in the
  highest division. Configurable even game count (default eight), color-reversed
  opening pairs, and configurable even tiebreak stages (default two games).
  Tied stages continue until a winner. Use normal per-engine controls or an
  ordered sequence of controls; the last control repeats as often as necessary.
- Regular-season winner and championship winner are recorded separately. Division
  standings alone determine promotion/relegation, even if a finalist loses or
  wins the championship. All divisions must finish before the final; the next
  season waits for the final to finish.
- Run divisions together within an event-wide CPU, memory, concurrent-game and
  shared-GPU budget. Source tournament limits still apply to each child. This
  uses the existing fair resource scheduler. Independent tournament-manager
  settings remain unchanged. One linked event runs at a time.
  The event's **Resources…** button can adjust shared limits while running;
  lowering limits lets active games finish before admitting more.
- Initial assignment can create consecutive strength divisions or spread seeds
  into balanced groups. The listed participant order is the seed order. No
  external rating lookup or inferred rating is used; review/edit assignments.
- Opening choice: keep the source selection each season, or advance through a
  saved, seeded shuffled sequence. Advance mode uses a new position per opening
  pair (per game in unpaired division play). Divisions share the season's sequence;
  the final continues after the longest division, and the next season continues
  after the final's regular and tiebreak games. Repetition occurs only after pool
  exhaustion. Replays retain their recorded openings. A one-position source
  naturally repeats that position; choose a sufficiently large book.
- The preview includes all regular championship games. Tiebreaks are additional,
  so the initial total is a minimum. Live totals include scheduled tiebreaks.
- Event reports show regular-season and final winners, final scores and individual
  tiebreak stages/controls, season movement, opening policy and shared budgets.
  Individual stage reports retain their own statistics. Testing/archive PGNs
  include EventId, EventStage and LeagueSeason; ordinary Event names also identify
  the season, division or championship. Stage ratings are not combined into a
  misleading single league Elo list.
- Saving immediately opens the saved event, with repeated submissions suppressed.
  The transactional database commit precedes acknowledgement; recovery-copy work
  is queued in the background. New labels are included in all eight languages.

## Recovery and corrections

Pause & drain stops admission across every division in the event and allows active
games to finish. A blocked division pauses/drains the whole event for review.
Restart recovery pauses the event and retains committed results, recorded openings,
original attempts, and saved decisions. Resume through **Run event**.

Replacing a division result requires explicit invalidation of any existing final
in that season and all later seasons. Replacing a final result invalidates later
seasons while retaining the season's division results. Superseded stages and every
original attempt remain archived. Championship creation, advancement, and the
next season's creation commit transactionally.

Existing saved events retain their recorded sequential scheduling, opening policy,
and standings-only championship rules. Create a new event to use the new choices.
Updating does not change engine profiles or start tournaments.

## Proposed owner test

64 CPU engines, eight divisions of eight, two seasons, one opening pair per
opponent and an eight-game final each season: **896 division games + 16 final
games = 912 scheduled minimum**, plus any tiebreaks. Use the owner's checked
Balanced GM book, 180+2, one thread and 1024 MB hash per engine, Ponder off,
CPU/concurrent-game limit 28 and memory budget 81920 MB. Clock tolerance 1 second.
This is workflow acceptance, not a statistically conclusive rating season.

## Reproducible checks

`tests/test_league_update.py` exercises finals and continued tiebreaks, regular
winner versus final winner, exact paired counts, opening offsets, deterministic
reproduction, correction dependencies, forced termination/recovery, 64-engine
preview, and live CPU/memory/GPU scheduling with pause/drain/resume. Existing
event/league/manager regression tests cover compatibility.

`scripts/preview_league_update.py` and `scripts/validate_league_update.cjs` use
disposable data to test the builder, 912-game preview, seeding, invalid counts,
save acknowledgement, final reports, and responsive layout. The fixture's synthetic
results are for UI/lifecycle validation only. `scripts/validate_league_package.py`
checks the packaged application with real Stockfish/Berserk profiles and verifies
reports, PGNs and crash recovery in a separate test workspace.
