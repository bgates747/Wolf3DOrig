# Wolf3DOrig TODO

This is the project's single authoritative list of intentionally promoted,
unfinished work. IDs are stable references and are not reused. When an item is
accepted, rejected, or superseded, record its ID, evidence, and rationale in
the current dated development log, then remove it from this file.

[ ] 2c. Present the original-style floor-completion intermission before each
ordinary or secret floor transition, using the bundled level-end artwork and
the completed floor's authoritative time, kill, secret, and treasure state.
Draw it immediately, begin loading the destination without an acknowledgment
pause, and use finalized-asset callbacks to animate/poll input while loading.
An acknowledgment may be latched during loading; Escape must instead converge
on the common clean application-exit path from every shell, load, intermission,
and gameplay phase.

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

[ ] 8. Replace the requirement for a dedicated Wolf3D VDP firmware with a
loadable Wolf3D VDPlet running on the shared VDPlet runtime. Phase 1 is a
feasibility study and implementation plan only: identify the renderer's
firmware dependencies, required VDPlet ABI/runtime extensions, memory and
performance envelopes, protocol and lifecycle changes, compatibility risks,
and qualification gates. Stop for Author review before implementing the
migration. See `agonport/doc/wolf3d-vdplet-migration.md`.
