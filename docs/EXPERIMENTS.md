# Suites and benchmarks

Select engine profiles in the library, then open **Suites & benchmarks**. Experiments start paused. Start/resume places an experiment behind running/queued tournament work. Cases run one engine process at a time; they do not overlap tournament games. Pause & drain finishes the current case. Stop current case archives that attempt and pauses; resuming restarts that case.

Each experiment snapshots profiles, cases and its search control. Node, depth and fixed time per move are supported. Pure node/depth searches have no chess-clock limit; the hang watchdog still applies. Startup/readiness limits are independent. Experiments use the selected experiment limit, a fresh process for each case, Ponder off and no opening book. A profile's tournament clock override does not replace the experiment limit. Thread counts are chosen explicitly for scaling benchmarks; there is no game concurrency multiplier.

## EPD suites

Each valid standard-chess EPD position needs `bm` (best moves), `am` (avoid moves), or both. A final legal move is correct when it satisfies both operations. Malformed lines identify their line number; contradictory answers and positions without legal moves are rejected.

Accuracy is correct cases / completed official cases. Engine failures count as unsolved, and the separate failure count makes them visible. Interrupted attempts remain archived and are excluded. Best-move PV recognition uses the primary PV, not secondary MultiPV output. JSON preserves `first_correct_pv_seconds`. New `time_to_solve_seconds` measures the start of the final uninterrupted sequence of correct reported primary PVs, only if the final move is correct. With no usable correct PV it falls back to the final correct move's elapsed time. This measures reported evidence, not the exact instant the engine internally found the answer. Old saved results retain their original first-correct-PV definition.

## Thread-scaling benchmarks

Enter distinct positive thread counts, a repeat count and a valid position with legal moves. The engine must advertise a Threads option accepting the requested value; otherwise the case records a configuration/protocol failure rather than reporting a misleading speed. Recorded effective threads are the UCI configuration sent to the engine, not a measurement of occupied CPU cores.

Measured NPS = final reported nodes / monotonic wall search seconds. Startup is excluded. Reported NPS is retained separately in JSON. Missing node counts remain unavailable. Summary rows group successful searches by profile slot and confirmed thread count, with mean/min/max NPS and NPS sample coverage / completed searches. Means exclude unavailable samples. The GUI shows up to 50 summary groups; exports include all groups.

Use enough nodes or time and repetitions for stable speed comparisons, and keep hardware/engine settings comparable. Very short searches mainly demonstrate that the workflow functions; they are poor evidence for thread scaling. Engine-reported nodes are not a universal amount of computational work across different engines.

## Storage and recovery

Case claims and results commit transactionally. Completing a case twice cannot change its result. A crash preserves completed cases and archives unfinished attempts; resume continues from the recorded cursor. Older experiment records migrate in place while retaining logs. New benchmark schedules store counts rather than expanding every repeat into a separate object.

The results window refreshes live and pages through 50 attempts at a time. Full JSON and readable text exports include every attempt, not only the visible page. JSON also includes original engine logs, identity, effective runtime options and profile/case snapshots.
