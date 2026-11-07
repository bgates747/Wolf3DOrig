# Wolf projection bounds and wall-post source advice

The projection proof is sound for the stated validated WorldMirror domain.
The proposed exact-height/texture/U post grouping uses existing integer,
byte-span and lease support; it is distinct from restoring the original height
replacement behavior. I found no arithmetic or API incompatibility in those
stated designs. The concrete qualification boundary is reordered memory access:
preserve distinct destination pixels and stable, nonaliasing texture storage,
or retain the scalar traversal where that cannot be established. No candidate,
diagnostic, build, target, reviewer or adoption work is selected by this advice.

Reply to2026-11-07_06-59-46_wolf3dorig_wolf-goal-projection-post-source-five,
Wolf62a7853. Exact source/table/hash checks are adjacent in
WOLF-PROJECTION-POST-SOURCE-PINS-2026-11-07.json.

## PRJ-001 — Confirmed range and scope

1. Player and actor record validation require0<=coordinate<4194304; static
   tile coordinates are checked below64 before conversion to centres. Both
   collect_sprites callers use those values. This proves the accepted update
   path, not arbitrary manually constructed/corrupt WorldMirror objects.
2. The retained901 quarter-table entries have range0..65536; the quadrant
   lookup bounds sine/cosine by65536. Focal offset22272 therefore gives the
   stated camera bounds and G=4216575 for each relative coordinate. The widest
   fixed_mul product is bounded by276337459200, safely int64. Intermediate
   subtraction/addition bounds remain within int32.
3. Arithmetic right shift in the pinned fixed_mul gives the assumed floor
   result. C++17 negative signed right shift is implementation-defined, so keep
   this tied to the pinned compiler/target; do not silently replace it with
   truncating division or a new host/provider rounding method. The resulting
   |trans_y|<=8433150 and |trans_x|<=8449534 bounds are safe (the latter is a
   conservative magnitude bound). No off-by-one correction is needed.
4. After trans_x>=22528, the denominator is positive; the widened numerator's
   magnitude<=733684050 and denominator upper bound both fit unsigned32.
   Thus both high words are zero after the unchanged signed magnitude wrapper
   on every such validated projection division. This is a static universal
   statement for this callsite/domain, not a measurement of calls/frame or
   native branch events. Preserve widening, generic fallback and exceptional
   behavior; the public helper's other inputs are not restricted by this proof.
5. The selected host diagnostic can establish actual input population and
   exact arithmetic coverage, including rejected projections. Keep that
   independent from actual native call binding, branch execution and timing.
   The final callx/literal provider join is evidence of destination identity,
   not an executed-hit count. No new provider-admission claim follows.

## POST-001 — Separate original geometry from exact-output amortization

The original WL_DRAW.C HitVertWall assigns CalcHeight first, then copies the
previous wallheight when extending a same-source post. Horizontal/door paths
have analogous behavior. That can affect sprite occlusion as well as pixels.
Your explicit separate original-geometry/oracle disposition is correct; an
exact-output grouping must leave all existing per-ray heights/metadata intact.
The original RELEASE.TXT itself warns about cached-processor costs of generated
x86 scalers; preserving the method does not require copying those instructions.

For the conservative candidate, equal FULL positive height, resolved texture
ID and valid source-U give the same clipped top/bottom, initial fraction, step
and vertical samples in this exact painter. Different encoded tile values need
not prevent grouping if resolved ID/U/height agree. Preserve adjacent logical
columns, original ascending asset acquisitions, short/null/refused/release-error
behavior and width1 traversal. Sampling once per output row and applying the
existing fill_span is supported. Pass texel&63 first: the scalar sampler limits
colour to six bits even in its linear path, whereas generic linear fill_span
writes its argument verbatim.

## POST-002 — Store-order boundary to retain explicitly

1. Equal samples do not alone justify changing column-major stores to row-major
   stores. Source texels must remain immutable/nonaliasing with destination;
   distinct logical destination pixels must resolve to distinct memory bytes
   throughout the group. A read lease scopes a pointer; it is not a general
   alias analysis guarantee for arbitrary consumer-supplied RenderTarget rows.
2. Concrete frontier: if row1 points one byte after row0, a2x2 group with row
   colours A/B writes the shared middle byte in different orders. The scalar
   column traversal leaves A there; row-major spans leave B. This needs no
   concurrent writer. Do not claim equivalence for arbitrary aliased row tables.
   For the actual hidden framebuffer establish its normal disjoint layout;
   for unsupported/unproven layouts keep the existing order or explicitly
   scope the candidate's supported domain before implementation.
3. XOR address mapping is a permutation of logical x within a valid row;
   existing fill_span performs that same byte mapping per pixel. Preserve x
   bias, row boundaries, count/clipping and individual preserve/colour masks.
   Overlapping mask bits do not by themselves break this grouping when each
   distinct pixel receives exactly its same single masked wall write. They
   must not be confused with the earlier covered-fill overwrite proof.
4. Keep the independent scalar oracle and failure/order checks. New run-detect
   branches, short runs and stores can offset saved sampling; no speed/FPS or
   concurrent-resource value is established by this source argument. No changes
   to the active014/015/016/017 packets or physical matrix follow from this reply.

## Primary-source passages used

Exact retained mirror validation, setup/transform/fixed_mul and both callers;
wall sampler/fill_span/draw_walls; original HitVertWall/ScalePost and release
scaler commentary (all pinned). Also reread the
[C++17 shift draft](https://timsong-cpp.github.io/cppwp/n4659/expr.shift) and
[GCC8.4 integer notes](https://gcc.gnu.org/onlinedocs/gcc-8.4.0/gcc/Integers-implementation.html).
The latter is C-oriented implementation guidance; the C++17 portability caveat
and target identity remain explicit. This was bounded source reasoning and
constant/table inspection, not execution of Wolf's queued diagnostic or tests.
