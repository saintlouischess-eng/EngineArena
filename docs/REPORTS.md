# Tournament reports and recorded test conditions

September 26 audit update: the completed 76,500-game tournament was independently reconciled against raw official results and all official move measurements. See `REPORT-AUDIT-2026-09-26.md` for evidence and caveats. Reports now include color results, a compact head-to-head matrix for up to 20 participants, pair coverage, explicit attempt accounting, a weighted technical overview, section navigation and expandable engine details. Text and print retain the full engine details. Hardware/resource variation is flagged; completed recovery messages are historical notes. Rendering cache changes no longer invalidate expensive numerical summaries. All eight language catalogs include these additions.

Local development update, September 20, 2026. The release hold remains in effect.

## Reading a report

The tournament report uses one committed, read-only database snapshot. HTML preview, HTML saving and Text export share the same report content and optional performance selection. Report work runs in the existing background report process, outside the writer and chess event loop.

- KO reports show the champion, quarterfinals/semifinals/final, per-match scores and stage controls. The initial seed is labeled **Seed**, and engines eliminated in the same round share the appropriate finish description. Match records and game statistics are separate.
- Regular and tiebreak games are counted separately, with a combined official total. Separate regular/tiebreak W-D-L follows standings order. All current official attempts count once; diagnostics, superseded attempts and invalidated rounds do not affect the official scores.
- Elo is relative to each engine's own sampled opposition. KO opponent selection, stopping and changing controls make fixed-sample CI/LOS descriptive approximations; they do not establish confidence that an engine is the strongest in the field. Existing normal and conservative calculations are unchanged.
- Failure forfeits are prominent. Details identify the game, recorded loser, reason and available engine error messages. KO matches show the score from the remaining games without implying what a replay would produce. The detailed failure list is limited to 200 entries; the full failure count and per-match totals are retained. Game history holds the complete list.
- Standings and engine configuration sections default to the first 50 participants in tournament order. **Engines in report → All engines** includes every participant without a fixed report cap. Full standings exports remain available. KO match and bye listings cover all recorded rounds.
- Conditions include the opening-book filename, available and used positions, assignment policy, seed, import depth, control settings, clock margins, adjudication and resource limits.
- An unsupported UCI Hash setting is **N/A (unsupported)** rather than an assumed transposition-table size. Lc0 NNCacheSize is labeled in positions. UCI_Elo is explicitly inactive when UCI_LimitStrength is off. Thread counts describe engine search threads, not dedicated physical cores; affinity uses logical processor IDs.

## Conditions saved for future run sessions

Start/resume records a session before its first dispatch: app/OS version, CPU model and physical/logical counts, installed RAM, available NVIDIA GPU model/VRAM/driver, and resolved resource budgets. Missing hardware readings are explicit. A new session is recorded after a pause/reopen/resume. No username, hostname or serial-number inventory is collected.

Engine startup records the identity, accepted UCI settings, affinity, and process start/end times. Recognized Lc0 announcements identify the loaded network even with WeightsFile set to autodiscover, along with backend, GPU, CUDA runtime and driver CUDA support. Where the network can be resolved within the engine's or configured weights folder, its SHA-256 is captured after the load announcement. This is a file fingerprint, not an attestation of engine-internal bytes. Unresolvable paths and missing files remain explicit; no filename is invented. File reads run off the event loop and use the existing fingerprint cache.

PGNs for newly recorded attempts include available network filename/hash/backend/GPU metadata and supported Hash/Threads values. Existing automatic PGNs remain intact. Manual exports render from committed records, including replacements.

The optional **Include observed performance samples** report checkbox includes available system-wide CPU load, RAM, CPU temperature/fastest-core clock and GPU utilization/VRAM/temperature/clock/power. The recorder aggregates fresh monitoring snapshots approximately every ten seconds while games are active. Monitoring preferences and sensor availability determine which readings exist. Counts, arithmetic means, observed minima/maxima and sampling times are shown. Missing values are not zeros; readings are not per-engine utilization or guaranteed instantaneous peaks.

Peak game attempts and GPU reservations are reconstructed from attempt intervals. Recorded process intervals provide engine-overlap evidence for new sessions. Activity includes retries, diagnostics and invalidated rounds. Interrupted intervals can extend to recovery; elapsed time includes pauses and downtime. Historical GPU groups without explicit limits are shown with the existing fallback of two engine instances, with guidance to set gpu0:1 for a single-instance GPU test.

## Per-engine technical readouts

**Include engine technical readouts** is optional and starts unchecked so the standard report opens first. It summarizes saved legal engine moves from current completed official attempts, including moves before a forfeit. Book moves, live/unfinished attempts, rejected moves, diagnostics, superseded attempts and invalidated rounds are excluded. Each game's history is read once for both sides. A Black-to-move opening is assigned correctly; self-play contributes two engine appearances but each saved move once.

Each engine's readouts are separated by recorded run session, effective time control, regular/tiebreak phase and observed engine configuration. A readout identifies CPU, physical/logical counts, installed RAM, session CPU budget/game limit, reported GPU, observed threads/hash/cache, and available network/backend/fingerprint. Unknown historical conditions remain unknown. The surrounding report includes session GPU/VRAM/driver, resource limits and optional sensor measurements. It does not claim dedicated CPU cores or attribute system-wide load, RAM, VRAM, temperature or power to an individual engine.

The measurement table gives coverage, arithmetic average, minimum and maximum for GUI-measured thinking seconds, engine-reported search seconds, depth, selective depth, reported nodes/NPS, hash occupancy, tablebase hits and remaining chess-clock seconds. UCI time is converted from milliseconds; hash occupancy from permille to percent. Additional summaries show summed thinking time/nodes, nodes divided by measured or reported time over the same covered moves, clock-at-or-below-one-second/negative-clock counts, evaluation-field coverage, game appearances/W-D-L and engine-attributed forfeits. Missing data is distinct from a reported zero; nonfinite/invalid numeric values are excluded. Node/depth/movetime controls do not report chess-clock pressure. Final-per-move search metrics can include reused work or pondering, and engine-specific NPS/node/depth definitions are not a strength comparison.

Both HTML and readable Text exports honor engine scope and technical/performance selections. Disabling technical readouts skips move-history analysis entirely. The background report process streams moves with bounded memory rather than loading them all. One local synthetic 50,000-game / 4,000,000-move report took 42.48 seconds with technical analysis; the prior 1.38-second measurement below predates that analysis. A current 52-game / eight-engine KO report took 0.32 seconds. These are point measurements, not endurance or concurrent-load guarantees.

## Historical reports and recovery

Old tournaments are not labeled with the computer's current hardware. A legacy report can sample the first official game's saved Lc0 announcements when attribution is unambiguous; its scope and lack of a historical network fingerprint are explicit. A current weights file is never hashed to manufacture historical evidence. New engine observations show up to 32 distinct evidence bodies per displayed engine; full saved evidence remains in SQLite.

`run_sessions`, `run_attempts`, `engine_evidence` and `attempt_engines` store the new data. Engine evidence bodies are deduplicated by content hash; process intervals and attempt links are separate. Runtime writes use the Store transaction/failure machinery and existing recoverable backups. Moves/results retain their existing transactions. Metadata failures are surfaced as saving failures rather than silently dropping evidence. Recovery retains committed observations, marks unclosed sessions interrupted and follows the existing unfinished-game recovery policy. Tournament deletion also removes its session/attempt links and unreferenced engine evidence, including applicable backup records.

## Validation

- Technical readout update: 21 focused backend report tests passed (`test-output/engine-readout-final-focused.xml`) plus eight text-format JavaScript tests. Coverage includes independent metric math, missing/zero readings, official replacements, invalidated rounds, running/diagnostic exclusions, Black-to-move openings, self-play, session/control/configuration separation, node-only clock omission, all-engine reports and both HTTP report/export selection paths. Browser checks verified all-engine and technical/performance switches, preservation across refresh, actual Text export, and populated HTML tables. Read-only current-tournament examples: `exports/engine-technical-readout-preview-20260920.html` and `.txt`. No current results or tournament settings were changed.

- 269 backend tests passed: `test-output/reports-delivery-20260920.xml`. Coverage includes runtime detection and SHA-256 through UCI fixture processes, node-only commands and PGN metadata, forced process exit with committed and unfinished attempts, restart recovery, deletion, failed-game replacement, sequential report invalidation, pairing and 32 concurrent short games.
- 33 JavaScript tests passed: `test-output/reports-js-tests.txt`.
- Actual old KO report was audited independently and regenerated read-only. Revised copies are in `exports/report-polish`; all 146 official results and 73 pairs are retained. Its two Lc0 crash forfeits remain official; no results were changed.
- Point measurements on existing synthetic fixtures: 10,000-participant report about 0.42 seconds; 50,000-game report about 1.38 seconds. These are individual local measurements, not sustained-load or endurance acceptance.
- Isolated browser preview exercises HTML/Text exports and the performance inclusion option. Native packaging and a real Lc0 run with the new fingerprint recorder remain separate follow-up checks. No real tournament was restarted and nothing was published.

The development launcher loads updated source/UI on the next reopen. No native rebuild is needed for this change.

## Completed-tournament performance (September 26)

Reports run in a separate, cancellable read-only process, independent of pool-rating and chart calculations. The dialog shows saved-game progress during technical analysis. Closing the dialog, choosing Cancel report, changing the report selection, or shutting down cancels unnecessary report work without touching saved results.

Completed reports are cached against a durable workspace identity/revision and their presentation options. Every report-affecting Store transaction advances the revision atomically with its changes; official replacements and subsequent play therefore invalidate old reports. UI-only preferences do not invalidate numerical results. The technical summary has its own language/confidence-independent cache, so changing confidence, language, or selecting the same engines does not repeat the move scan. Restoring a recovery copy and deleting tournaments clear disposable report caches. Failed cache writes do not prevent reporting.

On the actual completed 76,500-game tournament, the original standard report took 6.49 seconds and the full technical report took 165.36 seconds, of which 158.84 seconds read 9.74 million saved moves. A first uncached technical scan is still proportional to the move history; caching improves repeated access, not that initial scan. The standard report is available without requesting the scan. HTML and readable text exports are in `exports/Engine comparison - 76500 games.html` and `.txt`.

The final unchanged full report reloaded in 0.083 seconds (rendering function, excluding process startup/UI painting). All 7,237 table cells matched the original uncached full report exactly. Final validation: 315 Python tests and 41 JavaScript tests passed; browser progress/cancellation, report options, text export and layout checks passed. Native worker readiness was 0.828 seconds and a normal unchanged desktop close took 0.914 seconds.
