# Engine Arena 1.10.5 — color themes and rating presentation

## More colorful themes

Open **Interface themes…** and choose Ocean Blue, Emerald Club, Royal Violet,
Burgundy, Mint Lagoon, Lavender, Peach & Copper, or Sky Blue. These palettes color
the workspace surfaces and navigation, with contrasting text. All seven earlier
themes remain available. Existing accent and Windows appearance options remain.
The preview now reflects the selected theme's light/dark accent colors correctly.
Theme changes do not change chessboards, pieces, rooms, or engine settings.

## Rating and confidence interval display

Live Standings and Rating Center each have three saved controls:

- **CI display:** Full bounds (for example `2,980 – 3,020`) or Plus / minus (`±20`).
- **Rating decimals:** 0, 1, or 2 decimal places.
- **CI decimals:** 0, 1, or 2 decimal places, independent of the rating precision.

The two workspaces retain separate choices. Defaults remain full bounds and one
decimal place. Asymmetric intervals keep their two offsets (`−18 / +24`), rather
than showing an incorrect symmetric margin. Unbounded intervals retain their
full bounds. Missing estimates stay unavailable; a fixed anchor can show `±0`.

These are display choices, not changes in statistical accuracy. Underlying
ratings, confidence levels, interval methods, sorting, official ranks, and saved
evidence remain unchanged. Changing a display control redraws cached rows without
requesting a new rating fit. Data exports retain their existing numeric precision.
Live Standings continues to show Elo relative to sampled opposition; Rating
Center continues to show the selected anchored rating scale.

Includes the 1.10.4 **TF counts** choice: **Official results** (default) or
**All attempts**. Historical failures remain available for inspection after a
replacement result changes the official standings.

Pause and drain running games, then close Engine Arena before installing.
