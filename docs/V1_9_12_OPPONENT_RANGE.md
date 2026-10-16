# Engine Arena 1.9.12 — opponent-range rating comparisons

Designed by Mark Young. Coded with OpenAI Codex.

Rating Center now offers All opponents, ±100, ±200, ±300, ±400 Elo and a custom
positive range. All opponents remains the default. Select a single time category,
then select the range; Custom range requires Apply range. The all-category
overview returns to All opponents because each category has its own rating scale.

The comparison shows filtered Elo and rank, its confidence interval and LOS,
full Elo and full rank, rating change, included games, complete opening pairs and
opponents. Official games, W–D–L and score remain the complete selected record.
The summary distinguishes excluded distant opponents from matchups without a
finite baseline. An unavailable filtered rating never hides its full rating.
Text/forum, CSV and JSON exports carry the comparison; JSON also records the
evidence revision and scope. Entry history recalculates the baseline at each
stage end before applying the range.

## Calculation and limitations

1. Fit all opponents under the selected category, hardware, conditions, source
   and failure filters. Name search and best-version display do not restrict it.
2. Accept a matchup only when both full ratings are finite and their absolute
   difference is within the chosen range. A pair is accepted or excluded whole.
3. Jointly refit accepted samples, keeping the same reference. Do not select
   again using filtered ratings. Disconnected groups are not silently rebased;
   entries without an estimable rating show a reason and retain their full Elo.

The baseline is fixed during each calculation. New results or changed scope
recompute it. Full rank covers all configurations before best-version display.
Filtered rank covers the selected display; searching and sorting never change
ranks. CPU threads and GPU configurations keep their distinct identities.

Intervals and LOS are recalculated from the filtered samples, using the existing
paired/game-score sandwich covariance. They are approximate and conditional on
the reference and selected evidence. They do not account for uncertainty in the
data-dependent range selection; this is a sensitivity comparison, not independent
confirmation or a guarantee of greater accuracy. No minimum games or guessed
ratings are invented for excluded entries. Small samples remain visibly small.

No result, rating ledger, engine profile or PGN is changed by these views. Compact
retained evidence works after deleting tournaments. Fit/filter caches are bounded
and process only observed matchups, without a dense participant-by-participant
matrix. The work runs in the existing low-priority report process.

Install over the existing version after closing Engine Arena. No reset, replay,
reimport or installation of intermediate versions is needed. This is a private
test update; it has not been published to GitHub.
