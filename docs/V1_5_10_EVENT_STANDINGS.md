# Engine Arena 1.5.10 — complete event overview standings

Private test update. Designed by Mark Young; programming by OpenAI Codex.

The event overview previously displayed only the first 12 engines in each stage
and directed users to Open stage for the complete standings. Every engine is now
accessible directly in the overview.

- Tables show up to 50 entries per page, with Previous and Next controls and a
  visible participant range and total. A 16-engine division includes all 16;
  a 64-engine qualifier has pages 1–50 and 51–64.
- Table height is bounded, with scrolling and a fixed column header, so a large
  roster does not turn the event window into an excessively tall page.
- Live refresh preserves each stage's selected page, table scroll and keyboard
  focus. Navigation to another season resets its table pages.
- Full season exports still include every place, independently of the page being
  viewed. The data interface returns bounded pages for large fields.
- Automatic tournament-list refresh from 1.5.9 is included.

These are display and read-only reporting changes. Event progress, engine
assignments, clocks, results, rating calculations and opening sequences are
unchanged. The installer has not been published or installed automatically.

Pause and drain, close Engine Arena normally, install this update, then reopen
and resume the existing event.
