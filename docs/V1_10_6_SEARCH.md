# Engine Arena 1.10.6 — rating search and focused-game watching

In **Rating Center → Search engines**, enter multiple names separated by commas
or semicolons. For example:

```text
Rebel; Chess System Tal; Stockfish
```

The list shows entries matching **any** term. Searches ignore letter case, keep
spaces inside names, and match partial names, engine families, associated profile
names, or configuration IDs. Empty and duplicate terms do not add duplicate rows.
Use each search label's **×** to remove that term, or **Clear search** to show the
full list under your remaining filters.

Choose **All versions** to show every recorded version matching those names.
**Best version per engine family** continues to select the best version within
each CPU-thread/GPU configuration. Other filters still apply. Searching changes
only the displayed rows: ratings, confidence, ranks, anchors, and the game
population used to calculate ratings remain unchanged. Paging and Text / forum,
CSV, and JSON exports respect the combined search.

In **Focused game**, the **50-move counter** checkbox now sits directly beside
the watching controls. It immediately shows or hides the counter and remembers
the choice for this workspace. It shares the existing **Board & clocks → Show
draw-rule counter** preference. When fifty-move claims are disabled, the counter
shows the automatic seventy-five-move limit instead. Hiding the counter does not
disable draw rules or change tournament adjudication.

**Follow winning games** finds a live game where either side has a sustained
engine-evaluated advantage. Defaults are a 2-pawn advantage, confirmed for 5
seconds, and staying with that game until it finishes. Reported mate scores
qualify too. Scores are estimates, not probabilities or guaranteed results.
Current or just-completed search scores are used; stale scores and score bounds
do not qualify on their own. Engines without scores cannot be selected this way.

In **Winning-game options…**, change the advantage threshold and confirmation
delay, or choose **Until its advantage fades**. That mode defaults to at least
30 seconds viewing and 15 seconds below the threshold before looking elsewhere.
Both timings are adjustable, and switching requires another qualifying game.
A larger score on another board never interrupts a game that still qualifies.

**Next winning game** chooses another current candidate immediately, bypassing
the confirmation delay and final-result hold. It cycles alternatives and keeps
the current board visible when none is available. Normal automatic switching
still honors **Finish hold**, so the official final result remains visible.
Manual game selection or **Follow engine** leaves winning-game watch. Recorded
move review and connection loss do not automatically switch boards. Watching
options are saved for this workspace and never affect the engines or results.

Includes 1.10.5's eight colorful themes, CI bounds/plus-minus presentation, and
independent rating/CI precision, as well as 1.10.4's TF display options.

Pause and drain running games, then close Engine Arena before installing.
