# Two-engine SPRT review — September 26, 2026

Local development update. No GitHub publication or installer replacement.

## Setup and interpretation

Select exactly two profiles, create a tournament, and choose **Two-engine
SPRT**. Select the **Tested engine** by its numbered profile name. The other
profile is the reference. Positive logistic Elo and positive log likelihood
ratios favor the tested engine. This perspective stays fixed when colors,
standings order, or graph selection change.

Set Elo H0 below Elo H1. Defaults remain 0 and 5 logistic Elo. Alpha is the
nominal probability of selecting H1 under H0; beta is the nominal probability
of selecting H0 under H1. The GUI now exposes both as percentages, default 5%.
Both must be positive, and their sum must be less than 100%. These are error
targets, not posterior probabilities or the standings' confidence level.

The game/pair count is a **maximum**, not a guaranteed stopping sample size.
Reaching it without a boundary is **inconclusive**. Progress and ETA describe
that cap, not a prediction of when SPRT will decide. An H0 selection is not
automatically proof that the tested engine is weaker: interpretation depends
on the chosen hypotheses, particularly with negative bounds.

The live panel, likelihood graph, HTML report and its text export identify the
tested engine. The panel distinguishes continuing, paused, draining,
inconclusive, H0, H1 and invalidated inference. It shows admitted samples,
LLR and thresholds, with configuration details expandable. Reports include a
sequential section even before the first observation.

## Sampling and integrity fixes

New tests admit samples in scheduled order. A completed later game/pair waits
until every preceding sample is final, including its configured automatic
retries. This removes completion speed as the determinant of sample order.
Live descriptive standings continue to update as games finish. Each eligible
sample enters exactly once. Paired tests use both reversed-color legs;
unpaired tests use individual games and alternate colors.

Existing tests without a recorded ordering policy retain their legacy
completion order. Their saved evidence is never silently rewritten. New tests
record the policy, selected engine, sample order and exact official attempt
IDs. Admission, boundary detection and the associated official result commit
in one transaction. Abrupt worker termination preserves both admitted and
buffered completed results; only unfinished attempts restart.

The first crossed boundary remains frozen. Running games may finish and enter
descriptive standings, but cannot change that decision. Reports distinguish
these games from the stopping evidence. Diagnostic replays now work after a
boundary; dispatch admits only diagnostics and cannot schedule extra official
games. They leave official scores, the original curve and frozen decision
unchanged.

Manual adjudication before a boundary invalidates sequential inference as soon
as the adjudication request is committed. The GUI warns before submitting it.
Manual official-result replacement also invalidates inference. Repeated
corrections preserve the original evidence without repeatedly nesting it.
Descriptive statistics remain available. Start a new test for another valid
sequential decision. Adjudicating an already-running game after the frozen
boundary does not alter the earlier evidence.

## Numerical review

The constrained multinomial logistic likelihood formula is unchanged. Paired
samples have five score categories and unpaired samples have three. Empty
categories retain the existing 0.001 regularization. Wald thresholds are
`log(beta / (1-alpha))` and `log((1-beta) / alpha)`.

An independent SciPy constrained optimizer rechecked 144 likelihood cases;
maximum absolute LLR difference was 6.095e-10. The existing 1,408 descriptive
score/Elo/CI/LOS checks also passed. The logistic construction and regularization
were cross-checked against the [Fastchess SPRT implementation](https://github.com/Disservin/fastchess/blob/master/app/src/matchmaking/sprt/sprt.cpp).
Only Engine Arena's logistic model is offered; normalized and Bayesian Elo
are not interchangeable with these bounds.

These are implementation checks, not a new universal calibration guarantee.
Nominal error targets depend on model assumptions, independent samples and
stable conditions. Repeated correlated openings, selective failures/retries,
changing conditions, and finite-sample overshoot affect interpretation. Use
diverse recorded openings and predeclare retry/adjudication rules. Previous
simulation scope remains documented in STATISTICS.md.

## Acceptance evidence

- `tests/test_sprt_review.py`: both boundaries, both sampling modes, candidate
  direction, concurrent out-of-order completions, retries, game cap, empty
  reports, diagnostic-only dispatch, manual invalidation, and abrupt exit with
  buffered results. Legacy completion-order tests remain in test_sequential.py.
- Independent numerical audit: `test-output/tester-math-audit.json`.
- Real Stockfish 18 / Reckless checks: 28 official games plus two diagnostic
  replays, 30 unique legal PGNs, both boundaries and an inconclusive cap.
  These use 1,000 nodes/move, a 12-ply cap and deliberately wide boundary-test
  hypotheses. They test the lifecycle, not engine strength or endurance.
  Evidence and three full reports: `test-output/sprt-real.json` and its folder.
- GUI: candidate selection, custom alpha/beta, a complete node-only test,
  inconclusive live status, report output; all eight languages, both sample
  modes and 32 layouts at 20 px. Evidence: `sprt-ui.json`,
  `sprt-languages.json`, and SPRT screenshots in test-output.
- 439 backend tests passed; 48 focused checks passed. Full-suite evidence: `test-output/sprt-full-suite.xml`; focused checks:
  `test-output/sprt-focused.xml`. Existing JavaScript regressions: 42 passed.

Validation scripts: `validate_sprt.cjs`, `validate_sprt_languages.cjs`,
`validate_sprt_real.py`. Browser checks use the disposable preview_events.py
worker, never the user's tournament folder. Source profiles for real-engine
tests are read-only copies. The existing development EXE loads the updated UI
and worker sources.
