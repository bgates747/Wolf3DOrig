# WOLF-PERF-014 — Cache wall texture IDs across grouped scans

Next local candidate under WOLF-GOAL-001. This contract precedes implementation;
PERF013 actual78 remains immutable and must finish restoration/release first.
MechAgon first/Wolf second, Oryx down; Pi serial builds and actual Olimex grants.

- [x] WOLF-PERF-014-01 — Select/pin exact output-qualified baseline after the
  PERF013 physical disposition; freeze its actual package/source/provider pins.
- [x] WOLF-PERF-014-02 — Implement one bounded per-column texture-ID cache only.
- [x] WOLF-PERF-014-03 — Qualify actual kernel pixels/order/refusal/release,
  existing renderer/module/600pose equivalence, exact target control and
  compiler/provider/sections/nested-stack/resource/producer identities.
- [ ] WOLF-PERF-014-04 — Freeze finite uncapped matched run with current owner
  tuple/rollback/host closure, obtain normal opportunistic fresh admission.
- [ ] WOLF-PERF-014-05 — First-unexpected stop, preserve RAM before LOAD,
  exact restoration/readback/fullcleanup/release and next-owner notification.
- [ ] WOLF-PERF-014-06 — Publish/share measured gain, zero or regression;
  distinguish hidden draw capacity from end-to-end presented performance.

PRE-CODE: existing draw_walls first discovers required texture IDs, then scans
all256columns per required texture and calls wall_texture_id again. Both the
original/bespoke and selected module references are in VDPL034 LIN-F005. Keep
module grouping as its existing documented consumer choice; no claim that it
was forced by the API or identical to original post coalescing.

The existing row API supports a local256-byte array of exact per-column IDs.
Initialize every entry:0for nonpositive wall height, otherwise the same helper
result. Mark needed IDs exactly as before; visit texture IDs ascending, acquire/
bounds-check/release once per group, and visit columns ascending. Membership
uses the cached ID. Metadata scratch remains unchanged and texture/output
sampling uses the existing wall helper without change. No sorting, linked
buckets, new allocation, pointer lifetime, wide stores or firmware extension.

This reduces repeated metadata/helper work; it does **not** remove the repeated
256-column membership scans. Report that distinction. Preserve invalid-ID and
nonpositive-height behavior and all failure/refusal paths. New local storage
must fit the actual nested target stack before dispatch. No assumption that
helper source calls were all retained by the compiler or that the gain is large.
