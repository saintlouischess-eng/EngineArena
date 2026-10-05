# Profile opening books and live reliability

These features are in the local development build. No installer or GitHub release was published.

## Comparing two books with the same engine

1. Add the engine, then clone its profile. Give the copies clear names, such as **Stockfish + UHO** and **Stockfish + Noomen**.
2. For each copy, open **Configure → Engine move book → Import PGN / BIN**. Choose that copy's book, move selection policy and maximum depth; save the profile.
3. Select both profiles and create a head-to-head match. Leave **Use each profile’s engine move book** enabled. Choose **Initial position** for the common tournament opening source. Enable color reversal for balanced starting colors.
4. Review the scheduled total, resource limits and time control, then start.

Each profile chooses book moves on **its own turns**. This does not alternate whole starting positions from two books. For example, White can choose `1. e4` from its book and Black can answer `1... c5` from a different book. A profile permanently switches to engine search for that game at its first book miss or depth limit. There is no later book re-entry. Both engines still receive the actual position and move history when searching.

The common opening source is separate: it supplies the initial board to both participants. If used alongside profile books, their first lookup occurs at that supplied position. Matching positions are required; no historical moves are invented for FEN-only input. Ratings then measure **engine + book configurations**, rather than engine strength alone. Color reversal repeats the common starting position; subsequent per-profile book choices need not match.

## Import and selection

- PGN mainlines become a position-to-moves index. Repeated moves at a position increase their frequency weight. Variations and evaluations are not used as weights. Position-only files without moves cannot serve as move books; use them as common starting positions instead.
- Polyglot BIN entries retain their weights. Illegal moves and zero-weight entries cannot be selected. Polyglot castling notation is normalized through legal board parsing.
- **Weighted by book frequency** samples proportional to weight; **Equal chance per move** samples uniformly among available legal moves; **Highest book weight** selects the largest weight, with seeded tie selection.
- Depth is in plies from the game's recorded move number: two plies are one full move. Six plies means three full moves; zero is unlimited. If a common opening has already reached that depth, the profile searches immediately.
- Selection uses the tournament seed, game number, profile slot, book hash, position and ply. Retrying an unchanged game reproduces its book choices; search results after leaving book may differ.
- The immutable compiled book is stored once in transactional SQLite, shared by profiles and tournament snapshots, and included in normal recovery backups. Moving or deleting the external input file does not break a saved tournament. Importing the same bytes reuses the same book.
- Import and book deletion require idle engine processes so a large index transaction cannot delay move commits. Parsing runs outside the chess event loop with disk-backed indexing. There is no arbitrary position count cap. The compiled index consumes database and backup storage; its size can exceed the input BIN file.
- **Delete unused book** refuses deletion while a saved profile, tournament or experiment references it. Select no book and save a profile to remove its reference. Existing tournaments retain their snapshots. Normal storage optimization can reclaim freed database pages; rotating backups keep their recovery snapshots under the existing retention policy.

## Clocks and records

A GUI-supplied book move consumes zero engine search time and no configured per-move overhead. It advances move counters, earns increment and can cross a time-control stage. Startup/readiness/cleanup watchdogs still apply. No fake evaluation, depth, nodes, or elapsed-search annotation is generated for book moves. Pure-node games still send only `go nodes N` when the engine must search.

All actual played book moves are committed through the ordinary move transaction and retained in PGN. Annotated/testing/archive exports can mark their source; clean exports remain comment-free. Selected clock annotations retain genuine post-move clocks. Optional opening headers include WhiteBook/BlackBook and, in testing/archive, the book hash, selection policy and maximum ply. Engine technical reports exclude these book moves from search averages and show their separate count. Reports identify each profile's saved book and whether profile books were enabled.

Recovery preserves committed results and archives interrupted attempts. Only unfinished games restart from their saved common opening, using their saved books and deterministic selection. Editing a library profile does not change a previously created tournament.

## TF in live standings

**TF = time forfeits across all non-diagnostic competition attempts.** It counts original, automatic retry and replacement attempts, including attempts in later-invalidated rounds. This makes time-management problems visible even after a successful replay. Each losing profile is counted once per attempt; draws and interrupted games are not time forfeits.

Click the sortable **TF** count to open **Engine reliability**. The detail window separates the cumulative count from **current official losses**, lists original attempts with their details, and opens the exact attempt selected. It also offers separate filters for crashes, hangs, illegal moves, startup/readiness timeouts and protocol failures. The standings counter updates with live results; the detail window has Refresh and paging.

W-D-L, points, Elo, confidence intervals and opening-pair results still use current official results. TF history does not add losses to those calculations. HTML/TXT reports and standings CSV/JSON/text include TF and official TF with the scope explained. Older workspaces build the small reliability aggregate from preserved attempts once; routine live updates are incremental. Deleting a tournament removes its counters with its other data.

## Verification

- Complete Python regression suite: 357 passed before the final additional scale/fallback checks; 42 JavaScript tests passed.
- Final focused PGN/book/reliability suite: 36 passed, including the additional tests. Language checks: 2,809 messages in each of eight catalogs, no missing keys/placeholders.
- Actual two-profile UCI tournaments verified independent books, engine fallback, complete color pairs, node-only commands, fractional increments and staged clocks. Technical averages and PGN moves/source/clock annotations checked.
- Forced worker process exit retained a completed game and an unfinished committed book move. Recovery archived the interrupted attempt and reproduced the next attempt's book choice without its external source file.
- Original/automatic/replacement/diagnostic/self-play/invalidated attempts, migration and restart TF accounting checked. Repeated finish calls do not double-count.
- A 50,000-position BIN imported and queried through SQLite; profile JSON remained under 1 KB. Active references blocked deletion. Disabled books and permanent exit at a first miss were verified.
- Headless Edge exercised TF sorting, original-attempt navigation, PGN import, settings persistence, guarded deletion, the tournament enable switch and all eight language layouts. Screenshots inspected after adding a dedicated book settings section.
- Read-only reconciliation of the existing 76,500-game tournament matched the raw timeout attempt counts; the snapshot and comparison took 0.383 seconds. No real tournament records or automatic PGN files were changed.

Evidence: `test-output/books-reliability-regression.xml`, `books-pgn-final.xml`, `books-final.xml`, `reliability-real-readonly.json`, and the preview screenshots. Tests use isolated workspaces. Sustained real-engine testing of the new book comparison feature remains for the next test run; these checks do not establish zero GUI overhead.
