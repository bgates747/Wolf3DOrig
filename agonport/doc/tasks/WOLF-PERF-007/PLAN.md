# WOLF-PERF-007 — Restore the original table-driven ray walk

Smith's direct correction on2026-11-06 selects the original method: "carmack
was a genius. do what he does." The annotated issue is the bespoke port's
replacement of original precomputed tangent/intercept stepping by per-ray
fixed-point divisions. This task takes priority over PERF006-P02 division-
provider tuning. It is not permission to change every rendering subsystem.

- [x] WOLF-PERF-007-01 — Record the original/current unit inventory and source
  pins before implementation. Preserve physical69 O2/cd429 as the control and
  original PC source as the method reference; identify numerical/state gaps.
- [ ] WOLF-PERF-007-02 — Close the pre-code compatibility dispositions for
  quadrant setup, table generation, crossing order, wall/door/pushwall hits and
  world-state binding. Supported methods carry over; unresolved incompatibility
  is reported before any replacement method is invented.
- [ ] WOLF-PERF-007-03 — Freeze source-faithful candidate design, then implement
  in an isolated task directory: original tangent tables, integer intercept
  stepping and partial-step intersections. No reciprocal-only shortcut keeping
  the replacement distance-DDA algorithm. Keep O2/safe flags/providers fixed.
- [ ] WOLF-PERF-007-04 — Qualify original-method geometry and boundary behavior,
  table identities/index bounds, sanitizer/resource/lifecycle behavior, compiled
  code/ABI/PSRAM/whole sections/stack and actual per-arm producer lengths. Rebuild
  cd429 control exactly. Record expected original-versus-port numerical deltas;
  do not weaken an old oracle merely to obtain a pass.
- [ ] WOLF-PERF-007-05 — Freeze a finite matched hardware kit only after offline
  qualification; reserve normal Olimex FIFO and reconcile current components/
  source/rollback/real grant. Extender owns the currently requested bench use;
  no old69 token, preemption or implied test access.
- [ ] WOLF-PERF-007-06 — Run the selected same fixture/matrix under actual new
  custody, stop first unexpected, preserve RAM before LOAD where applicable,
  exact restore/readback/full handback and normal release. Smith's old HOLD
  concerned actual69 and was superseded; do not invent a new hold or reuse it.
- [ ] WOLF-PERF-007-07 — Publish exact original-method coverage, numerical/image
  changes, raw matched performance and limitations; share findings/advice gaps
  with VDPlet. Default/gameplay adoption and optical acceptance stay explicit.

The fixed view/projection scale87, pixel-angle table, world wire format, renderer
publication/row ownership/masks, span/background improvements, HUD/weapon/sprite
ordering and local arithmetic provider remain controls. Original ray-bin and
intersection behavior must be identified separately from those controls.
No SDK/firmware extension, ROM import, fastmath, safety relaxation, async renderer,
new carrier or general division-provider change is selected here.

Pi compilation is serial through normal actual checkout with finite child,
80C/512MiB guards and joined-owned cleanup. Emulator work, if needed for visual
qualification, uses Oryx actual checkout, boost off and the existing80C guard;
no Pi emulator diversion. Exact fixture/run selection, source/output/producer/
resource freeze and current component admission precede physical dispatch.
