# WOLF-PERF-001 — first qualified emulator baseline

The physical cohort and subsequent unchanged, Author-observed rotation repeat
are reported separately in [hardware results](HARDWARE-RESULTS.md). The live-game
spin comparison remains pending.

The fixture now works on Oryx: fixed E1L1 tile **(34,36)**, centered player,
**720 degrees over 600 nominal 30 Hz quanta**, no enemies. All three R06 arms
pass their output, completion and normal-MOS-return checks. A fourth deliberate
abort confirms restoration of the borrowed timer vector. Oryx is released.

**True hardware frame rate remains unmeasured.** PRT and MOS disagree in this
emulator, particularly in the short CPU arm. These results establish a
repeatable workload and reveal where its emulated time goes; their nominal
milliseconds/FPS must not be presented as physical Agon speed.

## The two processors

| Measurement | Qualified R06 result |
| --- | ---: |
| eZ80 camera preparation and serializer lifecycle, 600 records | 1,300 PRT ticks; 112 MOS ticks |
| Same CPU denominator on nominal PRT / MOS scales | 461.54 / 642.86 records/s |
| All 600 ordered hidden-render completions | 26,454 PRT ticks; 2,868 MOS ticks |
| Completed hidden-render rate, nominal PRT / MOS | **22.68 / 25.10 renders/s** |
| Inner ESP32 renderer, mean local CCOUNT interval | **10,053,962 counts/render** |
| Complete production module dispatch, mean local CCOUNT interval | 10,104,318 counts/render |

The CPU result covers scripted pose assignment, dirty-state preparation,
packing and serializer retirement. It excludes enemy AI, movement/collision,
doors, pickups, weapon animation and populated-world simulation. Pose assignment
itself is mostly below the 1 ms timer resolution; its 0.013 nominal-ms average
is quantized and must not be advertised as a precise microsecond benchmark.
The broader CPU lifecycle averages **2.163 nominal PRT ms**, p95/max 3 ms.

The native brackets surround the real production `render_world_direct` call,
its colour-row scope, and production module dispatch. The inner renderer
accounts for about 99.50% of the measured dispatch interval. That locates work
inside the module; generic RUN admission outside it is not included. CCOUNT
intervals include service calls and possible preemption. They are raw local
counts, without an asserted physical clock conversion or exclusive-CPU claim.
Diagnostic log append is outside those brackets but inside end-to-end latency.

For this fixture the expensive side is rendering/completion, while eZ80
preparation has considerable relative headroom. Full-game CPU capacity remains
an unanswered, different workload.

## Stage timing and presentation

All values below are **nominal PRT ms**, with 1 ms sample granularity.

| Stage | CPU mean | Unpaced mean | Paced mean |
| --- | ---: | ---: | ---: |
| Pose/dirty visibility work | 0.013 | 0.007 | 0.012 |
| Batch packing | 1.117 | 1.097 | 1.098 |
| Submission / CPU lifecycle bookkeeping | 1.033 | 1.633 | 1.618 |
| Requested completion wait plus batch acceptance | 0 | 41.347 | 41.352 |
| C3 plus ordered INFO0 presentation fence | 0 | outside timing | 7.350 |
| Total active sample | 2.163 | 44.087 | 51.429 |

The CPU submission bucket has no UART traffic: it is serializer bookkeeping.
Actual submission includes transport/backpressure and ownership work. Wait
includes acceptance bookkeeping and overlaps the VDP's work; these are not
exclusive processor costs. Do not add native CCOUNT intervals to the eZ80
stages or subtract CPU observations to invent isolated physical render time.
All 600 unpaced active samples exceed 33.333 on this nominal PRT scale.

The paced arm runs through **2,408 MOS ticks** (20.067 nominal MOS seconds,
including final completion), versus **22,121 PRT ticks**. It presents **429**
completed frames and coalesces **171/600 poses, 28.5%**. Every submitted pose
has a matching successful native render; the final step is 600, angle zero.
There are 258 one-step advances and 171 two-step advances, with no larger gap.
The two revolutions contribute 214 and 215 completed presentations.

Its nominal presentation rate is **19.39/s on PRT, 21.38/s on MOS**.
Fence-to-fence intervals, excluding the first frame, have mean 51.530,
median 51, p95 52 and maximum 68 nominal PRT ms. All 428 exceed 33.333 on that
scale. These are parser/swap completion observations, not optical refresh.
The fixture uses production C3 presentation with an additional ordered INFO0
fence; it freezes simulation other than the camera and does not reproduce
every opportunity for overlap in the interactive game's scheduling.

Both complete unpaced revolutions are retained. Their mean active times are
44.070 and 44.103 nominal PRT ms; inner renderer means are 10,053,542 and
10,054,382 CCOUNT. There is no material first-turn penalty in this cohort.
The earlier successful R05 hidden-render arm measured 22.703 nominal PRT/s,
versus R06's 22.681, a difference below 0.1%. R05's paced output remains
rejected because its unused slots violated the format; it is not pooled here.

## Clocks and Rally comparison

PRT uses Rally's reload 72/divider 256/nominal 18.432 MHz configuration. MOS
uses its nominal 120 Hz counter. The MOS-seconds/PRT-seconds ratios are 0.718
for CPU, 0.903 for unpaced and 0.907 for paced. R05 CPU had the same 1,300 PRT
ticks but 150 MOS ticks instead of 112. A short empty 600-iteration loop reads
zero PRT ticks; this bounds that control below one timer quantum and is not a
measurement of all marker/logging overhead. No overhead is subtracted.

The chosen Rally direct-row full-race baseline reports **39.16 nominal PRT
completed frames/s**, pooled over two reversed-order 900-frame runs, against
36.28 for its bitmap arm. It also reports unresolved MOS/PRT disagreement.
Wolf uses its exact frontend/backend/UART-repaired firmware snapshots and the
same timer donor, making instrumentation and runtime substantially closer.

The workloads and boundaries still differ: Rally runs four native physics
steps plus a render/presentation per frame, a 320x120 road, traffic, sky and
HUD. Wolf has a 256x160 3D view with retained statics/HUD and no enemies;
its 22.68 result omits per-frame presentation, while its 19.39 paced diagnostic
adds a fence and follows a nominal 30 Hz pose timeline. These values do **not**
establish which physical game is faster or identify the source of a bespoke
versus VDPlet performance difference. A matched physical cohort is still needed.

Rally source: `AgonArcade/docs/tasks/RALLY-28/custom-vdp/direct-rows/RESULTS.md`.
Exact donor hashes are retained with this result.

## Qualification, repairs and evidence

Four focused host checks pass: exact two-turn arithmetic and unchanged level
sections; corrupt completion/output refusal; unchanged production assembly;
and partial paced-buffer/native-identity validation. Target qualification
requires matching native counts/angles, zero unused rows, restored timer,
normal UNLOAD/farewell/MOS return and zero backend fault counters. Before/after
audio code matches the application, and entry/exit stack pointers agree in
all three benchmark arms. The intentional abort produces no performance result;
it verifies timer-vector restoration and normal owned emulator shutdown.

Two recorder prerequisites were repaired only in task-owned copies. The
client's fixed module staging at 0x060000 overwrote executable audio code;
memory snapshots proved the exact Xtensa bytes and balanced stack. The task
now stages at checked 0x0a0000. Separately, assembler DS padding was 0xff;
the fixture now explicitly clears sample storage before timing. The original
production staging declaration remains a source-level hazard for follow-up.
See [the diagnosis](STAGING-DIAGNOSIS.md) and [rejected cohorts](PROGRESS.md).

The final Oryx checkout was generation **277**, request **3e2ec70caf7e**.
All four fresh JIT processes used dummy SDL drivers and bounded runners.
**83 retrieved files** matched source hashes. Fresh whole-host idle evidence
released custody at **2026-11-04 14:24:28 UTC**, with no queued successor.
Pi compile generations 54, 58, 61, 62 and 63 were also released. No graphical
review, physical deployment/run, firmware/default change or publication occurred.

Retained results: [CPU](results/r06/cpu/report.json),
[unpaced](results/r06/unpaced/report.json), [paced](results/r06/paced/report.json),
[abort control](results/r06/cpu-fail/runner.json),
[memory/stack integrity](results/r06/integrity.json),
[runtime/input identities](results/r06/profiles.json),
[retrieval hashes](results/r06/retrieval-sha256.json),
[release](results/r06/release.json). Each arm also retains raw binary samples,
CSV, runner record and backend statistics. Full UART/memory evidence remains
under ignored `build/evidence/r06/` and the immutable Oryx profiles.

The [physical runbook](HARDWARE-RUNBOOK.md) and local hardware kit are prepared.
Hardware execution/calibration and Author acceptance remain open under
WOLF-PERF-001-06 and -08. This closes the authorized first headless baseline,
with physical speed and full populated-game CPU capacity explicitly unresolved.
