# Pre-code compatibility and work ledger

VDPL034 LIN-F003 identifies the original/bespoke column-level occlusion decision
and the converted renderer’s per-pixel wall-height comparison. This candidate
uses that report directly. It restores decision granularity within the existing
direct-row sampler; it does not restore a scratch bitmap or change sprite order.

| Unit | Existing method / supported API | Selected disposition |
| --- | --- | --- |
| Sprite acquisition | One checked64×64 texture lease per visible sorted sprite | Preserve order, bounds/error handling and release; no cached pointer after release. |
| Scaling and clipping | Fixed16-bit fractions and clipped screen rectangle | Precompute each clipped column’s min(source_x,63) once. Same start/step and integer operations; preserve y-outer sampling. |
| Wall occlusion | wall_height[screen_x] < projected_size per destination pixel | Decide once per column; byte0xff denotes occlusion,0..63 source coordinate. Preserve strict inequality/wall-wins-equality. |
| Storage | Exact retained DDA metadata and sprite arena in schema2 scratch | Do NOT borrow wall tile/side arrays: their post-render contents are contractual and checked. Use a bounded local256-byte column table; actual target stack/call chain must fit before physical dispatch. |
| Output | Supported borrowed rows with x bias/permutation/arbitrary masks, or linear destination | Keep actual put_pixel and byte merge unchanged; no new service/firmware, wide stores, layout or lease extension. |
| Painter/ties | Existing depth heap far-to-near | Preserve exact sort and overlap order, including equivalent-depth behavior; no tie-policy correction hidden in optimization. |
| Other work | Wall loops, projection, tangent ray walk, providers/O2/PSRAM policy | Fixed to exact a926 baseline. No compiler/library/helper/viewport change. |

Supported scalar C++ arithmetic and byte storage close the API gate before code.
A local stack table is a declared resource tradeoff, not permission to exceed
runtime stack admission. The source-level potential is up to height-fold fewer
column decisions/fraction calculations; compiler code and actual physical timing
must establish whether that is useful. Zero/negative results are valid.

Tests compare the actual candidate sampler against independent scalar equations
for clipping/occlusion/alpha/mapping, including partial/full offscreen sprites,
size extremes, equality ties, overlapping sprites, noncontiguous rows and guards.
The existing module/failure and600-pose oracle compare pixels, geometry and state
with exact unchanged original. Host arithmetic does not qualify native providers.
