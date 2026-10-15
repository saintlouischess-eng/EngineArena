# Engine Arena 1.7.5 — private club corrections

Designed by Mark Young. Coded with OpenAI Codex.

This build corrects the camera-dependent bald patches reported in the live
chess club. Imported transparent hair materials retained disabled depth writes
after being converted to opaque cutouts; the scalp could then overwrite the
hair. Hair now writes depth, tests depth and renders from both sides. The
temporary scalp caps on Mei and Nora were removed and those models rebuilt.

Visitors walk with a narrower foot track and their palms toward their thighs,
thumbs forward and fingers loosely curved. Seated players rest their hands
beside the board. Elbow orientation and forearm twist are corrected without
stretching the skeleton, and hand contact follows the moving piece and clock.

The formerly blank opposite wall now has a large framed chess composition,
four smaller matted prints, a paneled walnut record cabinet, books and a
leather reading bench. These static details are batched with the room geometry.


The pale vestibule caps were coplanar with the green wall around the upper
doorway and flashed during camera pans. They now terminate behind the wall.
A geometry regression checks the actual batched surfaces for overlap.

Choose **Live chess club — full 3D** in the 3D appearance controls. Existing
people, movement, background-game, atmosphere, local-time and sound controls
are retained. The decorative tables never submit real moves or results.

Validation includes material-depth regression tests, all twelve actual GLBs,
both palms throughout visitor routes, resting-hand direction, walking width,
piece/clock contact, route separation, camera views and the packaged club,
other-room and Player Arena workflows. Detailed results are recorded in the
local build-validation output. Models remain stylized original adaptations;
this is a correction to their rendering and animation, not a photoreal scan.

Pause and drain active games, then close Engine Arena before updating.
