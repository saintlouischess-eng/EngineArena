# Engine Arena 1.11.1 — Broadcast appearance and readability

The broadcast studio now saves its own board finishes and TV-friendly appearance.
Normal tournament workspaces remain independent of the broadcast.

- Charcoal and warm gold joins Ocean, Emerald and Burgundy.
- Choose maple, ash, golden oak, walnut, rosewood or ebony independently for light
  and dark squares, or retain the theme's plain colors.
- Lighten dark squares from 0 to 60 percent without changing the light squares.
- Warm TV preset: charcoal, ash/rosewood with 28 percent lightening, Classic Bold,
  a four-pawn evaluation range and a 150-second ticker. Preview before applying.
- Ticker text remains unchanged throughout a complete pass. New results appear
  on the next pass, after the previous line has moved off-screen.
- Diamond separators have clear spacing. Scores and endings use the theme accent.
- Scroll duration accepts 20–600 seconds; a larger value means slower movement.
- Evaluation numbers sit on the favored color's end, follow board orientation,
  use contrasting badges, and show a centered dash when no score is available.
- Evaluation range is configurable independently of the regular workspace.

The broadcast remains a read-only consumer of tournament data. These changes do
not create analysis engines, alter results or modify tournament settings.

For OBS, use a 1920 × 1080 browser source at 60 FPS and a 30-FPS encoded stream.
This recommendation concerns the lightweight 2D broadcast source, not the 3D room.

For installation, finish the stream and pause/drain games at a convenient time.
Close Engine Arena and restart its independent broadcast service after updating.
An already-running service deliberately stays running; it does not hot-upgrade.
If custom OBS CSS was used for an earlier preview, first save equivalent choices
in the new studio, then remove that override so the native controls can take effect.
