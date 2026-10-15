# Engine Arena 1.7.1 — Live environment

Private update for Mark Young to review. Designed by Mark Young; coded with OpenAI Codex.

## Turn it on

In the focus board, open **2D / 3D**, choose the 3D board and find **Live environment**.
Check **Bring the room to life**, choose an activity level, then **Apply**.
In Player Arena, select **3D board → Appearance…** to use the same room settings.
Both boards remember these preferences. Live environment and room sound start off.

**Quiet session** seats two background players at one table. **Club session**
seats players at up to two tables. **Busy chess evening** uses the room's full
layout and adds a walking spectator. The championship hall has five secondary
tables, the club three, the studio two and the study one.

People, decorative background games, subtle room movement and distant chess
sounds have separate checkboxes. Sound has its own volume (0–50%), independent
of game move sounds. The camera still supports orbit, zoom, height, saved views,
and presentation tours. Try **Room view** to see the surroundings more clearly.

## What changes

Each existing room gains a different arrangement of chess tables, smaller wooden
sets, digital clocks, scoresheets, pencils, cups, padded chairs, analysis boards,
chess-club signs, bookshelves, lamps or championship fixtures. A modeled floor grounds the furnishings in 3D while the photographic room
remains visible. Background players breathe,
look toward the board and gesture during illustrative games; busy rooms have a
spectator walking a smooth path. Plants and lamps have restrained ambient motion.
The scene figures are lightweight background characters, not photographic actors.

The background boards repeat a legal illustrative Ruy López line. They are scenery,
not tournament games or live representations of other engines. They never start
engines, use tournament scheduling slots, write moves/results, change ratings,
or enter PGN exports. No network access is needed for room assets at runtime.

## Performance and accessibility

The existing 15/30/60 FPS limit applies to live rooms on both boards. Static
furniture is combined into shared draw batches. Character assets load only when
live rooms are first enabled; switching among rooms reuses a bounded cache.
Turning the feature off stops its animation. Hidden/offscreen boards suspend
animation; Player Arena releases its renderer when leaving the workspace.
Reduced-motion preferences keep the furnished scene still. Photo previews freeze
the room with the board; 4K photo export remains available.

Graphics quality and room activity can be reduced independently. Live scenery
uses additional CPU/GPU work while visible; switch it off when display overhead
matters to an engine test. A frame limit is a maximum, not a guarantee of that
frame rate on every machine.

## Validation

Isolated source and packaged acceptance cover all four rooms, repeated switches,
independent toggles, the opt-in asset path, advancing animation, reduced motion,
hidden/offscreen suspension, both board workspaces, saved settings, eight UI
languages and 3840 × 2160 image export. Player Arena's real mouse workflow is
also checked, including 2D/3D click and drag, underpromotion, saved PGNs and
challenge series. Local evidence is recorded in test-output; this update does
not install itself or publish a release.

CC0 head/hair/skin attribution and build provenance are in `THIRD_PARTY.md` and
`ThirdParty/MakeHuman`. The scene arrangement, clothes, furniture and animation
are Engine Arena artwork. The existing room photographs retain Poly Haven credit.
