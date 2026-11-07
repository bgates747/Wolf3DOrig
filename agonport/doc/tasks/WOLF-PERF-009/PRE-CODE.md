# Supported-method ledger before implementation

| Unit | Original / bespoke reference | Current c8f | Selected disposition |
| --- | --- | --- | --- |
| Wall resampling | Original post/scaler; bespoke private scratch/Canvas column | Texture-group acquisition, per-column nearest-neighbor fixed fraction, generic put_pixel per output | Preserve current resampling and group/lease order; this is local loop-invariant correction, not retrospective endorsement of Canvas-to-row substitution. |
| Destination mapping | Supported ABI1.6 scoped row pointers, native lane permutation and color/sync masks | Every output calls target_pixel/put_pixel with the same frame, x and masks | Supported scalar arithmetic. Select representation and map x once per column, retain rows[y] for each y. Never assume contiguous rows or pointer validity beyond current render scope. |
| Texture read | Existing retained64x64 bytes | source_y=min(fraction>>16,63), source_x=tex_u; index source_y*64+source_x | Same fraction start/step/rounding/clipping, same reads and ordered byte stores. Hoist source_x into texture-column base; no outside-lifetime pointer. |
| Pixel merge | Bytewise color&63 then color-mask, old-byte preserve-mask | Generic helper applies merge per pixel | Same scalar merge with masks bound once; arbitrary overlap masks remain valid. Linear output ignores native masks exactly as before. No wide stores or new firmware helper. |
| Other units | Original ray walk restored; sprite occlusion and provider are separate priorities | c8f original-ray candidate/local divider/O2 | Fixed. Do not combine division/provider, sprite painter, grouping, projection or viewport axes. |

VDPlet VDPL034 LIN-F002 and LIN-F003 distinguish support closure and hot-loop
work from presumed speed. Prior PERF005 hoisting measured a benefit for solid
spans, but does not establish textured-column savings. Compiler inlining may
already remove part of this work; inspect actual c8f/candidate target code and
report a zero/negative outcome honestly. The ABI already supports all operations
selected here. No unsupported original method is replaced to make this change.

Gate: source compatibility CLOSED for this limited scalar hoisting. Output,
actual package/resources/stack, provider identity and physical timing remain
qualification gates. Physical73's failed GET is a collection dependency, not a
reason to change renderer scope or a claim that this candidate repairs transport.
