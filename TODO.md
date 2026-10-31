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
loadable Wolf3D VDPlet running on the shared VDPlet runtime. The completed
feasibility study is a conditional go. Under GOLEM-057, implement and qualify
only the released bounded proof: one real freestanding module, compact mirror,
representative static DDA/sprite scene, application-owned full-frame workspace,
generic pixel publication, requested completion, and orderly teardown. Preserve
the standalone renderer as the exact oracle and rollback path. The bounded
host, pinned Oryx target proof, full-MOS headless rehearsals, bounded
error/recovery matrices, and human visual/keyboard reviews passed on
2026-10-30 for both the copied-pixel proof and the optional ABI 1.6
direct-colour-row proof. Both returned cleanly to MOS and accepted `dir` after
unload. The direct-row proof preserves exact pixels while reducing caller
workspace by 80,608 bytes (87.47%), at a measured cost of about 32.93% more
modeled RENDER transaction cycles in the bounded scene. This emulator evidence
does not imply physical acceptance or establish a production winner. The full
eZ80 production-client lifecycle also passed generation 35 with exact scene,
teardown and MOS-return evidence. Its readable Author review passed on
2026-10-31: the oracle scene rendered correctly, Enter requested orderly
unload, MOS returned to a live prompt, `dir` worked, and the exact result hash
matched. Gameplay integration, update batching, fizzle migration, default
cutover, and physical qualification remain later gated work. See
`agonport/doc/wolf3d-vdplet-migration.md`.

[ ] 8e. Replace the bounded static scene with the production render contract.
Implement the compact authoritative mirror, validated atomic dirty-update
batches, real tilemap and per-texture asset access, actors/statics/doors/HUD/
weapon composition, one-producer APPLY_AND_RENDER ownership, and app-paced
fizzle. Compare deterministic output with the standalone oracle, then run
complete emulator, human, performance, and physical gates before changing the
default backend or removing the standalone rollback path.
