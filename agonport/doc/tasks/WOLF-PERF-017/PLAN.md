# WOLF-PERF-017 — Narrow fast subset in the existing local divider

## Pre-code support boundary

Exact independent a926 control remains separate from sprite972f/cyan22ef/
cache8c126c/trig2844. Source pins include native and production helper copies,
renderer, actual package and VDPlet's DIV001–003 advice/pins. Existing target
core XCHAL_HAVE_DIV32=1 and QUOU/QUOS in the accepted ELF support ordinary32-bit
integer division without a new API. Final candidate must itself lower to QUOU,
not a recursive or unadmitted helper. Keep PIC/PSRAM policy and all loader guards.

**PERF008 remains blocked:** its generic libgcc artifact has44 allocated unwind
bytes. This arm optimizes an existing local implementation, not the unavailable
original provider. Do not strip metadata/import ROM/relax admission, claim
original-provider parity, or retrospectively approve the port's method change.
Owner source advice finds the guarded local subset compatible; it assigns no
new peer build, firmware, target or review work.

## Exact arithmetic and intended work

Keep denominator0→UINT64_MAX first. Then, only if BOTH unsigned high words are0,
perform uint32 low/low and zero-extend. The nonzero divisor is already proven;
unsigned values2^31..2^32−1 remain valid. Do not narrow general64/32 operands
merely because their quotient might be small. Every other operand enters the
old64-iteration body without edits. Keep unsigned magnitude conversion,
wordwise negation and signed result restoration unchanged, includingINT64_MIN.

Compare bit patterns for zero divisors and signed overflow: existing signed
nonnegative/0→allones, negative/0→1; INT64_MIN/−1 keeps its existing pattern.
Never evaluate a C++ division expression for those exceptional oracle cases.
Retain pinned target/compiler interpretation of union words/out-of-range signed
conversion; do not claim new ISO portability.

Use both an independent mathematical quotient for defined inputs and exact old
body comparison. Join extracted test bytes to real source; rename ABI symbols
so they cannot replace the host runtime or recurse into an oracle. Test directed
0/1/2,2^31±1,2^32±1,2^63±1,UINT64_MAX, equality/multiples/remainders/signs,
explicit exceptional bits and seeded narrow/wide partitions. This is not an
exhaustive64-bit-pair proof. Renderer HOST_TEST excludes these bodies and alone
is insufficient. Actual ELF provider/QUOU/branch/call/stack inspection and a
selected physical native-use/coverage case remain necessary.

Live wide projection remains (int64(trans_y)*87)/positive trans_x after its
minimum-distance guard. Preserve widening. Earlier512ray-division counts became
obsolete after original tangent-ray restoration. Measure actual static/actor
inputs, fast/fallback hits, extra branch and call work; no assumed dominant cost
or cycle count. Keep any observer separate from the timed uninstrumented arm.

Actual85 completed and released; see [RESULT85.md](RESULT85.md). Pooled draw
change2.125% with3.111% control drift, no demonstrated presented-rate gain.
Qualified local candidate retained; generic libgcc gate and default adoption
remain separate.

For all Olimex bench procedures, use the sole authoritative [bench guide](/Agon/mystuff/agon-extender/docs/operations/olimex-bench/README.md).
