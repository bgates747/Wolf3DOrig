# Local narrow-division proposal; no implementation selected yet

Goal05 source-design question. PERF008's generic libgcc candidate remains
blocked by allocated44B .eh_frame. Do not strip it, change admission, link a
private ROM address or relabel an unqualified SDK provider as supported.

The present freestanding local divide_u64 explicitly handles denominator0,
then runs a64-iteration wordwise restoring division. Existing __divdi3 performs
unsigned magnitude conversion/sign restoration around it; all of that remains
current behavior. The original ray restoration removed the historical per-ray
reciprocal users. Live expensive wide division remains transform_point's
(int64_t(trans_y)*87)/trans_x for visible actor/static projection. Do not claim
512 axis divisions/frame or that this is dominant without current inputs.

A possible separate consumer-owned optimization: AFTER existing zero guard,
if unsigned numerator.high==0 and denominator.high==0, divide the two32-bit
low words using ordinary native unsigned division, zero-extend the result.
Keep the exact old64-step fallback for every other input and preserve signed
wrapper/zero/overflow bit-pattern behavior. Current target ELF already contains
ordinary QUOU/QUOS for existing32-bit wall operations. This is a proposal to
optimize the existing local body, not a claim that the blocked original library
method has become supported or a retroactive endorsement of its substitution.

Before selecting implementation, ask VDPlet for the pre-code/protocol boundary
and arithmetic/provider hazards. Need a separately frozen task/actual source
pins, independent mathematical and old-helper comparison over narrow/wide,
signed extremes/zero, and actual compiler lowering/dependency/sections/stack.
Ordinary renderer host builds exclude these native bodies and cannot provide
that proof. An extracted exact-body test must be identity-joined and rename ABI
symbols to avoid replacing the host's runtime; native32 division must emit an
admitted instruction with no helper recursion. Physical usefulness requires a
matched selected uncapped cohort with real static/actor projection inputs.

No helper code/build/test, runtime service, firmware change or new bench request
is authorized by this note alone. Preserve current16/14/15 source/candidates
and Mech priority. Generic provider qualification remains with its owner.
