# Bytewise span candidate passes host/control/code gates

Both arms pass existing arithmetic/renderer/module/error/lifecycle checks,
600-frame equality and98727 actual span/rectangle oracle cases under ASan/UBSan.
Six output pairs compare byte-for-byte, including51971104span/oracle bytes and
46080000scripted frame bytes. Mask pairs cover all65536colour/preserve values,
with varied per-byte originals, mapping, edge/zero counts, guards, independent
row addressing and unchanged linear behavior. Existing600frame scene-heading/
selected-page/modeled-page and host target-helper limits remain explicit.

Control target reproduces measured physical63 module54568 byte-for-byte.
Candidate SHA256bf7f2bb038387698464fbb297a437ef98457638a28261dc7f9688044d9b6eb28
is19896B (+20), resident text14344B (+20), resident data9732B unchanged,51relative
relocations unchanged. Exact rodata contents agree, bss size5496B agrees,
all41source stack entries remain at most736B, fill_span32B unchanged. This is
not a whole-command firmware stack bound; hardware INFO gates remain necessary.
Same Os/PIC/fno-builtin/PSRAM workaround/compiler/policy/providers/ABI1.6 and
capabilities257, no math/helper/library or other renderer-method change.

Actual direct-row loop has no CALL instructions. Row, bias/XOR, mask and encoded
colour setup precede it; each pixel uses L8UI, AND/OR, S8I and the retained two
MEMW barriers. The unchanged put_pixel still has its target_pixel call for
other drawing paths. Control's direct fill loop calls put_pixel, which calls
target_pixel and repeats generic field/mapping work. Linear path remains one
setup call and byte loop. Pixel stores were not widened. Disassembly, maps,
full provider/symbol output and source patches are retained; generated-code
work reduction predicts no specific physical speedup.

One precise private-code qualification: the native candidate emits row-table
loads before its loop-exit check. Its only exact native call sites are
compose_background with count320 and fill_rect after left<=right with
right-left+1>=1; zero count is unreachable there. The control's emitted linear
loop likewise has no entry zero check. Host actual-source null-row/invalid-y
zero-count regression passes; the source candidate guards count0 before row
lookup. Do not claim an exported generic native zero-count entry or use this
artifact outside the admitted private callers. Compiler caller specialization
is an inference, not a separately retained optimizer trace. The actual module/
frame contract remains the qualification domain.

Compiler271 asserted before every child; all gates pass in60.05s, peak54.55C.
Owned children joined and271released22:55:02UTC,nextnone. R01 test-formatting
compile failure remains retained, without warning suppression. Source/package
checks do not establish physical speed, pixel scanout or a newly supported ABI
mode. No hardware/emulator/default deployment occurred. Exact current owner
context/normal reservation, frozen fresh cohort and independent restore/readback
remain before physical timing. R02-BUILD.json retains exact hashes/code/stack.
