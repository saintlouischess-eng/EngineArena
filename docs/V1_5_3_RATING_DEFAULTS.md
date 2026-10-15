# Engine Arena 1.5.3 — Ratings preserved by default

Designed by Mark Young. Programming by OpenAI Codex.

This private development update makes continuous rating collection and retention
the default throughout Rating Center.

- The main rating list automatically collects newly played official games, as
  before. New custom rating lists now also start with collection enabled; their
  creation dialog shows the checked option.
- Deleting a tournament, a whole event, or multiple events now starts with
  **Keep compact Rating Center evidence** checked. Results already collected by
  a rating list remain available when future games are rated. Their engine
  identities, conditions, opening-pair evidence and applicable anchors survive.
- Moves, PGNs, diagnostics, tournament settings and event records still undergo
  the normal deletion and disk cleanup. Retained rating evidence is compact;
  it does not keep a second copy of the games and engine logs.
- Omitting the retention option in a deletion request also preserves evidence.
  Deliberately unchecking it removes the relevant rating history. Rating Center
  still provides its separate reset and removal controls.

Existing deliberate collection opt-outs stay off after updating. New list
creation does not automatically import old games. Previously uncollected games
must be imported before deleting their tournament; this update cannot recover
history that was already erased.

Pause and drain active games, close Engine Arena, install this update, and reopen
to resume. Existing settings, official results and engine profiles are preserved.
This installer has not been published on GitHub.
