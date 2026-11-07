# WOLF-PERF-016 — Avoid the cyan fill covered by the viewport

New source finding during WOLF-GOAL-001 moves this arm ahead of PERF014/015:
compose_background still fills the entire320×200 cyan play area, then overwrites
the256×160 viewport with ceiling/floor. Avoiding40,960pixel merges/frame is a
larger concrete work reduction than metadata caching; performance is unmeasured.
This extends the earlier clear-extent investigation, which removed64,000initial
dark-gray writes but intentionally left this separate cyan/view overlap.

No code changes to running PERF013/78. MechAgon first/Wolf second; Oryx down;
normal serial Pi compilation and actual Extender grants. No default adoption.

- [x] WOLF-PERF-016-01 — Pin exact output-qualified predecessor after PERF013
  disposition; freeze this compatibility/work ledger before candidate code.
- [x] WOLF-PERF-016-02 — Replace only the covered cyan fill with four exterior
  rectangles where overwrite semantics permit it; retain exact fallback otherwise.
- [x] WOLF-PERF-016-03 — Independent full-background byte/guard/mask oracle,
  renderer/module/failure/600pose equivalence, actual package/control/flags/
  providers/nested-stack/resource and exact real guest-size operand qualification.
- [ ] WOLF-PERF-016-04 — Freeze useful finite uncapped matched cases/current
  tuple/rollback/host closure; normal opportunistic fresh bench admission.
- [ ] WOLF-PERF-016-05 — Stop first fault, preserve RAM before LOAD, exact
  restoration/readback/fullcleanup/release and actual-next notification.
- [ ] WOLF-PERF-016-06 — Publish/share measured result, including no FPS change.

PRE-CODE gate: existing fill_rect/fill_span support the exact needed byte writes.
For copied linear output, overwrite removes the hidden cyan contribution. For
native rows with disjoint color/preserve masks, the subsequent ceiling/floor
replacement likewise removes it. Fill only top y<20, bottom y>=180 and<200,
left x<32/right x>=288 between those rows. Keep HUD background, ceiling/floor,
bevel drawing, palette application, geometry, asset order and failure behavior.
No earlier geometry cast, extra resource or pointer lifetime is introduced.

**Mask exception:** overlapping color/preserve masks can retain bits from an
earlier fill. Keep the original full cyan fill when those masks overlap; do not
assume physical0x3f/0xc0 semantics apply to every host target. This source-backed
fallback preserves an existing supported representation, not an SDK workaround.
Tests must witness overlapping as well as disjoint masks and arbitrary initial
bytes, row permutations/noncontiguous rows and linear output. Do not replace the
existing pixel merge or use wider stores. Do not combine removal of floor/
ceiling behind walls, cached HUD/page identity, or post-height reuse in this arm.
