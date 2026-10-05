# Readable text exports

Choose **Text…** beside an export to preview a fixed snapshot. **Copy text** copies exactly the preview. Choose **Forum [code] block** for ProDeo-style forums or **Markdown code block** for Markdown posts to preserve aligned columns. **Save TXT as…** always saves plain UTF-8 text, without forum wrappers, using Windows line endings. The desktop app opens a folder/filename dialog; a browser follows its download settings.

Tables use a monospaced font. Long names wrap without truncation. The preview scrolls horizontally for wide tables and vertically for long reports. Missing measurements remain unavailable rather than becoming zero. Confidence levels, interval methods, perspectives and scope are stated where applicable. These exports format the recorded report values; they do not calculate a separate set of ratings.

| Location | Text contents and scope |
| --- | --- |
| Live standings → Text… | All participants, selected sorting and confidence method, W-D-L, points, percentages, Elo, CI, LOS and completed pairs. Official ranks remain unchanged by sorting. |
| Tournament report → Text… | The same committed snapshot as the HTML report: first 50 participants, all KO matches and stages, official failure details, result/attempt counts, opening-book and test conditions, recorded hardware/resources, engine/network evidence and fingerprints. The performance checkbox applies to both HTML and Text. Collapsed technical JSON is omitted. Use standings Text for the whole field. |
| Opening & color results → All openings · Text… | All recorded openings for the selected participant or White-side perspective, color totals and starting FENs; not restricted to the visible page. |
| Pool ratings → All ratings · Text… | Entire pool in the selected sort order, reference, confidence intervals, samples and fit status. The row search filter does not restrict this all-ratings export. |
| Crosstable / Head-to-head → Current page · Text… | Current page and search filter, with perspective and scope explicitly identified. Crosstable includes a full-name participant key. |
| Pairings & tiebreaks → Current review · Text… | Current review page and participant numbers. Unsaved edits and UI controls are excluded. |
| Engine library → Text profiles… | Entire library, reported identity, effective resource settings, independent control and UCI options. Local paths, arguments and file-related options are omitted by default; enable the checkbox for a personal configuration record. |
| Suites & benchmarks → Results → Text… | The saved result snapshot, including both official and archived attempts, accuracy, timings and measured NPS. |
| Starting positions → Text… | Named position, variant and FEN. |
| Graph header → Text… | The displayed samples, series labels, units and context. Time axes use UTC timestamps. Long histories may already be sampled for display. |
| Export PGN… → Save TXT as… | All current official games in the selected readable PGN notation, with selected annotations, saved with a `.txt` extension. Streamed from a consistent snapshot without loading the whole tournament into the interface. Use Compact or Moves only for easier reading. |

Text files are for reading and sharing; existing JSON, FEN and PGN formats remain available for importing into other software. Review any report before posting it, especially when explicitly including local paths. Ongoing games can produce newer results after the snapshot was prepared.

The examples in `exports/text-export-examples` contain synthetic test data, not real engine strength measurements. `standings.txt` and `games.txt` were saved through the new GUI buttons.
