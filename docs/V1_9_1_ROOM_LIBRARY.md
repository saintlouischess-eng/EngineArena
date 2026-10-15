# Engine Arena 1.9.1 — room, camera and library update

Private candidate for owner and laptop testing. Designed by Mark Young;
coding and implementation by OpenAI Codex. This is a complete installer;
intermediate private updates are not required. The public version remains 1.2.14.

## Room motion and frame limit

In either board's Appearance settings, choose **Room motion**:

- **Follow Windows** respects reduced motion and shows a clear explanation if
  Windows pauses the room. This is the accessibility-preserving default.
- **Animate** enables the room independently of Windows Animation effects.
- **Still** deliberately freezes people and scenery; clocks keep time.

Bring the room to life and the individual room checkboxes still apply. Hidden
boards pause animation. Camera tours and focused-board move animation continue
to respect Windows reduced motion separately.

Animation limits are **15 and 30 FPS**. Previously saved 60 FPS choices load as
30 in both workspaces. The owner observed successful day/night testing at 30 and
repeated NVIDIA resets at 60; removing 60 is a mitigation, not proof of the exact
driver fault. Sustained testing on the owner's hardware remains necessary.

## Upward tilt and low-angle photography

Use the new **Tilt** slider while watching in Focused Game or Player Arena.
Positive values aim up; negative values aim down. The tilt range is −30° to 70°,
independent of orbit position, zoom and vertical framing. Appearance also has a
numeric tilt field and a **Low angle** preset. Viewing elevation now reaches 6°.
Camera views remember tilt; Reset camera restores the default view.

Both photo dialogs have tilt controls. The current position and room animation
freeze during composition. Photo changes leave the watching camera unchanged;
closing resumes the board. Exports remain 3840 × 2160 PNG. Photo folder selection
continues to use the native desktop save controls.

The live club's solid ceiling now has separated coffer rails without overlapping
undersides, shallow inset trim, and attached lamp canopies. These are statically
batched; they do not add lights, render passes or recurring animation work.

## Engine selection and deletion

Explicit Engine library selections take precedence over saved draft participants.
Other conditions remain available from the draft. Ordinary draft recovery,
selection order, all-library setup and gauntlet candidates stay consistent.

**Delete selected (count)…** sits beside the selected count in a sticky action
bar. Checkboxes can select profiles across pages. Confirmation and cancellation
remain available. After deletion, the search, current valid page and scroll are
preserved. An emptied last page moves to the previous valid page. This removes
library profiles; engine files and recorded tournament snapshots are preserved.

## Verification scope

Targeted automated checks cover setup drafts, editing, adjudication controls,
translations, release identity, camera input and motion, graphics recovery and
frame budgeting. Browser acceptance uses a disposable database and software
graphics, including reduced-motion emulation, bulk deletion and saved cameras.
Package acceptance checks the shipped worker/UI, short controlled UCI games,
all PGN presets, report generation and a clean restart. Installer verification
compares the manifest, source snapshot, catalogs and public documentation.

These are bounded regression checks; they do not establish a hardware GPU soak
result. No production results, installed program or public release are changed.
