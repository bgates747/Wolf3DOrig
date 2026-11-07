# Identical-post source gate: defer this canonical-room implementation

The unchanged control raycast on the canonical600-pose/two-turn room finds
**191864 texture reads potentially avoidable out of4368126 (4.392%)** if every
layout/source check admits the method. That averages about320 avoided reads per
frame. All4368126 wall pixel stores remain; background/sprite/HUD work remains.
Across600 poses there are150608 groups, only2976 with multiple columns, and the
widest group is3 columns. Width1 scalar work dominates this room.

This is enough to defer the harder implementation in this tranche while easier
qualified candidates await physical measurement and combination. It is not a
measured speedup/regression, a cycle-time bound, or a global rejection. Near-wall
scenes and a larger viewport can have different opportunities and remain useful
future subjects. No new scene/benchmark/method implementation is selected here.

Each pose compares independent per-column clipped pixel totals against summed
group width*clipped-height totals, with identical FULLheight/resolved-ID/U keys.
All600 scripted poses/300 distinct headings, CSV step/angle and arithmetic joins
pass. Sanitized serial host compilation/census completed4.788s, compiler373
children joined and normal release retained. Initial invocation stopped before
assert/child creation because the task build parent was missing; creating that
parent launched the unchanged selected script, with no compiler or target replay.

VDPlet's source advice and independent consumer reading establish the supported
boundary, not physical applicability: exact7593 pauses/drains/captures actual row
addresses until END; ordinary acquired textures retain their leases without
changing mappings. Wolf stores actual row pointers in separate leased workspace,
uses them directly and ends/clears even on failure. VGABaseController can allocate
multiple pools. Thus the proposed strict contiguous-row predicate may reject
an actual native page; no native admission/hit count is known from this census.
The optional fast path must still preserve stable row-table/grouping metadata,
source lifetime/nonalias, actual row pointers, acquire/null/size/release/failure
and partial-frame order, texel&63 and scalar fallback. No wider writes, new
firmware/API/helper, fabricated provenance flag or original geometry substitution.

The added predicate/run discovery/span setup has costs this source census does
not measure. Avoiding4.392% of this one class of reads is not avoiding4.392% of
render time. No claim that a prospective implementation is faster or slower is
made. Original Carmack height-copy/fractional/x86 scaler incompatibilities remain.

[Per-pose CSV](results/census01/poses.csv),
[receipt and source pins](results/census01/receipt.json),
[checksum manifest](results/census01/SHA256.json),
[retained owner advice](results/source01/WOLF-POST020-ADVICE-2026-11-07.md).
This source gate closes the selected investigation before candidate code; no
physical lease, firmware/consumer default or running019 input was changed.
