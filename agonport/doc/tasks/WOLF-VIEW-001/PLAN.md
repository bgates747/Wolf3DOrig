# WOLF-VIEW-001 — Investigate arbitrary player-controlled viewport sizes

Status: task prepared November 9, 2026; investigation and implementation have
not started. Smith requests the option to change the 3D viewport size during
play, with arbitrary sizes rather than a small selection of baked presets.
This task does not resume the paused optimization goal or change the queued
WOLF-PROD-001 runtime check.

## Intended behavior

The player can resize the 3D viewport during play within explicitly documented
screen, layout and resource bounds. Investigate runtime selection of width and
height at individual-pixel resolution, including odd dimensions; identify and
justify any unavoidable restriction instead of silently rounding to presets or
alignment multiples. Arbitrary size does not mean dimensions beyond the display.

Include expansion beyond the present 256x160 view. Determine the largest useful
view inside the current 320x240 display, initially retaining the HUD. Assess a
HUD-hidden/full-display option separately. Determine whether controls should
resize proportionally, allow independent width/height, or support both; recommend
an interface and document the aspect-ratio/FOV consequences before implementing
it. Investigate saving the selected size in the existing game configuration.

Changes must preserve the player's pose, world state, input responsiveness and
game speed. Build a complete new projection/layout state before adopting it at
a safe frame boundary. A failed or invalid change retains the previous working
view. Both framebuffer pages must receive correct borders and exposed areas
after expansion or contraction, without stale pixels or mixed old/new geometry.

## Projection preparation and original-code reference

Original `orig/src/WOLFSRC/WL_MAIN.C` separates `BuildTables` (around586–625)
from `CalcProjection` (around640–688). Its global sine/tangent tables are
independent of viewport size. Projection scale and per-column ray-angle offsets
are viewport-dependent; the original recalculated projection data when the view
changed. Its setup uses floating point, while normal drawing uses integer tables.

Our current tables are generated offline. Investigate computing the required
projection data on a size change and reusing it for subsequent frames. Keep
global sine/tangent tables shared. Compare the original projection method with
an integer/lookup implementation that respects the existing fine-angle and
fixed-point conventions; document rounding, FOV, near-depth and overflow domains.
Do not replace arbitrary-size support with precomputed per-size presets.

Check actual VDPlet compiler/library/runtime support before choosing a numeric
method. Record any incompatibility and consult its owner; do not introduce an
unreviewed fallback, loosen module admission, or assume setup-time floating point
has an available freestanding provider. This is an investigation, not a selection
of a new firmware service or arithmetic implementation.

## Current source constraints to inventory

Use maintained optimized production module7490d81c as the starting point;
preserve its existing 256x160 output as a regression control.

- `agonport/vdplet/production/wolf3d_renderer.cpp`: fixed view origin/dimensions,
  center, projection scale/height numerator, per-column ray loop, wall/sprite
  clipping, weapon placement, background and border composition.
- `production/wolf3d_tables.inc`: 256 per-column fine-angle offsets; degree sine
  and original tangent tables have separate size-independent roles.
- `production/wolf3d_renderer.cpp` wall chains: an explicit width256 assertion,
  byte-sized links and termination scheme. Views wider than256 need a deliberate
  index/sentinel design and stack/resource accounting, not just larger tables.
- `production/wolf3d_production_contract.h`, its generator/schema and renderer
  header: fixed per-column metadata/workspace regions, copied and direct paths,
  row access, fizzle bounds and runtime resource descriptors.
- Module CONFIG/APPLY/reset/retry lifecycle and eZ80 client: where dimensions
  belong, validation and wire/schema compatibility, change acknowledgement,
  configuration persistence and synchronization with a pending render.
- HUD, weapon, fizzle, loading/status/profiling indicators and both-page redraw:
  distinguish viewport-relative layout from physical-screen layout. Preserve
  each component's correct placement and transition behavior.

Changing the viewport within the current video mode is the primary subject.
Changing display resolution, adding async newest-pose rendering, changing
physics pacing or enlarging maps is separate work.

## Investigation work and deliverables

- [ ] VIEW-01 — Trace the original resize controls/projection lifecycle and
  inventory every current fixed-size dependency, with source intervals.
- [ ] VIEW-02 — Produce a pre-code compatibility/support ledger: projection
  generation, controls/configuration, module protocol, buffer/row ownership,
  metadata/index widths, memory and stack limits. Mark concrete gaps explicitly.
- [ ] VIEW-03 — Recommend supported dimension bounds, FOV/aspect-ratio policy,
  control interface, persistence and transactional frame-boundary resize design.
- [ ] VIEW-04 — Estimate projection-generation work, resize latency, resident
  memory, per-frame work and likely performance effects for smaller/current/
  larger views. Separate estimates from measurements and account for native
  scanout/presentation cadence independently of renderer time.
- [ ] VIEW-05 — Propose a finite correctness/performance qualification plan and
  implementation stages, then write REPORT.md and stop for Smith's discussion.

The report must answer whether arbitrary sizes are practical with current
firmware, what needs changing, the largest useful viewport, expected resize
latency and resource costs, and the smallest coherent implementation tranche.

## Proposed later qualification, not dispatched by this task preparation

Preserve exact current-size pixels/geometry. Exercise minimum/maximum sizes,
widths255/256/257, odd/even dimensions, aspect-ratio extremes, repeated live
expansion/contraction and invalid/allocation-failure requests. Check fine-angle
table endpoints/symmetry/rounding, projection bounds, texture/occlusion/clipping,
doors/pushwalls/sprites/weapon, HUD/fizzle, page guards/sync bits, leases and
unchanged world state. Compare direct/copied output where their contracts apply.

Use visibly rotating scenes for presentation acceptance, with static-only cases
clearly labelled. Measure resize-generation latency separately from steady-state
render/presentation and input responsiveness. Performance comparisons are
uncapped; record any future optional presentation pacing as a separate setting.
User-visible runs are loaded without agent RUN and announced through the
application's question feature so Smith can start them.

This request selects task documentation only: no prototype, build, benchmark,
reservation, firmware change or target operation. Later execution follows the
then-current FIRMWARE.md defaults and normal compiler/Oryx/Olimex scheduling.
