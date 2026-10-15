# PGN export choices

The development build's **Export PGN…** dialog offers four starting points:

| Preset | Headers | Move comments |
| --- | --- | --- |
| Clean games | Basic game, result, time control and available opening information | Moves only |
| Annotated games (default) | Useful game headers, opening book filename and engine identities | Compact score/depth/seconds; one end-of-book marker |
| Engine testing | Engine resources, independent controls, network evidence and game/attempt identifiers | Tagged evaluations, depth, elapsed time, clocks, nodes, NPS and selective depth when recorded |
| Complete archive | All available headers, including encoded engine/tournament settings | All recorded measurements and individual book markers |

Choose **Choose headers** to enable individual optional tags by category. **Essential headers** clears optional choices; **Testing headers** restores the testing set without changing move annotations. Custom choices are remembered after a successful export, or by pressing **Remember choices**. Missing measurements and metadata remain absent.

**Formatting and labels** controls opening markers, movetext width, evaluation perspective, profile versus reported engine names, date time zone, and optional Event/Site labels. Labels affect the export only. Profile names are the default because they distinguish engine clones with different configurations. UTC dates are the default; local dates use the exporting computer's time zone. UTCDate/UTCTime always remain UTC when selected.

The preview renders the first current official saved game using exactly the selected options. It updates after changes and can be copied. Very large previews are shortened; full exports are not. A tournament with no official result displays an explanatory message instead of an invented sample.

**Save PGN as…** and **Save TXT as…** both use the desktop Save As dialog. TXT contains the same readable PGN text with a `.txt` extension. The desktop streams to a temporary sibling file, then flushes and replaces the selected destination only after success. Browser use employs its file picker when available, otherwise normal browser downloads.

## Game integrity and interpretation

- Event, Site, Date, Round, White, Black and Result remain present and ordered first. Other tags are alphabetically ordered. Header quotes/backslashes are escaped and embedded control characters removed. PGN tag names and chess notation remain unchanged when the interface language changes.
- FEN/SetUp/Variant and any recorded opening-history warning remain when needed. Verified recorded opening moves are included; an unknown route to a FEN is never invented.
- Special or unequal controls retain the side-specific time/search controls even when optional headers are cleared. Node-only controls explicitly say there is no chess clock. KO games use their recorded playoff controls.
- Fixed time per move now uses a one-move period (`1/seconds`) plus its explicit search-control description. The previous `*seconds` header incorrectly described an hourglass clock.
- Compact evaluations default to the moving engine's perspective, matching the existing readable format. Tagged `[%eval]` values always use White's perspective. The ScorePerspective tag is retained whenever evaluations are selected. TimeControl is retained for elapsed/clock annotations.
- A move number stays attached to its SAN when lines wrap. Long individual comments and header values are not split merely to satisfy the chosen movetext width.
- Only current valid official attempts are exported, once per scheduled game, in game-number order. Replacements supersede earlier results; diagnostic and interrupted attempts remain in history and their original records.
- Settings in Complete archive are base64-encoded JSON, not encrypted. They can include local paths and launch arguments. The simpler presets omit these large values.

Existing automatic PGN files are not rewritten. Future automatic journal entries use testing headers and attempt identifiers, compact comments according to the tournament's annotation setting, and one end-of-book marker. Full settings and recorded measurements remain in the database. A fresh export applies the new presentation choices to an existing tournament without changing its records.

Readers use a consistent read-only SQLite snapshot and bounded chunks (16 games per streamed chunk), separate from the tournament worker. Full exports still take time proportional to the games and moves; the dialog preview renders only one game.

Header ordering and escaping follow the [PGN specification](https://www.saremba.de/chessgml/standards/pgn/pgn-complete.htm). Annotation handling uses [python-chess PGN support](https://python-chess.readthedocs.io/en/latest/pgn.html); importing software may display only a subset of optional measurement tags.

## September 26 validation

- Actual completed tournament `54680c1e358646c98069c7034d1ac470`: all **76,500** official games exported using Clean games. Every exported White/Black/result was reconciled with the ordered official records. Output: `exports/Engine comparison - 76500 games - clean.pgn`, **88,499,141 bytes**. Export plus header reconciliation took **393.54 seconds** on this workstation. SHA-256: `ddb0704c191cac6e6326f813175558d043d97a988b09664d37188939e0bd16e2`.
- **68 distributed real games × four presets = 272 round trips**, checking parser errors, result and final board against stored moves. Four-game samples for each preset are in `exports/pgn-presets/`. This sample validates complete movetext parsing; the full-export check reconciles headers, rather than independently replaying every game a second time.
- Regression coverage includes opening reconstruction, Chess960, node-only and asymmetric controls, recorded KO tiebreaks, replacements/diagnostics, annotation subsets, header escaping, invalid choices, preview/stream parity and the automatic journal.
- Full regression suite: **344 passed** before the final fixed-time header correction. The final related suite passed **85 tests** afterwards, including the new correction test; all **41 JavaScript tests** passed. Existing aiohttp AppKey migration warnings remain.
- Isolated browser checks cover all presets, custom headers, remembered choices, save/cancel bridge requests and actual HTTP export bytes. All eight languages were checked at 900 px window width with 24 px UI text: no dialog overflow or missing captured translations. The native file picker was simulated in this automated browser check; the desktop and sensor projects were separately rebuilt successfully. NuGet's vulnerability feed was unavailable (NU1900); no dependency was changed.
- Reproducible scripts: `scripts/validate_pgn_presets.py`, `scripts/export_clean_completed_pgn.py`, `scripts/validate_pgn_dialog.cjs`. Evidence: `test-output/pgn-presets-real.json`, `pgn-clean-full.json`, `pgn-dialog-ui.json`, `pgn-presets-focused.xml`, `pgn-polish-full.xml`.

All work is local development. The installer and GitHub release remain unchanged.

## Automatic shared output (1.5.12)

**Automatic PGN…** adds a continuing output destination, independent of one-time Save As. See [automatic PGN workflow and recovery](V1_5_12_AUTOMATIC_PGN.md).
