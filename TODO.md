# Wolf3DOrig TODO

This is the project's single authoritative list of intentionally promoted,
unfinished work. IDs are stable references and are not reused. When an item is
accepted, rejected, or superseded, record its ID, evidence, and rationale in
the current dated development log, then remove it from this file.

[ ] 2b. Diagnose and correct the hardware-observed ordinary floor-transition
defect: after completing E1L1, E1L2 currently appears to place the player in a
single enclosed grid cell surrounded by gray walls. Determine whether the
runtime W3L state, tilemap upload, VDP reset/rebind sequence, or starting pose
is stale or malformed; add a regression that proves the destination floor's
real map and player spawn are authoritative before accepting the fix.

[ ] 3b. Add the reserved Agon-specific splash and presentation hook without
changing the accepted original-facing startup flow.

[ ] 4. Widen or remap the byte-sized actor-state dispatcher before importing
the remaining original actor states, avoiding the current 254-ID ceiling.

[ ] 5. Implement bosses, projectiles, ghosts, and other special actor
behaviors from the original game.

[ ] 6. Implement music playback as a separate subsystem from the accepted
sound-effects implementation.

[ ] 7. Add high-score entry and remaining presentation polish after the core
game progression is established.
