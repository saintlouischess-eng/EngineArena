# Engine Arena 1.12.4 — broadcast readability and OBS startup

Local update for installation and testing; no public release is implied.

- Both engine ratings appear in result/upset ticker headlines, including engines
  below the leaderboard's top 20. Bold rating labels remain readable against the
  selected theme. Missing or ambiguous ratings show `Elo pending`.
- Upsets explicitly describe how much higher the beaten opponent was rated.
  This number is a rating gap, not a gain awarded for that result.
- Every broadcast standings and Rating Center row and heading is bold.
- The 2D thinking arrow is slightly slimmer and softer. Its selected color and
  delay, including zero seconds, are retained.
- Broadcast Designer can open OBS at verified Normal Windows priority. Existing
  OBS instances are reused; no streaming or recording is started automatically.
  Custom installation paths are supported. An isolated Windows process test
  covers startup from a Below Normal parent and survival after the parent exits.

The ticker uses existing cached ratings and exact recorded profiles, without
additional rating fits. A visible scrolling pass finishes before new text is
displayed. Ratings, standings, games and tournament scheduling are unchanged.

Pause and drain, stop the live broadcast, and close Engine Arena before installing.
Then reopen Broadcast Designer. If an old broadcast helper is still running,
accept its offered restart after stopping the stream. OBS retains its source URL.
Use **OBS program output & switching → Open OBS · Normal priority** for future
launches; **Check OBS priority** confirms the actual running process.

See [Broadcast Designer](BROADCAST_DESIGNER.md) for all controls and data limits.
