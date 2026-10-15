# Engine Arena 1.8.0 — season admission

Private installer for owner testing. Designed by Mark Young; coded with OpenAI Codex.

## Workflow

Save a source tournament containing every candidate engine and the desired
default conditions. In Events & leagues, choose **Create season competition**.
Select one of the season admission policies:

- **Keep the existing roster**: the previous workflow. All selected engines have
  a league place. New entries and withdrawals are managed manually.
- **Everyone requalifies every season**: all eligible candidates play qualification
  before each season. The highest finishers fill the divisions from highest to
  lowest. Those outside the field remain candidates for later seasons.
- **Challengers compete for places**: everyone qualifies for the first season.
  Subsequently, returning places at risk are counted from the bottom of the
  earned division/seed order. Protected engines keep their division places;
  the remaining incumbents face outside candidates for the vacant places.

Set **Main season field size**, then adjust **Division sizes, highest first**.
The sizes must add up to the field, and each division needs at least two engines.
Changing the field input distributes it over the existing number of divisions;
editing the division sizes allows unequal divisions and updates the field total.
There is no 32-, 64- or 128-engine restriction. Candidate and main-season field
sizes do not determine concurrency; the separate CPU, memory, GPU and simultaneous
game budgets continue to govern execution.

For example, invite 300 candidates for 64 season places, with eight returning
places at risk. Season 1 qualifies all 300 for 64 places. Thereafter, 56 returning
engines are protected and the remaining 244 candidates compete for eight places.
Removing a protected engine creates an additional vacancy. A different engine
replacing an incumbent must qualify; a version upgrade retains the entrant's
identity and eligibility. Neither type changes historical games or versions.

Swiss and round-robin qualification are supported. Swiss rounds are reduced to
the available opponent count when a later qualifier has fewer contestants; the
preview shows the effective count. With one uncontested candidate for one place,
admission is recorded without fabricating a game or rating result.

## Season review

The paged roster includes the whole candidate pool, with protected, qualifying
or outside-field status. Add new entrants from the engine library at a season
boundary, or upgrade an existing candidate, including one that missed the last
cut. The candidate-number editor permits withdrawal and later reinstatement;
history is retained. New entries do not enlarge the configured season field.

Review windows and version-update rules remain configurable. Automatic
continuation uses the approved candidate pool; adding candidates requires a
scheduled review window. Division assignments in admission events are earned
through qualification instead of overwritten manually.

Protected-place order uses earned division seeds: higher-division relegations
are seeded before the division's retained engines, and lower-division promotions
follow them. Within each block, recorded standings order is preserved. The
selected placement tiebreak policy also applies to the protected-place boundary.
Full requalification provides the alternative with no protected places.

In Progressive Championship, higher stages include the assigned residents plus
incoming qualifiers. These are existing members of the same bounded season
field; a climber can play more than one stage. The preview explicitly lists the
actual playing field in each division. Promotion does not grow the unique field.

## Results, schedules and recovery

Qualification stages include the season number. Season overviews show qualified
and not-qualified outcomes, provisional until any required playoffs finish.
Reports record protected entrants, qualifiers and engines missing the cut, using
the names/versions recorded at the decision. Careers retain outside candidates.

The schedule preview includes qualification for every planned season, division
games and the regular championship. Totals assume the current candidate pool;
review edits recalculate remaining games. Placement playoffs and championship
tiebreaks can add games. Admission and advancement use the existing transactional
stage checkpoints. Correcting an earlier official result requires invalidating
dependent stages; all previous attempts remain available.

## Compatibility and validation

Existing events retain their saved rules. Installing this version does not add
qualification to an event already underway. Use a new competition to select
the new workflow. The owner's running Season 2 was not opened or changed during
development or validation.

Validation uses disposable simulated seasons, not a restarted real test. Cases
cover both division modes and admission policies, newcomers winning places,
outside-candidate upgrades, withdrawals, admission-boundary playoffs, result
correction, extension, fresh copies, forced process termination and recovery.
Large-pool simulations exercise 300/64, 500/128 and 1,000/32 candidates/places.
Browser checks exercise 300 candidates, both exact schedule forecasts, pagination,
approval, reports and eight languages at desktop and laptop widths.

Pause and drain the event, then close Engine Arena before installing. Resume the
existing event afterward; its saved format and results are preserved.
