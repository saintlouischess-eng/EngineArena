# Engine Arena 1.4.2 — competition desk

Private installer for owner testing. This update includes the 1.4.0 Season Manager
and 1.4.1 setup improvements. It has not been published to GitHub.

## Follow a season

Open a competition in **Events & leagues**. **Season overview** now shows the
champion or current phase, championship score, division tables, promotion and
relegation, recorded champions and next steps. **Latest** follows the current
season automatically; select a season number to inspect its history.

Live division places are provisional. They become official only when the event
records advancement, including any required placement playoffs. Playoff points
are never added to the division table. Final results decide the championship;
division places retain their own results. Stage progress refers to that stage's
current schedule; tiebreaks can extend it. Future stages may not yet exist.

Use **Open stage** for the complete standings, boards, reports, games and PGNs.
The overview shows eight stage cards per page and twelve entrants per card to
stay responsive. Existing stage records remain in **Stages & records**.

## Follow an engine

Select an engine name or open **Engine careers**. Search covers both current and
previous version names. Careers are scoped to the selected competition, with
title seasons, W-D-L, recorded versions, division/stage history, original playing
conditions and rivalry results. Approved version upgrades keep the entrant's
identity. A new entrant receives a separate career even if it uses the same name.

Totals include only official results in valid stages. Diagnostic replays and
superseded stages do not contribute. Original attempts remain available through
the existing history controls. Replacing an official result updates these views
through the normal result and dependency handling.

Career W-D-L describes the recorded games. It is not a rating across changing
versions, opponents or time controls. No combined career Elo/CI/LOS is generated.
Byes can contribute stage points, but never played-game totals or rivalry games.
The original version names remain attached to historical stages.

## Share the results

**Season summary** offers **Forum recap** and **Complete season tables**. Both
contain a fixed, timestamped snapshot. The recap includes the champion, final,
division leaders, recorded movements, engine changes and climbs from the original
stage seed. Seed movement is not presented as a measured improvement in strength.
The complete version includes every stage row, W-D-L, points and recorded default
stage conditions. Open stage reports for detailed per-engine conditions and ratings.

Use **Copy / save summary…** to review plain text, a forum `[code]` block or a
Markdown code block, or save a UTF-8 TXT file to your chosen location. Nothing is
posted automatically. **Refresh snapshot** explicitly updates the preview.

## Compatibility and installation

The views work with saved legacy leagues as well as new Season Manager events.
They read existing aggregates and snapshots; they do not change pairing rules,
engine versions, clocks, results or historical attempts. Large game logs are not
scanned to build the season dashboard. Data is cached only in memory and refreshed
after database changes. Deleting an event also removes it from these views.

Pause and drain any active games, close Engine Arena and run the 1.4.2 installer.
Reopen your completed league to inspect the new views immediately, or create a
new season competition for the next full test. Designed by Mark Young;
programming by OpenAI Codex.
