# Isolated aligned byte-span qualification

Compiler408 completed all34 serial compilation/check steps in123.509 seconds.
ASan/UBSan remained enabled, peak CPU temperature was56.2C, every owned child
joined, and the compiler lease released normally with no next request. No device
or emulator was contacted. The source candidate is correctness-qualified; its
physical speed and resource-query results are still unmeasured.

|Package|Exact SHA256|Bytes|Resident data|Resident text|
|---|---|---:|---:|---:|
|Combined control|8d3d19bb74e1f2ea862b2154c038dfd23de2fd741fd1831d1880d849b5ad838b|22572|11184|15676|
|Aligned byte span|b181a8fdba5b0e0791359593e95169a99ad732e369cbb9442be1e4046baed1d4|22620|11184|15724|

The control reproduced exactly before candidate qualification. The only source
insertion is the supported complete-quad direct-row specialization: constant
colour, XOR0..3, aligned start/count, conservative nonwrapping end. Source early
zero return, entire linear path, scalar fallback, per-span/row/call painter order,
asset lease/callback ordering, masks and PSRAM policy remain unchanged.

Each arm passed74755 independent actual-private-span oracle cases, including
all65536 mask pairs, partial quads, arbitrary XOR/bias, safe initial uint32 wrap,
zero before row fetch, destination-row aliases and overwritten target-metadata
aliasing. Each also passed1176 original globally ordered background/alias cases,
the retained98727 span/rectangle cases, renderer error matrix and module lifecycle/
retry/recovery/direct-copy parity. All600 host-fixture frames, states, geometry,
module frame and span outputs match the exact control and prior combined output.
These600 host frames cover300 scripted degree headings in the retained host
fixture, not an independently executed canonical hardware map or all360 headings.

The extracted actual candidate predicate passed19584 boundary-domain cases,
including468 admitted original-address sets. End-overflow controls refused the
fast path without ever constructing invalid row pointers. This is separate from
actual valid-storage span execution; the guard is not row-allocation admission.

Actual ELF inspection identifies an8-instruction eligible pixel loop versus10
for the scalar loop. It retains one L8UI, masked update, one S8I and following
MEMW per byte; no wider access or helper call was introduced. Scalar fallback
opcode counts and the linear loop remain. The span's individual frame remains
32B. Private target callers have positive counts; host execution of the preserved
source zero return is not claimed as a separately executed zero-call Xtensa path.
Instruction count is not a cycle measurement or physical hit-count claim.

Safe O2/PIC/fno-builtin/PSRAM flags, ABI1.6/capabilities257, sections/relocations/
providers and image/data/text/resource admission all pass. Full native modules
and numeric bodies are unchanged from the qualified combined control. Selected
wall/acquire module/task bounds stay1488/2048B and1936/4096B; selected background/
span bounds stay880/2048B and1264/4096B. These are ordinary synchronous source
paths, not universal IRQ/error/foreign-callback peaks. The512B cumulative INFO
floor still applies to later physical work.

The source census's98.918% eligible constant-fill byte coverage and static loop
savings justify a separate uncapped comparison; neither establishes speed yet.
Package cost is48B, resident data unchanged. Real per-arm eZ80 producer bindings,
host/controller freeze and fresh Mech-first physical admission remain required.
No default adoption, sprite013 decision or firmware/helper/provider change.

[Build receipt](results/build01/build-receipt.json),
[byte-loop audit](results/build01/byte-loop-audit.json),
[selected stack](results/build01/nested-stack-source.json),
[compiler release](results/build01/release408.json),
[109 frozen inputs](results/build01/frozen-inputs/index.json),
[archive manifest](results/build01/SHA256.json).
Large host executables/frame streams remain in build/r01; their actual hashes,
pairwise output equality and unchanged source inputs are retained in the archive.
