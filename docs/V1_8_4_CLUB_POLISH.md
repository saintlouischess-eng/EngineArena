# Engine Arena 1.8.4 — live club polish

Designed by Mark Young. Coded with OpenAI Codex.

Private update for owner review. Includes the approved Tal 1962 set and the
previous season admission, Player Arena and graphics-recovery improvements.

## Characters and movement

- Fuller side and nape coverage for short-haired spectators and cameos. Fitted
  opaque hair follows the head and retains depth from every viewing direction.
- Solid, fitted beard underlayers for the two bearded cameos, with fine growth.
- The younger seated player has a face and blonde, center-parted,
  shoulder-length hairstyle based on the owner's photograph. This is a modeled
  approximation from a single view, not a scanned likeness.
- Both seated players' feet and knee poles derive from their own hip joints.
  The free hand follows torso motion rather than staying fixed on the table.
  Arm bones keep constant lengths; reaching is solved through joint rotation.
- Bookshelf visitors select one of three chess books, reach with the nearer
  hand, take it down, step back, open/read/turn pages, close it and replace it.
  The selected book leaves its actual shelf slot; the other books stay put.
  Disabling people returns the books to the shelf. Pausing animation freezes
  the current reading pose.

## Review and validation

Front, side and rear grooming views, seated resting/reaching/clock poses and
the complete bookshelf sequence were reviewed. Automated motion validation
samples all twelve actual character assets over 1,820 simulated seconds.
It checks constant arm lengths, hip/knee alignment, hand-to-piece/book contact,
foot planting, inward walking palms, visitor separation and door passage.

The update also runs the JavaScript regression suite, asset/provenance and
release checks, eight language catalogs, packaged live-room workflows, camera
controls and simulated graphics-loss recovery in disposable test data.
All packaged checks passed, alongside 85 JavaScript tests, 17 backend/asset/
release tests and all eight catalogs. The disposable fixture retained its two
original results/openings and passed SQLite integrity checking. The installer
validation sidecar records the final results and checksum.

These are software-rendered functional and visual checks. They do not measure
performance on every GPU or reproduce a physical GPU-driver crash. Production
tournaments, engines, ratings and settings are not used by the checks.

Pause and drain any testing, then close Engine Arena before installing.
