# Engine Arena 1.9.2 — mouse camera polish

Private candidate. Designed by Mark Young; coding by OpenAI Codex.

The 1.9.1 tilt slider could aim above the board, but ordinary mouse movement
stopped at the lowest viewing elevation. The same mouse drag now continues
smoothly into an upward look, keeping the camera above the table. Dragging back
down returns toward the board. Downward movement is bounded to prevent flipping
the camera over. Horizontal rotation remains available while looking up.

- Right-drag to look up, down, left or right. No additional key is required.
- Alt + left-drag provides the same movement for trackpads.
- Shift + right-drag adjusts vertical framing; the wheel zooms.
- Arrow keys look around; Home resets the camera.
- The tilt slider and photo controls remain available for precise composition.

Focused Game and Player Arena share the controls and save the view. Player
Arena still reserves ordinary left-click and left-drag for moving chess pieces.
The live-room animation limit remains 15 or 30 FPS.

Validation evidence and packaging status are recorded in docs/HANDOFF.md.
Graphics checks use a software renderer; they are not a physical GPU endurance
test or a claim to have identified the desktop driver's instability.
