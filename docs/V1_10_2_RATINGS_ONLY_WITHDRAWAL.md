# Engine Arena 1.10.2 — fair standings after RR replacements

Designed by Mark Young. Coded with OpenAI Codex.

Paused, fully drained standalone round robins now offer two ways to handle
withdrawn entrants' completed games. Historical rating records, attempts and
original PGNs are preserved under either choice.

## Equal games for the final field

1. Pause and drain; wait for every active game to finish.
2. Open **RR roster… → Withdraw engines from future games**.
3. Choose **Keep ratings only; exclude from tournament standings** (the dialog's
   initial choice). Select entrants to withdraw and any new profiles to add.
4. Choose newcomer scheduling. **Catch up first** prioritizes new entrants until
   their average counted game total catches up with the incumbents.
5. Preview the changes. Check excluded completed games, canceled unplayed games,
   added games, active field size and the final counted games per engine.
6. Save, review the revised standings, and resume when ready.

The exclusion applies to both sides of every game involving a withdrawn entrant.
Tournament points, wins, tiebreaks, pair statistics and tournament ratings use
only the revised field's games. Games between remaining entrants keep their
identities, results and opening assignments. Replacements have new identities
and earn their own results; they never inherit points from withdrawn entrants.

All previous keep-results withdrawals are also excluded when this option is
chosen. If there are previous withdrawals, the dialog can convert their results
without withdrawing any additional engine. The preview is required before saving.
There is no automatic change to an existing tournament merely by installing.

In a 400-engine double round robin with one opening pair per matchup, replacing
seven entrants leaves 400 active engines and 159,600 counted tournament games:
798 per engine. Previously played excluded games remain additional historical
rating evidence, so Rating Center may contain more games than the standings.
Counts remain provisional and unequal while the schedule is still running.

## Keep all points instead

**Keep results in tournament standings and ratings** retains the 1.10.1 behavior.
Played games still count for both sides, withdrawn rows remain labeled, and only
future games are canceled. Final game totals can differ under this policy.

## History and safeguards

Original standings and PGNs remain available through **Previous roster revisions…**.
The normal tournament report and on-demand PGN export show the revised competition.
The automatic append-only PGN archive also retains previously saved excluded games.
Existing Rating Center records retain the same engine identities and results,
including forfeits. This option does not create ratings for previously unrated
games or reset the rating list. Replay cannot restart withdrawn matchups.

Changing the policy invalidates the preview. Saving checks the roster, result
revision and fully drained state again, and commits the revision atomically.
Roster changes remain paused. Event stages and other tournament formats are
outside this feature. Install over your existing version after closing the app.
