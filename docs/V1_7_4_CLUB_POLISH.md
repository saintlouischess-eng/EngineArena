# Engine Arena 1.7.4 — private club polish

Designed by Mark Young; code and original scene artwork developed with OpenAI Codex.

This private update refines the standalone **Live chess club** in both Focus
Game and Player Arena. It does not change tournament execution or results.

## People and movement

- Seated players have corrected anatomical elbow planes, forearm twist,
  restrained wrist flexion, softer grasp/clock paths and closer seating.
  Resting hands sit beside the near edge of the board.
- Four different players: Arthur, Mei, Daniel and Elena. Elena now has an older
  face, glasses, light ponytail and tailored outfit, clearly distinct from Mei.
- Jonas and Nora have separate builds, faces, hair and complete outfits.
- Six occasional cameo visitors: Magnus Carlsen, Fabiano Caruana, Hans Niemann,
  Bobby Fischer in his 1972 era, Hikaru Nakamura and IM Levy Rozman. Faces,
  proportions, hair, glasses and clothing are individually authored. These
  are artistic likenesses, not scans or exact digital doubles.
- Eight visitor identities rotate through two roaming places in a shuffled
  order. A person never appears twice simultaneously. Visitors walk in,
  watch games, browse or study the wall position, and leave through the door.
- Walking has a more ordinary cadence, shortened steps, knee compression,
  pelvis weight transfer, shoulder counter-rotation, relaxed hands and
  heel/toe roll. Start/stop transitions ease smoothly. Faster walking retains
  the separate aisle timings so people do not collide.
- Activity speed changes preserve elapsed scene time rather than jumping
  visitors or games to a different point in their routines.

## Room and controls

The room now includes a three-cup honours display, bound records, an old
two-dial clock, pinned notices, original chess prints, a visitor book and an
entrance umbrella stand/coat hooks. Static decoration is batched.

Use the existing **Board view → Live chess club** selection. People, live
motion, background games, atmosphere, activity and frame-rate controls still
apply. Quiet mode shows two seated players; switching people off hides the
entire cast. There are at most six visible people in the busy room. Cameos
appear during visits, not all together at startup.

Hidden/offscreen views pause; still mode does not run a continuous animation
loop. Local-time lighting, the real computer-time wall clock, side chess
clocks, camera controls and 4K photo capture are retained. Scenery games are
illustrative and isolated from tournament and Player Arena games.

## Validation and scope

Validation uses disposable data only: actual GLB pose/contact tests over
30 minutes of simulated scene time, guest-rotation coverage, open-door
crossings and visitor separation; asset hashes and embedded resources;
Focus/Player controls, local time, reduced motion, hidden pause, 4K output,
resource lifetime and eight-language dialogs; existing room and Player
workflow regression checks. Local validation artifacts record exact results.

This remains a finite modeled cast with authored animation, not motion capture
or autonomous people. The private installer is for the owner's visual review;
no publication or production installation is performed by the build process.
