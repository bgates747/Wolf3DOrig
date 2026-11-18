# WOLF-PERF-014 — Cache wall texture IDs across grouped scans

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

For all Olimex bench procedures, use the sole authoritative [bench guide](/Agon/mystuff/agon-extender/docs/operations/olimex-bench/README.md).
