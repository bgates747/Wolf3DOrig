# Final12857 divider prefix inspection

ELF32 little-endian, divide_u64 at0x3C88,48B frame. Entry arguments are64-bit pairs: numerator a2(low)/a3(high), denominator a4(low)/a5(high). The high numerator is retained in a6 before a3 is reused.

0x3C8D ORs denominator words into a8.0x3C8B/3C92 set low/high result registers to allones;0x3C94 branches to the common return when denominator0. Therefore QUOU is never evaluated for zero.

0x3C97 ORs denominator.high with saved numerator.high into a3;0x3C9A branches to the old wide body at0x3CA2 if either high word is nonzero. On the narrow fall-through, a3 is0.0x3C9C executes QUOU a7,a2,a4 (unsigned low/low);0x3C9F reaches common return0x3D5C, which copies a7 into return low a2 and retains high a3=0. Thus narrow results are zero-extended, including unsigned values aboveINT32_MAX. The function has no CALL/CALLX and no recursive helper path.

The remaining wordwise body and signed magnitude/sign wrapper are source-identical to the accepted control; final compiler/provider policy is unchanged. Actual old/candidate native body tests execute independently on the host and preserve exceptional bits. This instruction/dataflow review is target artifact evidence, not full-domain Xtensa execution. Physical common-input/path coverage and timing remain separate gates.
