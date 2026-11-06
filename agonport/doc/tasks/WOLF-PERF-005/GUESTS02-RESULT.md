# Actual producer binding qualified

Four serial eZ80 assemblies and the real linked producer check PASS under actual
Pi compiler274;3.028s total, all children joined, released23:37:17.501176UTC,
nextnone. Original control/unpaced binaries reproduce the retained physical54/
63 producers exactly. Candidate source differs only in PACKAGE_BYTES19896 and
strict PACKAGE_LIMIT19897 versus original19876/19877. Both module packages stay
exact54568/bf7f; no module rebuild/padding/runtime change.

For each mode, candidate binary has exactly six changed bytes: low bytes of
five PACKAGE_BYTES immediate operands and one PACKAGE_LIMIT operand. Each
listing instruction is checked against its actual linked binary bytes: three
LD HL, two LD DE and one LD BC. The producer's MOS read/upload/VDPL LOAD paths
therefore use the selected exact module length/header; LOAD's high length byte
is explicitly zeroed. Original/candidate entry/exit-SP labels are identical,
so the existing post-run check's original listing addresses remain applicable;
all per-arm actual listings are separately pinned and rechecked.

The real stopped65 producer combined with bf7f is independently passed into
this checker and must refuse before target access. Source file identities are
compared across both arms; only the two equates normalize away. The whole
module file/header and source values are joined with actual guest immediates,
not inferred from successful SD transfer. Host/source/generated binary checks
do not claim physical LOAD execution, live wire identity or span performance.
Full receipts/source freezes/listings/binaries remain in ignored build/guests02;
GUESTS02-RESULT.json retains exact operands, hashes and byte differences.

The next hardware02 coordinator selects explicit arm/mode guest names from the
verified installed module hash, preserves the same sixguest/sevenprobe matrix,
resource/clock/observer/carrier and full transaction lifecycle. Returned startup
failure requires a prompt following the error, never an earlier CD/LOAD prompt.
RAM preservation precedes any LOAD; missing/corrupt optional diagnostics are
retained/recorded and do not prevent exact restore/handback. Derived controller/
listener composition and fresh frozen admission remain separate requirements.
