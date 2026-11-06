# Hardware03 — corrected recorder, recurring loading-query failure

The recorder-lifetime correction builds and its exact native control method
passes ASan/UBSan repeated-lifecycle regressions. Pi177 was released, then
fresh actual Olimex42 admitted the1052-pin kit. All shared assets and staged
executables passed independent reads. New nativeA c5cfaaed91a0d294bbe30811ca57ff36a585d070946f0813a469412f57d77fcc
was independently verified after its app-only/tail write. B artifacts unchanged.

Three fixtures passed; the fourth failed during loading before any timed or
warmup render. No B image/guest/INFO probe or successor was invoked.

| Completed work | Raw counters | Result |
| --- | --- | --- |
| A intentional timer-restoration control | Normal restored/MOS return | Pass |
| A CPU600 | 676 PRT ticks /80 MOS ticks | 887.57 scripted poses/s; pose+pack mean1.113ms |
| A unpaced600 | 19818 PRT ticks /2382 MOS ticks | 30.2755 completed hidden renders/s |

Native draw mean30.714ms, median30.687ms, p9532.846ms, maximum33.146ms at the
source-configured240MHz. Complete unpaced frame-cycle mean33.023ms, median33ms,
p9535ms, maximum36ms.237/600 recorded cycles are34ticks or more; PRT granularity
is1nominal ms, so this is a quantized budget observation, not exact deadline
qualification. The CPU/VDP costs clearly differ, but average unpaced throughput
does not establish steady30Hz visible presentation. CPU fixture excludes normal
populated-game simulation. Source clocks are nominal, not externally calibrated.

These clean-lifetime measurements replace the earlier provisional A data for
this identified arm, but the matched A/B/B/A comparison remains incomplete.
The CPU0-to-next-render transition succeeds; hardware qualification of a
full600-to-next-warmup transition was blocked by the subsequent loading failure.
The exact native-control host regression covers that transition separately.

## Loading failure: ten waits, no recognized mode reply

Fourth invocation A paced aborts at HUD record37 / total418 with AGNB14 and
loading-error1. Actual MOS return observed; PRT/wp_run never started. The saved
48B WPL2 record reports:

| Field | Value |
| --- | ---: |
| Started loading fences | 845 |
| MOS0x41 timeout returns | 10 |
| Recovered fences | 0 |
| First timeout elapsed | 28 raw MOS ticks (~233ms nominal) |
| Whole failed fence elapsed | 294 ticks (~2.45s nominal) |
| Last A / pass count | 15 /10 |
| Phase | 1: after first-page paint/C3, before second-page paint |

Only one mode query was emitted and the same pending flag observed throughout;
no clear/resubmit/replay between waits. Ten-pass bound won before1200-tick limit.
Thus this is not explained by merely stopping at the first approximate MOS wait
expiry. A late reply beyond this observation is not ruled out; loss, malformed
parsing and receiver/callback behavior remain unseparated.

Exactly one non-ASCII byte appears in the fourth guest's entire serial capture:
0x86 at offset99474, immediately after the loading hint and beforeCLS/error.
It is the mode-query opcode. Saved RAM's query bytes at0x8b6c3 remain170086,
matching the executable. This supports a parser/framing question, not proof of
missing wire bytes or a particular layer. Native source normally sends mode
information for23,0,0x86; top-level0x86 can instead reach vdu_print/printer output.
Timed readByte_t can abandon an incomplete command; COMMS_TIMEOUT is200ms.
These are source possibilities, not a demonstrated timeout/byte-loss path.

## Preservation and release

The failed guest returned normally; no reset was needed. Host stopped further
dispatch, saved complete app RAM before any LOAD and retrieved loading.bin.
Original native20029942 app/tail restored exactly and independently read back.
Fresh mode0/callbackzero/CLI/startup+listener fullcompare/neutralinput/idleworker/
offlinelistener/freebothUSB checks passed. Olimex42 released00:50:55UTC Nov6
(19:50:55EST Nov5). Next actual requester MechAgon52187060d50a and Extender were
immediately notified; a new scheduler grant is required for successor access.
No Wolf target custody or actors remain. SD card stays mounted.

Evidence: build/hardware03/{kit.json,compile-receipt.json,host-lifetime.log,
source-checks.json,physical-summary.json,release.json}; evidence per-case
receipts/rawCSV;04-bespoke-paced/serial.bin;failure-collection/{ram.bin,loading.bin,
loading.json,decoded-anchors.json};flash-restore readback and fresh handback.
Exit0 of the recovery branch means restoration completed, not that the suite
passed; complete.json is absent and summary complete=false.

Source-only advice requested from Extender on installed EMOS TX/mode-flag path
and VDPlet on native parser/printer behavior. No new component implementation,
build, target access, blind replay or successor experiment assigned. The
physical setup fault is separate from both the fixed task recorder lifetime
and the older Flexe asset-loading stall. Next selection requires these findings
and an identified finite diagnostic plan.

## Source-owner disposition — native parser

VDPlet's source-only return `2026-11-05_19-59-22_vdplet_perf003-r03-parser-source-return-one`
independently confirms the raw86 context and exact retained parser source.
Four supplied source SHA256 values match locally (receipt parser-source-return.json).
Correctly consumed query arguments are not mirrored by normal VDU2: parameter
readByte_t calls pushEcho, and sendModeInformation sends a structured mode
packet. A loose top-level86, or one gathered as printable text, can instead
reach vdu_print and its DBGSerial printer output. Literal VDU1/27, console mode
or another producer must be excluded before that attribution is unique.

Two concrete incomplete-command paths exist:17 consumed but00 misses its200ms
parameter deadline, or17/00 consumed but86 misses the next deadline. Each abandons
partial parser state; a later86 is printable. Missing/otherwise consumed17 can
produce the same observation. These are compatible mechanisms, not established
wire loss or a proved timeout. Source shows C3 queues SwapBuffers and waits for
primitive execution; it does not intentionally discard/query-split the next
three contiguous already-buffered bytes. Permanent C3 blockage alone cannot
explain subsequent output from that same parser.

Wolf's exact-installed EMOS5735812 source inspection adds: RST18 invokes
EMOS_vdu_WRITE, backend0 sends each byte with blocking UART0_serial_PUTCH. PUTCH
waits CTS when enabled and retries finite UART0_serial_TX attempts until sent;
a single low-level TX timeout therefore does not by itself explain silent
byte skipping in this synchronous path. RST18 adjusts an HL pointer when MBASE
is nonzero, while __exec24 clears MBASE for an ADL program. No runtime MBASE or
per-byte transmit timing was captured, so neither pointer rewriting nor correct
wire timing is established from the retained descriptor alone.

The missing discriminant is actual sender/receiver timing and grammar state,
not another longer same-flag wait. A future task-owned loading diagnostic can
record the duration of the unchanged query/C3 transmit calls and relevant state,
but those are proposals requiring an identified finite plan/fresh checkout,
not newly selected tests. Do not replace the native parser, change clocks or
replay a render to disguise this setup failure. Installed-source advice from
Extender is reconciled below. No hardware access or new reservation initiated.


## Source-owner disposition — installed EMOS and next evidence

Extender return `2026-11-05_20-19-16_linux-extender_wolf-installed-query-source-return-one`
independently inspected the exact5735812 source present for42. Public41 observes
an existing flag for250000 iterations and returns15 on exhaustion; this is not
a calibrated second or a query identifier. Public40 clears the selected bits;
MODE handling stores eight fields then sets the mode flag. A same-type unsolicited
reply can satisfy that flag. Rewaiting emits nothing but cannot identify a reply.
The enabled synchronous PUTCH retries low-level TX expiry instead of silently
skipping that byte. Raw TX's carry result has a different contract. Neither
saved query bytes nor USB printer-mirror ordering establish UART arrival timing.

Retained guest source places the image callback after agnb_stream_data returns
with remaining zero and matching file/chunk bounds, consolidation, then bitmap
selection/creation. vdu_load_buffer emits a header then its declared block via
separate synchronous RST18 calls before returning. Thus no intended callback
inside an unfinished upload was found. This is a source ordering check, not
proof that the receiver consumed each declared payload or that no writer intervened.

The next evidence proposal is in LOADING-DIAGNOSTIC-DESIGN.md under003-16.
It preserves the existing sender calls and captures bounded RAM history around
upload completion, paint/C3 and query send/wait. Whole-call timestamps cannot
prove per-byte arrival or receiver grammar state. No implementation, compile,
new reservation or run was selected by this source review.

Bench43 is independently held by Extender under MechAgon ownership. Its newly
installed EMOS ROMb5a1f4aa/sourcec9c8b6b and P4app512d3591 differ from42; a generic
127-byte carrier fault remains under investigation. Those prefixes are context,
not qualified full pins. Future Wolf work must obtain the full current component
binding and fresh admission, including current rollback, addresses and public
API semantics. Generation42 artifacts/tokens cannot supply that admission.
