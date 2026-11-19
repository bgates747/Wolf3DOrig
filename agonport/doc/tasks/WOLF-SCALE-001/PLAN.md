# WOLF-SCALE-001 — Compare Rally’s bitmap sampler with Wolf’s renderer

Determine whether Rally’s SCL-001 sampler or its precomputed horizontal
sample map can make actor and weapon drawing faster in Wolf’s production
VDPlet renderer. This task starts with source review and a consultation with
Rally.

## Existing evidence

Rally’s retained SCL-001 host results cover nearest-neighbor reductions
with a 99-entry horizontal sample map, transparency, clipping and horizontal
mirroring. The sampler writes a scratch bitmap and then plots it. The Pi
results show a speedup over cached stock affine plotting for the tested
cases. Ask Rally for the latest evidence, particularly any native VDP results
and any coverage of identity scale or enlargement.
[SCL-001 status](/Agon/mystuff/AgonArcade/docs/tasks/RALLY-28/custom-vdp/scaler-comparison/STATUS.md)

Wolf already uses incremental fixed-point sampling and draws directly into
the back-buffer rows. The actor pass checks wall occlusion by screen column
and draws far to near. The weapon pass uses the same sampling approach with
its own placement and clipping. Compare against the accepted production path
in `draw_sprites` and `draw_view_weapon`.
[Wolf renderer](../../../vdplet/production/wolf3d_renderer.cpp)

## Investigation

1. Confirm the current Rally source and its qualified inputs with Rally.
   Compare sampling precision, rounding and clipping against Wolf. Check
   representative reduced, same-size and enlarged draws, including clipped
   actors, a sprite partly occluded by a wall, and the weapon overlay. Record
   any domain limits that prevent direct reuse.
2. Compare the whole Rally scratch-and-plot path and the smaller option of
   precomputing source X indices for Wolf’s existing direct draw. Account for
   scratch memory, stack footprint, copies and VDPlet services. Preserve
   transparency, per-column occlusion, pixel format and drawing order. Record
   unsupported operations before considering any replacement.
3. If a trial is later selected, compare exact output pixels using the same
   assets and poses. Measure total sprite drawing cost on the pinned native
   target, including setup and any final plot. Record uncapped frame cadence
   separately from drawing time in an actor-heavy scene. Use the existing
   firmware pins and bench procedures.
   [Firmware pins](../../../../FIRMWARE.md)
   [Olimex bench guide](/Agon/mystuff/agon-extender/docs/operations/olimex-bench/README.md)

Report which technique, if any, warrants a prototype, with the measured
evidence and unsupported cases called out. The current freeze covers the
plan and source consultation. A build or benchmark is a later decision.
