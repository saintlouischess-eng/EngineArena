# Knockout tournaments

Choose **Knockout (KO — single elimination)** when creating a tournament. Set **Games per match** separately for each round, including the final. These are actual games, not opening-pair counts. With reversed colors enabled, every count must be even. Unpaired matches allow odd counts and alternate colors. First-round byes are shown and never count as played games or match wins.

For example, eight engines with 4 games in each quarterfinal, 6 in each semifinal and 8 in the final require **36 regular games**. The preview shows this total before creation. Added tiebreak games increase the scheduled total and can change the completion percentage and ETA.

## Ties and controls

New KO tournaments keep playing tied matches until one engine wins a complete match or tiebreak stage. They do not advance an engine on seed or standings points. Every scheduled game in a stage finishes, including the reversed-color leg, before the match is decided. A win apiece still produces a tied two-game stage.

- **Games per tiebreak stage:** choose the length of each additional stage. Paired testing requires an even count.
- **Keep each engine’s normal control:** retain the tournament control and any independent profile controls or handicaps.
- **Custom sequence / progressively shorter:** set an ordered list of controls for both engines. The editable example is 60 seconds + 1 second per move, then 30 + 0.5, then 15 + 0.25. The final control repeats as long as stages remain tied. Choose controls appropriate to the regular match; the example does not automatically scale to its duration.

Custom tiebreak controls replace both engines’ normal controls during those games. Each game starts with fresh clocks. All supported control types are available, including pure nodes per move without a chess clock. Startup, readiness and hang watchdogs remain independent of these controls.

There is no finite maximum number of tiebreak games: repeated draws can continue indefinitely. Pause/resume and existing adjudication controls remain available. Saved tournaments retain their original rules; installing this update does not change existing seed-based or limited-playoff policies.

Double-elimination KO also uses continuous tiebreaks for new tournaments. Its normal match length remains the common opening-pairs-per-match setting; the per-round game-count table applies to single elimination.

## Shared openings and tiebreaks

Choose **KO: shared sequence; new opening each pair** to give all matchups the same opening sequence in a stage. Games 1–2 use the first opening with colors reversed; games 3–4 use the next opening. Each additional tiebreak pair advances to a fresh position, and later KO rounds continue from the end of the sequence. With color reversal off, it advances after every individual game. This replaces the former interpretation that reused one position throughout an entire KO round and its tiebreaks. The old shared-suite preset receives the same correction; the GUI shows one shared KO option.

**Fresh position for every opening pair** instead gives each matchup pair its own position. **Sequential** and **Seeded shuffle** avoid recycling the pool until it is exhausted. **Seeded random** allows immediate repeats. **One fixed position** deliberately repeats through all tiebreaks. Setup explains these choices and warns when only one position is available; no preset can create variety from a one-position pool.

Assignments are reserved transactionally in `opening_suites` before incremental materialization, then recorded in each game. Tiebreaks with more than one pair consume that many new positions, even when the regular match was shorter. Both colors share the identical recorded opening. The same round/stage suite survives official-result replacement so unchanged matches retain comparable openings. The ledger stays through dependency invalidation, recovery and backups, and is removed when its tournament is deleted. PGNs include one-based `OpeningPosition` and `OpeningAssignment`, and new shared KO games identify their opening policy.

Existing games and previously saved stage plans retain their recorded openings. After reopening the updated app and resuming an existing tournament, newly planned KO stages advance beyond its old suite. Previously completed or pending games are not rewritten. Reports distinguish old and new recorded stages; restarting the whole tournament is unnecessary.

Validation of this correction: 278 backend tests and 34 JavaScript checks passed, including both shared presets, single/double elimination, paired/unpaired games, multi-pair tiebreaks, exhaustion, partially materialized legacy stages, forced-exit recovery, official replacement and deletion. Evidence: `ko-opening-final-20260920.xml`, `ko-opening-coordinates-js.txt`; isolated GUI checks used `ko-opening-coordinates-ui-20260920`. No real tournament was interrupted or changed and nothing was published.

## Results, reports and recovery

Live KO results show the current round, surviving engines, match scores, stage scores, actual tiebreak control and winners. The default standings order follows survival and elimination round. Same-round exits share a status and are ordered by seed; the row numbers do not award distinct finishing places. Clicking statistical headers still sorts by the selected game statistic.

Game W-D-L and points remain separate from match wins/losses. Elo, confidence intervals, LOS, pool ratings, opening statistics and head-to-head statistics describe the official games sampled, including tiebreak games. They do not select bracket winners; pooled results at different controls/opponents are not a single uniform strength test. Ratings retain the existing paired-game accounting.

**Full KO report** includes every recorded round, regular match, tiebreak stage, score, control, outcome and bye. HTML and readable text exports are available. Standings CSV/JSON/Text include KO status and match records; the full JSON/text snapshot also includes match results. The live display limits match and bye rows for large fields and points to the full report.

History, focused games and live cards identify KO rounds and tiebreak stages. PGNs record `CompetitionStage`, `PlayoffStage`, and the actual White/Black time/search controls. Stage metadata is stored with each opening before its games are materialized, so restarting or replaying an unfinished game uses the same opening and control. Original attempts remain archived. Result replacement still requires explicit invalidation of affected later stages or rounds, then rebuilds bracket results without double-counting. Diagnostic replay does not change the bracket.

## Local validation, September 20, 2026

- Full backend regression suite: 261 passed before the final small adjustments; focused follow-up runs cover final history clocks, reports, continuous defaults and legacy behavior.
- All 32 JavaScript tests and UI syntax checks passed.
- New acceptance cases cover 2/3/5/8/9-engine brackets, different round lengths, byes, ties beyond the old limit, repeating the final control, complete paired stages, odd unpaired matches, a champion with fewer game points than the runner-up, invalid settings, replacements and diagnostic replay.
- A test-owned worker was forcibly terminated with a playoff attempt open. Recovery retained committed results and the saved stage/control, archived the interrupted attempt and finished the same tournament without duplicate official games.
- Actual fault-engine UCI sessions verified `go nodes 77` with no clock arguments, and clock-based tiebreak commands with the configured increment.
- Isolated GUI review covered 4/6/8-game round counts and the 36-game preview, invalid odd paired counts, shorter-control presets, stage add/remove, format changes, saved configuration, active/complete KO results, pending tiebreak clocks, and HTML/text reports. No user tournament or settings were changed.
- Synthetic committed-snapshot reads: median 87.9 ms with 10,000 participants (only 64 game rows materialized), and 118.4 ms with 50,000 recorded games. These measure result reads on this machine, not prolonged engine throughput or a full 50,000-game endurance run.

Evidence: `test-output/ko-full.xml`, `ko-followup.xml`, `ko-default-final.xml`, `ko-scale-results.json`; GUI fixture `ko-ui-20260920`. No installer, GitHub push or release was produced. The release hold remains in force.
