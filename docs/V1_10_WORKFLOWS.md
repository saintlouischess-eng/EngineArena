# Engine Arena 1.10.0 — tournament and viewing workflows

Designed by Mark Young. Coded with OpenAI Codex.

This candidate includes the full approved workflow update and the 1.9.13 fix for
intermittent empty/slow large-list ratings. Rating mathematics, confidence
intervals, engine identities and existing anchors are unchanged.

## Watching games

- **Follow engine…** follows the exact profile in the selected tournament. Its
  current game stays selected; its last board remains while it waits. Choosing a
  game manually ends following.
- **Finish hold** shows the committed last position, result and termination before
  switching. Choose zero for immediate switching, or up to 60 seconds. **Next
  game** skips the hold. Engine play never waits for a viewer.
- Live boards have **Recent finishes**. A saved-result lookup covers games ending
  between display polls. A disconnected display does not invent results.
- **Best-move arrow**, initially off, shows the current engine's legal primary-PV
  move in 2D/3D, with configurable delay. It clears on position/search changes,
  review and game end. It starts no extra engine and supplies no Player Arena hint.

## Results and appearance

- Independent saved **Text** sizes for standings, attempts, engine library,
  Rating Center and dense result dialogs. Floating/expanded panels retain their
  preferences. Reset affects only that panel's size.
- Optional **Tiebreak values** and **Ranking explained…** show actual criteria,
  values and seed fallback. Points are compared first; bracket/ladder placement
  remains format-specific. Display sorting never changes competition rank.
  Values are provisional until play ends. Reports/exports include the explanation.
- Seven interface themes: Midnight, Daylight, Charcoal, Deep Blue, Forest, Warm
  Parchment and High Contrast. Preview, four accents, optional Windows light/dark
  appearance and named-layout persistence. Board finishes/rooms stay independent.

## Round-robin rosters

**RR roster…** adds entrants to a paused/drained or completed standalone RR.
The preview shows retained games, added games and the new total.

- **Catch up first** prioritizes newcomers until their average completed plus
  active game count reaches the incumbents, then uses normal scheduling.
- **Interleave** alternates newcomer priority with ordinary scheduling.
- **After the existing schedule** uses the ordinary existing queue first.

Resource admission limits always apply. Blocked engines do not prevent eligible
matchups using available capacity. Additions are saved paused. Old games,
openings and engine snapshots remain unchanged. New profiles use their current
saved settings; check threads/hash/time controls before saving. Opening assignment
follows the recorded policy; shared suites, random selection or exhausted books
can deliberately repeat positions.

Completed standalone RRs support withdrawal/replacement. Revised standings exclude
a withdrawn entrant's games for both sides. A replacement has a new identity and
plays its required matchups. Old standings, exact official attempts, original PGN
export and historical Rating Center evidence remain available. See **Previous
roster revisions…**. Revised tournament standings and all-history ratings can
therefore intentionally describe different game sets. Stale previews are rejected.
Version 1.10.1 adds ongoing withdrawal after pause/drain while retaining all played
results; see V1_10_1_RR_WITHDRAWAL.md. Swiss/KO and event-stage roster changes
remain excluded.

## Durability and traceability

- **Activity history…** and **Tournament activity…** record observed sessions,
  play/wait/pause/drain states and normal/unknown shutdowns. Tracking starts with
  this version, sampled about every ten seconds. Sleep, offline time and gaps are
  not uninterrupted uptime. Older run sessions remain in existing reports.
- Presets have a confirmed **Delete** action. A deleted starter preset does not
  return at next launch. Saved tournament conditions remain unchanged.
- Rating Center links profile labels to immutable configuration IDs. Rows, search
  and anchor selectors share collision-safe short IDs. Details show full IDs and
  settings. CSV/text/JSON and optional detailed PGN references expose provenance.
  Renaming a profile never transfers its anchor or changes an old configuration.
  Historical associations are backfilled only from exact saved game-side records;
  unavailable evidence is labeled explicitly.

## Installation and validation

Pause and drain, close Engine Arena, then install over the existing version.
Resume the saved tournament afterward. No reset is needed. This private candidate
has not been published automatically.

Validation uses disposable workspaces: lifecycle, rollback/restart, PGNs, retained
ratings, three browser workflow passes, real Stockfish/Berserk games, 2D/3D arrows,
small/expanded/floating panels and theme persistence. The owner's installed data
was not used for mutation tests or bundled. These checks do not replace extended
hardware/driver stability testing. New UI strings use the existing localization
system with English fallback where translations are unavailable.
