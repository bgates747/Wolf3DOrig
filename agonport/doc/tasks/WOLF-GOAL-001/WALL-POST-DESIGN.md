# Wall-post scaling: next-method disposition

Source-only progress on WOLF-GOAL-001-06. This selects no new implementation,
compiler child, numeric/graphics probe or physical matrix. Preserve active
H02/017 packages and all prior candidates. This is harder/less certain than
those already qualified arms; measure them first.

Carmack's HitVertWall first computes CalcHeight, then when the same wall side,
intercept tile, tile value and texture column continue, widens postwidth and
replaces the new column's wallheight with the previous column's height.
HitHorizWall and the door paths have corresponding grouping. ScalePost samples
a column and draws the wide post. This saves sampling/setup, but the literal
height replacement can change both wall pixels and the heights used for sprite
occlusion. Current a926 computes every ray's projected height independently.
Consequently this original behavior needs an explicit original-geometry arm
and oracle; it cannot be reported as output-identical invariant hoisting.
Original x86 generated machine-code scalers cannot be copied as Xtensa code;
the original source itself warns about their effect on cached processors.

A more conservative consumer-local candidate would group **adjacent** columns
only when all already-computed positive full heights, resolved texture IDs and
source-U values match. No per-ray metadata or height changes. Keep current
ascending texture acquisition/order, refusal/bounds/release semantics and one
lease per needed texture. Width1 keeps the existing optimized column path.
For width>1, sample each identical vertical texel once and invoke the existing
bytewise fill_span for that output row. Do not use wider stores or retain row
pointers beyond current frame/lease; existing PSRAM policy remains.

Compatibility/intended-work gates before any candidate code:

- Existing frame rows, colour/preserve masks, mapping bias/XOR and fill_span
  already support bytewise horizontal spans. No firmware/API/helper extension
  is needed for this local grouping. This does not resolve the historical
  Canvas-to-rows conversion-method divergence or certify literal original posts.
- Match exact **full** height before clipping; equal clipped destination height
  alone is insufficient because fractional texture phase/step may differ.
  Keep top/bottom clipping and fixed-point fraction/step byte-identical.
- Existing wall sampler limits source texel colour to six bits even for linear
  output. Pass sampled_colour&63 to fill_span; passing raw arbitrary texture
  bytes would change semantics under nonstandard masks or high input bits.
- Never require equal encoded tile values when current resolution gives the
  same texture ID, but preserve all tile/side/U/height metadata. Conversely do
  not merge columns only because their bytes happen to look alike.
- Grouping changes internal column-major stores to row-major stores. Correctness
  depends on stable asset lease and distinct destination pixels on the current
  hidden framebuffer, without external writers; masks and mapping must remain
  exact even with permuted rows, XOR, arbitrary/overlapping masks and guards.
- An independent column sampler must check generated runs, splits, clipped and
  very tall heights, boundaries, odd widths, failed assets and painter order.
  Full renderer/module/state/geometry/frame parity and actual target byte-store/
  helper/call/nested-stack/provider/package/producer checks remain required.
- Count opportunities using real room and actor-rich geometry separately from
  timed uninstrumented arms. Extra run-detection branches, remaining per-ID
  scans, unchanged pixel-write count and short runs can outweigh saved samples.
  No speed estimate or default adoption follows from this source argument.

Relevant source: retained a926 production/wolf3d_renderer.cpp cast_walls,
sample_wall_column, draw_walls, fill_span; original WL_DRAW.C HitVertWall/
HitHorizWall/ScalePost and RELEASE scaler caveat. Exact pins adjacent.

## Further original-scaler compatibility boundaries

A fresh WL_SCALE.C review adds three concrete boundaries to the later-method
inventory. ScalePost interprets wallheight with fractional low bits, masks with
0xfff8, halves the index and clamps maxscaleshl2 before a generated scaler
lookup. SetupScaling builds one scaler per two pixels and shares some larger
entries in steps of three. The current renderer treats its height as an integer
pixel extent; copying those index operations directly would mix units.

BuildCompScale forward-maps each of64 source rows into screen intervals using
floor(src*height/64), centre placement and clipping, then emits x86 byte loads
and repeated VGA stores. Current sample_wall_column instead inverse-maps output
rows with its fixed texture-step accumulator. Even an implementation of the
same physical wall height can differ at texel boundaries. Source-generated x86
machine code and segmented VGA mapmasks are unavailable as-is on Xtensa rows;
those incompatibilities must be marked before claiming a faithful method port.
The original RELEASE explicitly recommends a looping texture mapper on cached
486+ processors, rather than treating dynamic code generation as universal.

The VGA post masks have four start-plane choices and widths1..8. A row-backed
implementation must establish its own valid-width/domain contract and cannot
silently use an arbitrary-width row loop as proof of identical original VGA
behavior. These are source review findings, not new speed/correctness defects
in a926 or an assignment to implement a workaround. An exact original-scaler
restoration would need its own unit conversion, forward-interval oracle and
intentional image/occlusion-difference qualification before performance work.

## Owner advice: destination alias frontier

VDPlet POST-001/002 confirms the existing byte-span support and exact full-height/
ID/U/texel&63 constraints. A lease does not by itself prove source/destination
nonaliasing or distinct destination bytes for arbitrary row tables. If row1
begins one byte after row0, a2x2 group with row colours A/B leaves different
values at the shared middle byte under column-major and row-major order.
That is a concrete counterexample even without concurrent writers. Establish
the actual framebuffer's disjoint rows and stable/nonaliasing source extent,
or retain the old order on unproven layouts; do not claim arbitrary aliased-row
equivalence. Overlapping colour/preserve bits alone are not a problem for this
same-single-write grouping, unlike the covered-fill overwrite proof. This is
source advice, not a selected fallback implementation or a new test matrix.
[Advice and exact pins](results/source-advice-07/WOLF-PROJECTION-POST-ADVICE-2026-11-07.md).
