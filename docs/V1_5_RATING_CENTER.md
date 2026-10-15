# Engine Arena 1.5.0 — Rating Center

## 1.9.3: opening pairs across system updates

CPU-only opening pairs now remain usable across Windows maintenance-build and
display-driver updates when the recorded CPU hardware, engine configurations,
time controls and other playing rules still match. The original conditions IDs,
hardware records and games are preserved. This is a read-only calculation change;
existing compatible games count automatically after installing the update.

GPU and unverified legacy GPU comparisons retain exact condition matching.
Changes to the OS family, CPU, memory, clocks, adjudication or engine identity
are not silently combined. Selecting exact hardware or conditions still requires
both games to be present in that filtered view.

The Rating Center explains how many CPU pairs were retained across system
updates. It also shows games outside the sample because their partner is absent
from the view, engine/color identities differ, or conditions are incompatible.
Text and JSON exports preserve this explanation. W-D-L continues to include all
selected official results, even when a complete statistical pair is unavailable.

Private installation candidate. Designed by Mark Young; programmed with OpenAI
Codex. Includes the season, competition desk and setup improvements in 1.4.2.
This installer has not been published. Close Engine Arena before installing over
your existing installation. Existing tournaments and engine profiles are retained.

## Getting started

Open **Rating Center** in the sidebar. The main list collects games first attempted
after this update initializes its database. Older results are not silently imported.
Use **Manage contributions** to import selected tournaments or pages of tournaments,
including league stages. Import can stop between batches and be repeated safely.
Official replacements stay synchronized even when automatic new-game collection is
paused. All official failures count by default; an optional view filter excludes
them. This is a descriptive filter, not evidence that failures were random.

Bullet, Blitz, Action / Rapid and Classical each have independent ratings. **All
categories** compares them side by side without inventing a combined Elo. Fixed
nodes, fixed depth, fixed move time, and unequal clock handicaps have separate lists.
For those limits or clock handicaps, the individual budget is part of entry identity.

An entry records engine version, executable/network identity when available,
configured UCI threads, hash, options, launch arguments, affinity, ponder, Chess960,
and engine move-book configuration. Changing a relevant configuration creates a
distinct entry. Display names automatically include the configured thread count:
`Stockfish 19 · 1 thread` and `Stockfish 19 · 32 threads` can appear in one list and
play each other. Thread counts describe requested UCI settings, not measured CPU
utilization. Engines without a recorded thread option say **threads unverified**;
resource reservations are not mistaken for confirmed engine settings. Configuration
IDs distinguish otherwise similar labels. Entries without executable fingerprints
use conservative profile identity and should not be assumed equivalent binaries.

## Time categories and comparable conditions

Default boundaries use a nominal 60-move allocation:

| Category | Nominal allocation |
| --- | --- |
| Bullet | Below 180 seconds |
| Blitz | 180 through 600 seconds |
| Action / Rapid | Above 600 and below 3,600 seconds |
| Classical | 3,600 seconds or more |

Fischer increment and delay are multiplied by 60. Staged controls sum the time
and increments available over 60 moves; repeating stages are included. This is
a categorization convention, not predicted game length. Actual saved clocks,
including championship/KO tiebreak controls and engine handicaps, take precedence
over the tournament default. Pure node/depth limits never become clock ratings.

Change boundaries in **Rating settings** on an empty list. To recategorize existing
evidence, reset the list and explicitly import selected history under the new rules.
Create additional named lists to isolate test methods or hardware; those begin with
automatic collection off. A hardware filter compares recorded machine snapshots.
No CPU-speed normalization is performed. Exact time controls, book and adjudication
conditions remain in the evidence and exports. Unknown historical hardware remains
explicitly unknown. Combining different conditions is a user choice, not a claim
that all tests are interchangeable.

## Ratings, anchors and engine updates

The sparse logistic expected-score solver fits all opponents together. Ratings are
not sequential per-game Elo updates, so concurrent completion order does not change
fitted rating differences. Paired tournaments contribute only complete reversed-color
opening pairs with matching conditions and configurations. Unpaired tournaments
contribute individual games. W–D–L can include a game before its pair is complete.
Diagnostic attempts, byes, same-configuration self-play and superseded event stages
are excluded. A replacement updates the game's single ledger contribution; original
attempts are preserved in tournament history.

Without an anchor, each category has a stable internal reference at zero. This is
not a CCRL or FIDE calibration. **Reference anchor** fixes one exact configuration
at a supplied rating. It does not move automatically when that engine is upgraded.
Disconnected entries and separated/unbounded fits are shown as unavailable instead
of invented numbers. The reference itself has no estimated confidence interval.

CI and LOS reuse the existing score-histogram sandwich uncertainty calculation.
They are approximate, conditional on a fixed reference whose uncertainty is not
included. LOS compares with the named reference, never the next ranking row.
Small samples, all draws, adaptive schedules, SPRT stopping, correlated openings
and changing conditions limit interpretation. See `STATISTICS.md` for the model.

Open an entry for its configuration, stage history and version continuity. Link a
predecessor with the same thread count to show its rating as a **provisional reference**.
Approved event upgrades link automatically when their entrant identity and relevant
configuration match. A new version never inherits measured games or a narrow CI.
Its own results determine its fitted rating. Removing the link leaves it unrated
until sufficient comparisons exist. History reconstructs cumulative current official
evidence through original game-completion endpoints; a later replacement revises that history, rather
than preserving a misleading obsolete official result.

## Storage, deletion and recovery

The ledger stores one official game reference, result, reason, pair identity,
configuration IDs, conditions and source. It does not copy moves, PGNs or engine
search logs. Shared configurations and hardware/conditions are deduplicated.
Result and rating updates commit together. Fitting runs in a low-priority report
process, after its SQLite read transaction closes; the GUI displays 50 entries per
page. Imports commit bounded 200-game batches and do not start engine processes.

Deleting a tournament or event offers **Keep compact Rating Center evidence**.
Unchecked removes the contribution as well as game data; checked retains only
already-collected rating evidence while freeing the large game history. It does
not import missing history. Superseded stages remain excluded. Exports saved outside
Engine Arena are independent files and are not removed.

**Manage contributions** removes selected tournament contributions while keeping the
tournament. Entry removal excludes that configuration from future collection in the
list. Restore collection through **Rating settings → Excluded configurations**; an
explicit import is needed to restore removed historical contributions. **Rating settings** resets a category, resets a complete list, or deletes a
custom list. Pause and drain games before destructive cleanup. A separate durable
receipt cleans the live database and rotating recovery copies, survives interrupted
cleanup, and prevents an older backup from reviving removed ratings. Old games are
not automatically imported again after reset. Explicit imports are always a choice.

Text/forum, CSV and JSON exports include the reference and interpretation context.
Review text before posting; it is a timestamped snapshot, not a live web rating list.
