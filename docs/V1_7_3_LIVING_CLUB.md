# Engine Arena 1.7.3 — living chess club

Private update for review. Designed by Mark Young; coded with OpenAI Codex.

Choose **Live chess club · full 3D** in board appearance. Four distinct seated
players now reach for, grasp, carry and place chess pieces before pressing the
clock beside their board. Castling moves the king and rook separately. The two
illustrative tables play an opening and then return through it by hand as an
opening study; pieces do not teleport back to the starting position.

Two additional individual visitors arrive through a real doorway, follow curved
aisle routes, stop to watch the games, study the analysis board or browse the
library, and leave. Each of the six people has a separate fitted full-body model,
face/build, outfit treatment and hair. No person is instantiated twice. Walking
feet use room-space stance targets, and players lean toward their reach without
stretching their arms. Thinking pauses, gazes and movement phases differ.

The wall clock follows the computer's local time, including its timezone and
daylight-saving settings. **Use computer time for daylight** is enabled by
default for this room. Window light fades through dawn (06:00–08:00), daylight,
dusk (18:00–20:00) and night, with warm interior lighting at night. These are
local-time visual transitions, not calculated astronomical sunrise/sunset or
live weather. Disable the option to choose a manual lighting preset. The wall
clock still shows local time. The chess clock beside the foreground board still
shows actual game time, independently of the room wall clock.

Quiet activity shows two seated players. Club and Busy show four players plus
the arriving/departing visitors. People, background games, room motion and sounds
retain separate controls. Hidden/offscreen boards pause activity. An otherwise
still, visible club updates the wall clock once per second instead of running a
continuous high-frame-rate animation. Photo mode freezes the room clock during
capture. Existing photographic environments remain unchanged.

## Checks

- Unit coverage: legal opening/castling choreography, continuous hand paths,
  no resetting-piece teleports, placement before clock presses, civil-time hands,
  smooth day/night boundaries and display preference validation.
- Actual GLB pose/route acceptance: six unique models, one matching rest pose per
  model, 6,240 samples across 780 seconds, hand contact during grasp/carry/release
  and clock presses, visitor separation, open doorway at threshold crossings.
- Graphics acceptance: Focus/Player room controls, 8 languages, actual game
  clocks, 4K photographs with/without depth blur, warmed GPU resource stability,
  frame limits, hidden/offscreen pause, reduced motion and manual lighting.
- Existing Player workflow: mouse click/drag, promotion, completion, PGN and
  challenge games. Disposable data only; production tournaments are untouched.

These are stylized background characters and authored illustrative routines,
not autonomous human simulations or motion-capture actors. Laptop performance
and artistic approval remain part of the owner's review.

## Artwork and rebuilding

CC0 MakeHuman graphical inputs and MIT Three addons retain their provenance and
notices. `scripts/build_club_cast.py` creates the six individually fitted models;
`scripts/sync_club_assets.py` copies the room/cast to the offline app. The builder
now clears old armature actions between characters, preventing a standing visitor
from receiving a preceding character's seated pose. Garment clearance also
improved for shoulder movement. No additional software or download is needed
at runtime. The local architecture preview uses the same motion module.
