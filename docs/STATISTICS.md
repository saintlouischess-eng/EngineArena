# Statistical methods and validation

All descriptive statistics use current official results. Diagnostic attempts and invalidated rounds are excluded. Replacements reverse the former contribution before applying the new one. Byes are tournament points, not observations of engine strength.

## Samples, Elo and uncertainty

An unpaired observation is a game score in {0, 0.5, 1}. A paired observation is one completed reversed-color opening pair, normalized to {0, 0.25, 0.5, 0.75, 1}. An incomplete pair contributes to W–D–L but not paired Elo, intervals or LOS. Logistic Elo is `400 log10(p / (1-p))`; empirical score zero/one maps to negative/positive infinity.

The normal interval uses sample variance with Bessel correction and `mean ± z × standard error`, where `z = inverseNormalCDF(0.5 + confidence/200)`. Limits are clipped to [0,1] before the Elo transformation; 95% gives `z = 1.95996398454`. LOS is the normal CDF of `(mean - 0.5) / standard error` and does not change with the selected confidence level. Neither normal uncertainty nor LOS is supplied for fewer than two samples or zero empirical variance. This plug-in normal approximation can under-cover small samples. The UI offers 50, 68, 80, 85, 90, 95, 98, 99, 99.9 and 99.99%, plus custom levels from 50 to 99.99%. See NIST's [common confidence levels](https://www.itl.nist.gov/div898/handbook/eda/section3/eda352.htm) and [normal quantile construction](https://www.itl.nist.gov/div898/handbook/prc/section1/prc14.htm).

The conservative alternative uses the two-sided Hoeffding radius `sqrt(log(2/(1-confidence/100))/(2n))` for observations in [0,1], clips score limits to [0,1], then transforms to Elo. At 95% this reduces to `sqrt(log(40)/(2n))`. It remains valid without estimating variance and may be very wide or infinite. Its fixed-sample coverage bound requires independent observations; dependence within a color-reversed pair is allowed because the whole pair is one observation. See [Stanford concentration notes](https://ai.stanford.edu/~gwthomas/notes/concentration.html) for the independent bounded-observation inequality.

The selected level changes standings, head-to-head, crosstable details, curves, pool-rating uncertainty and reports. The selected normal/conservative method changes applicable display intervals; anchored pool ratings retain their own sandwich normal approximation. Exports include `confidence`, `ci` and `ci_conservative`; legacy `ci95` and `ci95_conservative` remain actual 95% bounds for compatibility. Neither method is a confidence sequence; repeatedly checking these intervals is not a valid stopping rule. Changing a display level does not change SPRT alpha/beta. Repeated correlated openings, changing engines and adaptive opposition can violate the model. Aggregate Elo describes sampled opposition and is not a calibrated absolute rating.

CSV exports use scalar confidence-bound columns rather than embedding arrays in cells: standings provide `ci_lower`, `ci_upper` and `ci_method` for the selected normal or conservative method; pool exports provide `ci_lower` and `ci_upper` for their own normal approximation. JSON retains the full interval arrays and compatibility fields described above.

The September 18 preview audit independently checked 1,408 descriptive-statistics cases at eleven confidence levels (50 through 99.99%, including custom 97.5%), 144 constrained SPRT cases and 180 pool-rating estimates. Production LOS uses the numerically stable complementary-error-function form of the same normal CDF to preserve tiny nonzero probabilities. No statistical model was changed. See `tester-math-audit.json` and `tester-pool-audit.json` for errors and methods.

## Sequential tests

SPRT uses constrained multinomial maximum likelihood under two logistic expected-score hypotheses, with three categories for unpaired games or five for paired scores. Empty category counts are regularized to 0.001. The log likelihood ratio is compared with Wald thresholds `log(beta/(1-alpha))` and `log((1-beta)/alpha)`. This model is consistent with the established constrained-likelihood approach in [Fastchess](https://github.com/Disservin/fastchess/blob/master/app/src/matchmaking/sprt/sprt.cpp); estimated nuisance probabilities and finite-sample overshoot mean nominal error targets need empirical calibration.

The first boundary is committed with the official result transaction. Already-running games drain into descriptive statistics without moving it. Prescribed automatic retries finish before a pair enters the sequential sample. Manual replacement invalidates the inference while retaining the original stopping evidence. A new sequential decision requires a new test.

## Independent checks, September 15, 2026

- A separately implemented SciPy SLSQP optimizer over logit probabilities, with an exact expected-score constraint, checked 144 trinomial/pentanomial cases including empty bins and large counts. Maximum log-likelihood-ratio difference from production: 6.095e-10. Saved reference values are tested without SciPy at runtime.
- 1.2 million fixed-sample simulations cover six draw/correlation/effect distributions and 20, 100, 1,000 and 10,000 pairs. Normal coverage was as low as 93% at small sample sizes; at 1,000/10,000 pairs the observed range was 94.79–95.138%. Extremely drawish small samples often have unavailable normal intervals; the report includes availability separately. Conservative coverage was 99.984–100% in these scenarios.
- 36,000 sequential trials cover 18 paired/unpaired scenarios, both null boundaries, draw probabilities 0.5/0.9/0.99 and paired correlation mixtures 0/0.6. Hypotheses are 0 versus 5 Elo, or 0 versus 1 Elo at draw probability 0.99. No trial reached the 200,000-sample censoring limit. False-decision rates were 4.15–5.75%; every individual Monte Carlo 95% interval included 5%. This does not prove calibration for all nuisance distributions.
- The C# simulator independently uses safeguarded Newton optimization; all 376 saved checkpoints were checked against production Python likelihoods (maximum error 1.410e-12).
- The GUI choice persists across reload. On the eight-pair all-draw fixture, the conservative Elo interval is approximately [−677.5, +677.5], while normal uncertainty/LOS remain unavailable.

## Reproduce

### Anchored pool ratings

The pool model fits `p_ij = logistic(theta_i - theta_j)` to normalized game/pair scores by maximizing the weighted logistic score objective. It is a quasi-likelihood for fractional draw/pair scores, not a separate probabilistic draw model. One selected reference parameter is fixed, and natural-log odds are converted to Elo with `400 / log(10)`. A supplied reference value defines the scale; it is not independently verified by the software.

Only the reference's connected comparison component is identifiable on that scale. Strong connectivity of the positive-score comparison graph is checked before fitting; separation yields unavailable estimates, not arbitrarily clipped ratings. See [Butler and Whelan's analysis of Bradley–Terry existence conditions](https://arxiv.org/abs/math/0412232). A damped Newton solver uses conjugate-gradient products on the sparse anchored information matrix; no dense participant matrix is created.

For uncertainty, `H = Σ n p(1-p) x xᵀ` and `M = Σ (observed_score-p)² x xᵀ` are formed from each histogram. The covariance is `H⁻¹ M H⁻¹ × G/(G-d)`, where G counts independent games/pairs and d is the number of fitted ratings. This is an approximate finite-sample-adjusted sandwich estimate; the [statsmodels covariance implementation](https://www.statsmodels.org/dev/_modules/statsmodels/stats/sandwich_covariance.html) documents the score/Hessian construction. Visible variances are solved individually without allocating the inverse. Normal intervals and LOS are conditional on the fixed reference. Zero empirical variance or insufficient residual degrees of freedom yields unavailable uncertainty. Color effects, reference uncertainty, nontransitivity and changing opponents are not separately estimated.

An independent SciPy trust-region fit with root refinement and dense sandwich covariance checked 180 estimates across 2/3/5/12-engine paired/unpaired pools. Maximum Elo discrepancy was 9.257e-9 and standard-error discrepancy 1.780e-10. Two 1,000-replication, three-engine paired simulations (500 pairs per matchup) observed interval coverage from 94.4% to 95.6%. These results support the tested scope, not universal coverage.

A 10,000-engine star graph used 9,999 actual comparison edges. Fitting and calculating 50 visible uncertainties took 2.19 seconds with allocation tracing enabled, with 11.12 MB peak Python-traced allocations. This is a sparse fixture, not a dense 10,000-engine round-robin performance claim. Raw evidence: `test-output/ratings-validation.json`. Run `scripts/ratings_validation.py` in the separate validation environment to reproduce.

### Commands

Use a separate Python 3.12 validation environment; NumPy/SciPy are not application dependencies. From the source root:

```powershell
python -m venv .validation-venv
.\.validation-venv\Scripts\python.exe -m pip install -r requirements-statistics.txt
dotnet run --project scripts\statistics-simulation\StatsSimulation.csproj -c Release -- test-output\statistics-sprt-simulation.json 2000
.\.validation-venv\Scripts\python.exe scripts\statistics_validation.py
.\.venv\Scripts\python.exe -m pytest tests --basetemp test-output\pytest -q
```

The two statistical scripts write JSON under `test-output`. Random seeds, distributions, availability, confidence limits and likelihood errors are retained. Regenerate committed optimizer reference fixtures only deliberately with `--write-fixtures`.
