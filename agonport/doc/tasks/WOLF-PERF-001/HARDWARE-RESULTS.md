# WOLF-PERF-001: first physical baseline

**Visible-repeat update:** WOLF-PERF-002 repeated the unchanged paced fixture
on hardware with an explicit start callout. The Author confirms the correct
room and both turns;201 presentations and near-identical counters reproduce.
See [visible review](../WOLF-PERF-002/RESULTS.md). Ordinary-game spin comparison
remains pending; these are fixture timings, not verified gameplay capacity.

On 2026-11-04, Olimex generation 26 completed the frozen three-arm cohort.
The stationary E1L1 player at tile (34,36), centered (34.5,36.5), turned
720 degrees through 600 scripted poses with no enemies. All three arms passed
sequence, timer restoration, code preservation, balanced stack and native mode-0
restoration checks. [Raw records and receipts](results/olimex01/) are retained;
all three reports reproduce exactly from the archived binaries.

| Arm | Completed | PRT ticks | MOS ticks | Nominal PRT rate | Nominal MOS rate |
| --- | ---: | ---: | ---: | ---: | ---: |
| eZ80 pose/serializer lifecycle, no UART | 600 | 1,301 | 158 | 461.18 updates/s | 455.70 updates/s |
| Unpaced hidden render, wait/accept | 600 | 49,206 | 5,916 | 12.19 renders/s | 12.17 renders/s |
| Paced render, C3 and ordered fence | 201 | 20,064 | 2,414 | 10.02 presentations/s | 9.99 presentations/s |

These are nominal clocks: PRT is interpreted as 1 ms/tick and MOS as 120 Hz.
No independent physical clock or optical calibration was performed. The report
JSON's inherited `clock_qualification` string mentions emulator; that generic
analyzer wording does not describe this cohort's execution platform. These
records came from physical hardware, with the uncalibrated-clock limitation
retained. Whole-host execution and retrieval durations are not denominators.

## What each processor is doing

The eZ80-only arm averaged 2.162 nominal ms per pose and serializer lifecycle
(p95 3 ms). Packing averaged 1.092 ms; lifecycle bookkeeping averaged 1.060 ms.
Pose generation is a scripted table lookup, not movement, collision, enemy AI
or populated-world simulation. CPU-mode `submit_ms` contains no UART traffic.
Thus approximately 461 updates/s describes this isolated camera workload only.

The complete unpaced path averaged 82.005 nominal ms per hidden frame, p95
83 ms, maximum 84 ms. Mean packing was 1.108 ms, submission 1.593 ms and
wait/accept 79.300 ms. Most elapsed time is on the rendering/reply side of the
boundary; the wait bucket includes transport, firmware service and rendering.
It cannot be equated with exclusive ESP32 renderer execution.

ESP32 inner-render CCOUNT averaged **18,781,443.74 ticks/frame**, median
18,749,942, p95 19,017,517 and maximum 19,084,792. Mean surrounding color-row
scope was 18,886,915.91 ticks and full module dispatch 18,897,093.53 ticks.
These nested intervals must not be added together. They include preemption and
service calls; no calibrated MHz or exclusive CPU-time conversion is claimed.
The inner renderer accounts for about 99.39% of the measured module interval.

## Cadence and spin-up

The paced arm selected the latest of 600 nominal 30 Hz poses and completed 201
presentations, coalescing 399 poses (66.5%). It reached final step 600, closing
both turns. The 200 measured presentation intervals averaged 99.76 nominal ms,
with median, p95 and maximum all 100 ms. The extra ordered presentation fence
averaged 7.657 ms. This is the instrumented fixture's cadence, including that
fence, rather than an optical display measurement or ordinary interactive FPS.

There was no meaningful first-turn penalty in this already-warmed workload:
unpaced mean active time was 82.007 ms in revolution one and 82.003 ms in
revolution two. Inner-render means were 18,782,533 and 18,780,355 CCOUNT ticks.
Paced turns retained 101 and 100 presentations with mean active times 99.614
and 99.800 ms. Two warm-up frames precede all timed samples, so this does not
measure cold-start costs.

## Runtime and comparison limits

The installed native VDP was the retained r2 diagnostic image, SHA-256
`8ade1e7dbc8b82cfbb20bfc92bdeb02e909c38c9f93c37723f9c9d409a9af7c4`.
It emits RX/TX diagnostics around VDPlet calls; end-to-end rates include that
logging. The inner CCOUNT bracket excludes those surrounding print calls but
still includes services and preemption. The task module itself was unchanged
from the accepted R06 emulator cohort, SHA-256
`27f3d39285a5b49fec8aeed35085b1916ef537154f1d1d53956b075e00174c82`.
Live ABI/capability/typed-result guards passed before measurement. Exact
component provenance is in [release.json](results/olimex01/release.json) and
[compatibility evidence](results/olimex01/COMPATIBILITY.md).

R06 emulator unpaced throughput was 22.68 nominal PRT renders/s; physical was
12.19 here. The runtime differs from R06/Rally's a50eb23a firmware, and the
emulator clocks disagree more strongly. This difference cannot be attributed
solely to emulation or pooled with Rally's race FPS. Rally's timer and recorder
method are reused, but workload and firmware equivalence are not established.
A clean-runtime, externally calibrated or optical result remains future work;
these measurements do not establish production-game FPS.

## Preservation and disposition

No firmware operation or reset was performed. Startup and listener were fully
read and compared on entry and handback. Native mode 0, original cwd, actual
CLI, neutral input, offline listener and free device handles were verified.
The SD card was left mounted. Central lease generation 26 was released at
15:40:12 UTC (10:40:12 EST), and Extender plus the queued 6502 chat were notified
before analysis. Full transport journals remain under ignored
`build/olimex01/evidence/physical-r01/`; portable outputs and local retrieval
hashes are archived above. Deployment used independent full GET comparisons;
local SHA hashes are not claimed to be device-computed output hashes.

WOLF-PERF-001-06 has collected the authorized physical cohort. Author acceptance
under WOLF-PERF-001-08 remains open, with the calibration and runtime limitations
explicitly retained.

## VDP-local call-to-return timing clarification

The recorded `module_ccount` already brackets the synchronous production
APPLY_AND_RENDER entry on the ESP32: read CCOUNT immediately before
`wp_production_entry(h,r)`, and again immediately after return. Record copying
and readout occur afterwards. The inner bracket directly surrounds
`render_world_direct`. Neither interval uses an eZ80 timestamp or includes
command transmission, RX/TX print calls surrounding dispatch, or the later C3
presentation. The module interval excludes runtime admission before entry and
runtime automatic cleanup/reply after return; it is not the complete interval
from packet receipt to reply.

At the retained source configuration's nominal 240 MHz, the unpaced physical
records imply **78.738 ms mean production module call-to-return** (p95
79.734 ms, maximum 79.990 ms), including **78.256 ms mean inner rendering**.
This is approximately **12.70 module calls/s** before transport/presentation.
Conversion is conditional on the installed CPU actually running at 240 MHz;
that frequency was not independently sampled or calibrated in this cohort.
Raw cycles remain authoritative. Source snapshot support is not an exact
reproduction of the installed image, as documented above.

Thus local VDP timings, rather than just the eZ80 wait bucket, already support
an approximately 79 ms render call under this diagnostic runtime. Removing
surrounding serial logging cannot by itself remove this measured interval.
Logging could still influence system state or subsequent scheduling; observer
and clean-runtime controls have not been performed. No additional physical
run or firmware operation was made for this clarification.
