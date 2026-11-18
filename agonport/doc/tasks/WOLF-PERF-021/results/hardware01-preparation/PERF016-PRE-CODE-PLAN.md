# WOLF-PERF-016 — Avoid the cyan fill covered by the viewport

New source finding during WOLF-GOAL-001 moves this arm ahead of PERF014/015:
compose_background still fills the entire320×200 cyan play area, then overwrites
the256×160 viewport with ceiling/floor. Avoiding40,960pixel merges/frame is a
larger concrete work reduction than metadata caching; performance is unmeasured.
This extends the earlier clear-extent investigation, which removed64,000initial
dark-gray writes but intentionally left this separate cyan/view overlap.

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

For all Olimex bench procedures, use the sole authoritative [bench guide](/Agon/mystuff/agon-extender/docs/operations/olimex-bench/README.md).
