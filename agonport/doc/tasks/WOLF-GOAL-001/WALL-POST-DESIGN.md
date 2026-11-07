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
