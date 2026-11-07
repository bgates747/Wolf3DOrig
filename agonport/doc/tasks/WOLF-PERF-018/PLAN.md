# WOLF-PERF-018 — Reuse identical wall-column scaling setup

One later local optimization under WOLF-GOAL-001; keep the running PERF017
cohort, all prior candidates and their evidence unchanged. This contract
precedes candidate code. MechAgon remains first priority; Oryx is down.

- [ ] WOLF-PERF-018-01 — Freeze exact a926 baseline and pre-code compatibility,
  work, order and lifetime boundaries.
- [ ] WOLF-PERF-018-02 — Implement only a one-entry scaling-setup cache within
  each existing texture lease; no pixel sampler or write-order change.
- [ ] WOLF-PERF-018-03 — Qualify an independent scalar wall oracle, aliased rows
  and assets, exact call/refusal/release order, metadata, full renderer/module/
  600-pose output and target control/code/provider/stack/package bindings.
- [ ] WOLF-PERF-018-04 — Count actual setup reuse opportunities separately from
  timing; select a useful finite uncapped hardware comparison only after code,
  resource and real producer qualification. No new test under actual85.
- [ ] WOLF-PERF-018-05 — Normal fresh grant, finite run, first-fault preservation,
  exact restoration/readback/fullcleanup/release and next-owner notification.
- [ ] WOLF-PERF-018-06 — Publish timing, size, stack and work changes, including
  zero FPS improvement; no automatic default adoption or arm combination.

## Pre-code compatibility and intended work

The selected a926 draw_walls acquires each needed texture in ascending ID order
and visits its columns in ascending screen order. Every accepted column repeats
top/bottom clipping, destination extent, fixed texture step division and start
fraction, all determined solely by its positive full height.

Ordinary integer locals and comparisons support caching that pure setup as-is;
the existing draw_wall_column call can consume the identical cached values.
No firmware, SDK, helper, service, allocation, provider or row API extension
is needed. Keep the supported row-span and safe compiler/PSRAM policy unchanged.

Within each texture lease, start cached full height at zero and initialize all
cached fields. For a matching positive column, read its actual full height.
Recompute exactly the existing expressions when that height differs; otherwise
reuse their results. Still invoke the existing scalar column sampler once per
accepted column, with that column's current U, in exactly the original order.
Cache a zero/empty destination result consistently and keep acquisition, bounds,
statistics, failure and release semantics unchanged. No early U/source read or
retained asset pointer. The cache dies at that texture lease's end.

This saves repeated setup/division on equal heights; it adds a comparison and
several local words. It does not reduce pixel writes, texture samples or per-ID
membership scans. Count the actual eligible columns rather than assuming every
wall ray saves a division. Changed code/stack cost may outweigh the work saved.

## Original-method and alias boundaries

Carmack's widening posts can replace a new ray's height with the previous
post's height, and his generated scaler uses different fractional units and
texel-boundary rules. Those are the explicit incompatibilities recorded in
the original-method ledger. This task restores none of those behaviors and
implements no substitute for unavailable x86/VGA generated code.

It selects a distinct, output-preserving arithmetic cache in the current
renderer. Unlike the earlier possible horizontal row-span grouping, it changes
neither column-major write order nor texture-read order. VDPlet's concrete
aliased-row counterexample therefore remains an oracle case rather than an
assumption that rows never alias. Also test source/destination aliasing, arbitrary
colour/preserve masks, mapping XOR/bias and guard bytes, and positive full heights
whose clipped extents match but texture phases differ. Equal clipped extent is
never the cache key. No arbitrary-alias equivalence is asserted before testing.

Exact baseline and owner advice are pinned in SOURCE-PINS.json. A hardware
contract, if useful, must be separately frozen with actual current component,
rollback, resource, host closure and per-arm guest length/limit operands.
