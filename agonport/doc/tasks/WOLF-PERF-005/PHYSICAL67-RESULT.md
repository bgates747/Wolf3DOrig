# Span invariant hoisting cuts draw time by45.83%

The bytewise span candidate reduced mean VDP draw time from
68.3236ms to37.0105ms,
saving31.3131ms per completed pose. Unpaced completed
fixture throughput rose from13.9274 to
24.6949FPS (+77.31%). This is the separately
matched span change against the already-corrected lower40-clear control.

| Frozen module | Draw ms | Module scope ms | Complete-command ms | Completed fixture FPS |
| --- | ---: | ---: | ---: | ---: |
| Control54568 |68.3236|68.7925|68.9054|13.9274|
| Spanbf7f |37.0105|37.4806|37.5999|24.6949|

Draw measures the established VDP draw bracket after command arrival, through
draw completion; it includes preemption/service waits. Local scope/command are
the existing surrounding brackets. Native ms use configured240MHz, FPS uses
unchanged nominal1kHz PRT and every completed pose. Independent nominal120Hz MOS
gives13.9023/24.6575FPS.
No external calibration, optical scanout/latency or ordinary gameplay trial.
Asset loads/module selection/probes/SD collection are outside measurement.

## Matched physical evidence

Actual67 ran corrected freeze8ae4a54/277pins/kit6a7fde79, exact modules54568/bf7f,
native7593, same runtime/SDK/compiler policy/carrier/clock/observer/scene work.
Two controls followed by original/candidate/candidate/original600-pose runs
supply1200samples per arm and2400total, no skipped/coalesced poses.

| Measured case | Arm | Draw ms | Completed fixture FPS |
| --- | --- | ---: | ---: |
|03|Original|68.3661|13.9214|
|04|Candidate|37.1803|24.5932|
|05|Candidate|36.8407|24.7975|
|06|Original|68.2811|13.9334|

Paired original-minus-candidate mean draw savings are
31.1858ms and
31.4404ms; second pair reverses
execution order. Samples/headings/revolutions are deterministic and correlated,
not statistically independent. RawPRID0xCDCD throughout is interpreted
under the pinned SDK as PRO/core0. E1L1 tile34,36 center34.5,36.5,720degrees/
600poses/300distinct integer headings, no enemies, fixed HUD/weapon, two warmups.
This is an unpaced capacity run rather than the20second paced fixture.

All six guests pass470loads/952fences/zero loading errors/timeouts, normal return,
mode0/callback0, original registers/timer/stack restoration and whole records/
angles/index/order/counter-wrap checks. Seven resource probes show zero live
slot/lease and minimum whole-command stack1956B (refusal512B).
Cumulative/non-atomic memory halves are not per-call peak attribution. All six
module replacements verify previous/selected/backup bytes, explicit supported
RECOVER3 and final target-only state1. No journal/guard/runtime workaround.

## Producer correction and interpretation

Stopped65 remains immutable/restored/released. It exposed the real fixed-length
eZ80 producer truncating19896B bf7f to19876B, loader IMAGE10 before INIT. Its
preserved RAM independently confirms LOAD19876. Whole-file SD staging and
intrinsic module tests had missed this composition boundary. Corrected actual
per-arm guests reproduce original control/unpaced binaries exactly and change
only six immediate length bytes per candidate binary (PACKAGE_BYTES19896,
strict LIMIT19897). All source/listing/file/header/read/upload/LOAD joins and
shared SP observation addresses are independently checked and pinned. Actual
per-case dispatch receipts bind the installed module to its corresponding
staged/loaded producer. Source/timing loops/assets/observer otherwise match.

The candidate changes only bytewise direct-span invariant setup: row/address/
mask setup moves before the loop, which retains masked byte reads/stores and
two generated MEMW barriers. Linear path and other pixel callers stay fixed.
98727host span/rectangle oracle cases and six outputpairs, generated code/
PSRAM/provider/resource checks retain GUESTS02/R02/M4/M5 limits. In particular,
source/host zero-count coverage is broader than the private native positive-
count call domain; no generic exported native zero-count service is claimed.
Host pixel equivalence is not a new physical framebuffer capture.

The matched result establishes this implementation's measured saving; it does
not attribute the remaining time to dispatch, math helpers, background pixels,
textures or a pure call-overhead share. The earlier clear-only correction's
physical63 candidate measured68.5399ms; this cohort's identical control measured
68.3236ms. Earlier bespoke30.7010ms is historical separate-cohort evidence, not
a freshly matched comparison or achieved30Hz. The current candidate still
averages37.0105ms of draw work and about40.49ms per completed pose;30Hz is not
established by this result. Production/default adoption remains separate.

## Exact restoration and release

The complete incoming1105920B profile8 native app/touched-tail85f9 was restored
and independently read back. P4d9bcb/EMOSa25f/startuped403/listener0566 preserved;
rawmode0/callback0/route0/files/rootCLI/cursor/inputneutral/offlineidle/worker0/
freebothUSB/joined actors pass. Actual67 released2026-11-07T00:18:33.631576+00:00; nextnone,
scheduler/VDPlet notified before detailed analysis. SD stayed mounted and all
Wolf target access stopped. No firmware/carrier change, uncertainty replay,
additional native install or default adoption occurred.

PHYSICAL67-RESULT.json retains aggregate/raw identities, six guest/producer/
module-selection receipts, seven probes, binary hash ledger, full restoration/
final observation/release. Full raw records and original SDK journals remain
under ignored build/hardware02/evidence. The inherited per-case analyzer's
generic clock text still says emulator; actual67 physical operation/identities/
restore are documented by independent hardware receipts, not inferred from that
stale label. All timing remains nominal/preemption-inclusive/uncalibrated.


Independent owner verification ba09212 rechecks all2400raw records/277inputs/
160binary pins and exact restoration/release, agreeing with every aggregate.
See INDEPENDENT67-RETURN.md for pinned review provenance. Core checks compare
entry/post-production raw IDs before logging; the single header retains only
the latest c0, not per-sample history or continuous migration proof. Source/host
zero-count coverage does not supersede the private positive-count native limit.
