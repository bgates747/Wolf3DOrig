# Projection input coverage PASS

Exact source/helper host diagnostic selected by a9ea6f4; implementation6aade57,
source bound62a7853 and owner PRJ-001 independently agree. Compiler346 serial
ASan/UBSan compile/run PASS in6.27s, all children exited and normal release
2026-11-07T12:09:09.927389+00:00; no next request. No device/emulator access.

|Population over600 poses|Retained E1L1 room|Eight-static fixture|
|---|---:|---:|
|Objects per pose|121|8|
|Attempted projections|72600|4800|
|Rejected before division|36608|2728|
|Actual-source signed-helper input pairs|35992|2072|
|Both magnitude high words zero|35992|2072|
|Wide fallback input pairs|0|0|
|Negative numerators|17972|1030|
|Accepted visible projections|28822|2000|
|Max numerator magnitude|221741598|7915347|
|Min positive denominator|22609|22849|
|Max positive denominator|2555068|98571|

The room supplies about59.99 helper inputs/frame; the eight-static fixture
about3.45. Every observed guarded input qualifies for the narrow branch;
static domain proof separately bounds every validated coordinate call. All
600 exact pose words cover300 distinct headings through two turns. This uses
the actual retained W3L static records/camera and existing sprite seed, with
actual setup_view/transform_point and independent fixed-point input arithmetic.
Both extracted exact native helper bodies equal the mathematical quotient on
all these input pairs; the actual transform's screen/height/acceptance agrees.
The million-pair helper-domain test remains separate.

Final original/candidate ELF literal0xEA4 (R_XTENSA_RELATIVE) and callx8 at0xF35
resolve to their own __divdi3 at0x2DBC/0x2DB4. The candidate's previously checked
zero/high-word guards and unsigned QUOU remain the only native helper change.
This joins the real native call destination, not native sampled branch counts.
Height projection uses a separate32-bit division and is not another avoided
64-iteration helper call. Former512-per-ray estimates remain obsolete.

[Raw receipt/source pins](results/projection01/receipt.json),
[observed output](results/projection01/coverage.log),
[source-domain proof](PROJECTION-DOMAIN.md).

These are host executions of real source and input values plus target code
binding. No native hit-counter instrumentation, full-domain Xtensa execution,
measured draw/FPS gain, exclusive CPU or physical result is claimed. The
ordinary room has the larger useful-call population, so a room-only bracketing
physical comparison is justified before any additional scene or numeric probe.
No production/provider/default adoption; generic libgcc remains blocked.
