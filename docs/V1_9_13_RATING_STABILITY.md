# Engine Arena 1.9.13 — rating calculation stability

In large, uneven fields, newly completed games could make all non-anchor Elo
values temporarily disappear with “Fit did not converge.” Later results could
make the same list calculate successfully again. No game records were lost.

Near the solution, the solver compared two large totals whose tiny difference
was obscured by floating-point rounding. It could reject a valid final step and
spend additional time trying smaller steps before returning unavailable ratings.
The solver now measures the change directly for each comparison and sums those
changes accurately. The convergence requirement has not been relaxed.

This correction is shared by Ratings Center, tournament rating reports, and
opponent-range comparisons. It does not change the rating model, anchor,
opening-pair rules, confidence calculation, or saved evidence. Truly separated
or disconnected entries still show the appropriate unavailable status.

Regression coverage includes an independently generated 400-entry field,
successive result additions, likelihood residuals, different reference engines,
reversed colors and observation order. Existing rating tests cover confidence,
retention, replacement games, filters, ranking, CPU/GPU identities and exports.

Validation: 86 targeted tests passed. All 40 consecutive result snapshots from
the reported 400-entry run converged after the correction. An independent dense
NumPy calculation matched all 398 finite ratings within 0.000001 Elo and sampled
confidence standard errors within the same tolerance. The other two entries had
separated results and correctly remained uncalibrated.

The packaged worker passed the formerly failing 28,929-game snapshot and the
28,932-game snapshot, including after restart. Browser checks covered keeping
rows visible while refreshing, newer results, paging, the fixed anchor, best
versions, and both themes. The copied evidence was unchanged. Fresh fits with
50 visible confidence intervals took approximately four seconds on the test
machine; cached requests were faster. This is not an instant or precomputed list.

Pause and drain running tournaments, close Engine Arena, then install the update
over the existing version. Resume afterward. No ratings reset or reimport is needed.
This candidate is for local testing; it has not been published.
