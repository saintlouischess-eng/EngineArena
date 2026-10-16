# Engine Arena 1.9.11 — keep established ratings visible

A newly tested engine with only wins or only losses could make the entire
connected Rating Center pool show unavailable ratings. The official game count
remained correct, including when tournaments were deleted with ratings retained.

The solver now retains finite ratings within the fixed reference's strongly
connected comparison group. Other entries remain visible with their original
games and an explanation: separated results, no completed comparisons, or no
comparison path to the reference. It does not invent results, add rating priors,
move the anchor or assign arbitrary finite ratings to separated entries.

Confidence intervals and LOS use the finite group's observations and parameter
count. One-sided results outside that group do not artificially increase its
precision. The same correction applies to tournament pool ratings, Rating
Center, history, sorting, best-version selection and exports. The interface
explains partial availability in all eight supported languages.

The method follows the strong-component/extended-likelihood treatment discussed
by [Butler and Whelan](https://arxiv.org/abs/math/0412232). Engine Arena retains
its existing logistic expected-score model and pair-score sandwich uncertainty;
it does not switch to a binomial model for draws or opening pairs.

Validation includes isolated retention/deletion/restart tests, sparse pools of
10,000 entries, exact agreement of finite-group Elo/CI/LOS before and after
adding separated opponents, and returning score paths that resolve separation.
The owner's unchanged 12,480-game ledger produces 97 finite configurations,
including the fixed Berserk 14 reference at 3628. Nine configurations have
separated results; 123 have no completed reference path (including two without
a completed pair). The 12,478 eligible games contain 6,239 completed pairs;
6,169 pairs support the finite reference group. Two unmatched games remain saved.

Close Engine Arena and install over the existing version. Rating history and
settings are retained; no reimport or new tournament is needed. No data migration
or rating-evidence changes are required. This build is for owner testing and has
not been published to GitHub.

Designed by Mark Young. Coded with OpenAI Codex under his direction.
