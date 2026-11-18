# WOLF-PERF-006 — Performance-gap priorities and the O2 comparison

## Prioritized work

- [x] WOLF-PERF-006-P01 — Compare exact current module under -O2 versus -Os.
  Low implementation effort, uncertain potentially useful payoff. Same source,
  helpers, safety flags/runtime/scene. Close package/sections/stack/actual guest
  producer bindings before matched physical timing. Selected now.
- [ ] WOLF-PERF-006-P02 — Qualify optimized division provider instead of fixed
  64-iteration helper. Moderate effort/potentially substantial gain; exact
  supported libraries, signed domains, final closure/relocations/stack first.
- [ ] WOLF-PERF-006-P03 — Hoist remaining textured-pixel invariants where safe.
  Moderate effort/potentially substantial payoff. Extrapolates measured span
  improvement, not another measured result. Preserve masks/permutation/alpha/
  bytes/row lifetimes and inspect actual generated loops.
- [ ] WOLF-PERF-006-P04 — Factor sprite-column occlusion decisions once per
  column. Low/moderate effort, scene-dependent payoff. Preserve row locality,
  clipping/wall-wins-equality/transparency and bounded storage.
- [ ] WOLF-PERF-006-P05 — Reduce repeated texture-group wall-column scans while
  retaining acquisition savings. Moderate effort/conditional payoff; exact
  borrowed-resource lifetime and output equivalence first.
- [ ] WOLF-PERF-006-P06 — Compare quarter-wave versus full trig tables.
  Moderate effort/likely smaller payoff and resident-data cost. Setup-only
  floating-point trig is not a hot-frame diagnosis.
- [ ] WOLF-PERF-006-P07 — Study original wall-post/scaling/visibility techniques.
  High effort/uncertain payoff; these already differed in bespoke, and literal
  x86 methods do not automatically suit Xtensa. Projection and sprite ties are
  behavior decisions, not covert performance edits.

Priorities use VDPlet VDPL031/NEXT-MEASUREMENTS, VDPL033 original-unit ledger,
verified physical63/67 and VDPL034 lineage discussion/report. The latter report
is reviewer evidence pending owner verification, not an established defect list.
Both original draw entry points are synchronous; finite RUN alone is not a
measured cause. Independent physics/latest-pose rendering is a separate possible
responsiveness task; this comparison does not select it.

## Immutable implementation subtasks

P01 completed in PHYSICAL69-RESULT.md/json, commit af4d780. Same-source O2
draw32.4392ms versus Os36.7942ms (-11.84%), completed27.8390 versus24.8329
frames/s. All6guests/7probes/2400records pass; exact native/tail85f9 restored,
actors stopped, actual69 held. Detailed result/held-idle handback delivered to
Extender and VDPlet in wolf-perf006-physical69-held-result-ext-nine and
wolf-perf006-physical69-held-result-vdplet-nine. No further priority, production
adoption, device probing or release is selected. Await Smith's bench direction.

Later custody update: RELEASE69.md records verified newer Smith direction and
actual fresh clean release69 at23:16:35Eastern. The earlier held-idle result and
all frozen inputs remain historical evidence, not current bench ownership.

## Build and execution boundaries

For all Olimex bench procedures, use the sole authoritative [bench guide](/Agon/mystuff/agon-extender/docs/operations/olimex-bench/README.md).
