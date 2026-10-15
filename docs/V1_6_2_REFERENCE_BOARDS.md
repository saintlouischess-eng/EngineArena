# Engine Arena 1.6.2 — two crafted 3D boards

Private development update. Designed by Mark Young; coded with OpenAI Codex.

## Choose a board

In a focused game, open **2D / 3D**, select **3D · 1849 Staunton**, then use
**Setting & lighting → Board design**. Choose Original Engine Arena,
Walnut & maple · Drueke, or Purpleheart & maple · Jaques, then **Apply**.
The selection is saved independently of your room, table surface and camera.
**Table details → Board coordinates** shows or hides the letters and numbers.
Hide them for the unmarked appearance of the physical reference boards.
The existing Photo button exports the selected board at 3840 × 2160.

## Construction and finish

The Drueke-style model has a broad tapered walnut surround, butt-jointed rails,
and recessed intersecting grooves extending beyond the playing field. The
Jaques-style model has a narrower raised, mitered walnut surround with a rolled
inner profile and a recessed purpleheart/maple playing field. Both retain an
8 × 8 playing surface with the pieces resting at the same height.

The models follow the sellers' 2.5-inch-square versions: a 20-inch playing field,
24-inch overall width for Drueke (2-inch border), and 22-inch overall width for
Jaques (1-inch border). These are scene proportions, not a physical screen scale.
The unspecified thickness and molding cross-sections are inferred from photos;
these are faithful visual reproductions, not measured manufacturing replicas.

Original geometry uses 3D grooves and molding, rail-aligned grain, different
wood sections for individual squares, fine normal detail and satin reflections.
The photographed CC0 wood material is given walnut, maple and purpleheart color
palettes. It does not reproduce the exact grain of the seller's individual board.
No seller photographs are included in the application. Wood scan attribution
remains in ThirdParty/PolyHaven. Lighting and environment change perceived color.

Coordinates fit the narrower raised frame and follow the Drueke taper. The
wider board shifts nameplates and plaque outward to keep them clear. Board
switching preserves game position, camera, piece directions and crown marks.
The models share three material maps, and each style's small mesh collection is
built once per renderer. Switching repeatedly adds no further GPU resources.
All resources are disposed when the renderer closes. Hiding trays or nameplates
now refreshes the cached shadow map, removing stale shadows. No network is required.

## References

- [Walnut and maple Drueke-style board](https://www.etsy.com/listing/1744616098/walnut-and-maple-drueke-style-chess), ColoradoWoodWorker.
- [Purpleheart and maple Jaques-style board](https://www.etsy.com/listing/4387759532/purple-heart-and-maple-jaques-style), ColoradoWoodWorker.

Reference names describe the requested styles; no affiliation or endorsement is claimed.

## Validation scope

Isolated source and packaged-app checks cover all three boards, empty/playing
positions, raised and low camera angles, coordinates, saved preferences,
repeated switching with stable GPU allocation, and real 4K PNG exports. The
existing scene acceptance also checks all rooms and surfaces, eight languages,
idle/hidden rendering, camera-tour interruption and renderer cleanup. No
production tournament data is used or modified by these checks. This is not
a sustained GPU performance benchmark or a substitute for laptop review.
