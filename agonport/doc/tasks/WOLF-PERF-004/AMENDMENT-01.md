# Defined fixed-point scaling prerequisite

The original control failed before the fill candidate ran. Add a separately
recorded source-correctness prerequisite so ordinary sanitizer qualification
can exercise the intended arithmetic without suppressing the finding. This
is practical Wolf work under Smith's existing directly verified improvement
instruction, not a new performance mechanism or a silent row/API workaround.
Freeze this amendment before changing the prepared sources.

## Pre-code compatibility and intended computation

1. Existing operation: scale an int32 numerator by65536 in int64, divide by
   the unchanged denominator/helper, then apply the existing int32 return
   conversion. Negative `a <<16` is undefined in the target language version.
2. Proposed defined expression: `static_cast<int64_t>(a) * 65536`. Every int32
   input scales into [-2^47, 2^47-65536], entirely inside int64. The quotient,
   existing denominator domain and int32 return policy are otherwise unchanged.
   No float conversion, rounding redesign, divider replacement or new library
   is selected. This is a required safety correction to source semantics.
3. Existing target support: the same compiler already handles this constant
   scale and signed64division. No missing row/firmware/ABI operation is found.
   Confirm the generated target code instead of assuming its optimization.
4. Apply this one expression change to BOTH task-owned arms as a common
   prerequisite; keep the fill-loop difference only in the candidate. Preserve
   the untouched historical r01/source/module control and failed log.
5. Require the defined-scaling original target rebuild to match module1907
   byte-for-byte before accepting it as the physical control. If it differs,
   stop the existing measured-control comparison; no fallback or automatic
   baseline substitution. Candidate measurements still isolate the clear
   extent only if this identity and all correctness/resource gates pass.

## New finite revision

Prepare fresh r02 sources and outputs. Preserve r01 and record both transforms
in the source ledger/diffs. Retain all existing sanitizer checks. Add a small
actual-source arithmetic regression with independently specified signed and
boundary expected values whose quotients are representable. Zero denominator
and unrepresentable-return redesign are outside this selected change.

Use the same finite serial Pi build limits and normal fresh reservation.
Rebuild/check both host arms and target modules; compare full outputs, all-angle
two-page frames, geometry/service counts and unchanged target control bytes.
First unexpected failure still stops the revision without automatic replay.
No hardware work proceeds before a successful exact package/correctness freeze.

The frozen main plan remains unchanged. This amendment explicitly adds the
common source-correctness prerequisite and corresponding regression; all other
mechanisms, resource/ownership limits and default-adoption exclusions remain.
