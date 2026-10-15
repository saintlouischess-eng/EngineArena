# Engine Arena 1.9.7 — release-check candidate

Designed by Mark Young. Coded with OpenAI Codex.

Opening moves reviewed in Focused Game now display their opening move number
(for example, `Opening · 1. e4`) instead of a negative engine-relative ply count.
The original opening history, game moves, replay selection and live following
are preserved. Labels use the selected interface language.

Includes the completed-event summary and Quick match corrections from 1.9.6.
Updates the bundled multidict dependency to 6.9.1, which fixes the reported
items-view set-operation memory leak (GHSA-54p9-h82j-f925).
When several tournaments have the same creation timestamp, Add all ready now
keeps their creation order instead of breaking ties using random IDs. Existing
saved queue positions are unchanged.
This is a private release-check build; publication requires owner approval.

Close Engine Arena before installing over the existing installation. Saved
engines, games, events and ratings are retained. No replay or data reset is needed.

The release audit covers backend and interface regressions, numerical statistics,
real-engine formats, failure/recovery, Player Arena, exports, storage and packaged
application workflows. Exact results and remaining hardware/installation limits
are recorded separately in the local release audit, rather than treating a short
automated run as a guarantee for every Windows PC or graphics driver.
