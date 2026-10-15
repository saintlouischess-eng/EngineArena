# Engine Arena 1.5.2 — development update

Designed by Mark Young. Programming by OpenAI Codex.

Rating Center now shows a sortable **Rank** column. Ranks follow descending Elo
within the selected time category and evidence filters. Name searches, table
sorting and page changes preserve those ranks. Equal estimates share a rank
(1, 1, 3); unavailable estimates show a dash. Calculations use full precision,
so two ratings rounded to the same displayed value can still have different ranks.

All Categories shows each category's rank alongside its Elo, without combining
different time controls into one ranking. Text/forum, CSV and JSON exports carry
the same ranks. Rating calculations, anchors and game evidence are unchanged.

The reference-anchor selector now has Previous/Next buttons and a page count.
The selected engine stays available by its full name, even when it is outside
the current page or search results. Searching does not clear the selection or
change the reference rating. All eight interface languages are supported.

Includes the GPU-aware Rating Center changes from 1.5.1.

To update: pause and drain the running event/tournaments, wait for zero active
games, close Engine Arena, run the installer over the existing installation,
then reopen and resume. Existing results, settings and rating anchors are retained.
This is a private development build for owner testing, not a new public release.
