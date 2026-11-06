# Matched Olimex result: bespoke 30.7 ms, VDPlet 91.6 ms per draw

The complete physical comparison passed. In this fixture, the quiet production
VDPlet takes **2.98 times as long to draw a pose** as the bespoke native renderer.
The eZ80 preparation is a small part of the frame budget. The paced fixture
completes approximately **24.4 frames/s bespoke and 10.0 frames/s VDPlet**.

These are measurements of this deterministic workload on the Olimex, not a
measurement of ordinary interactive gameplay. The VDPlet result identifies
drawing as the principal bottleneck; it does not identify the expensive drawing
operations or establish that generic VDPlet dispatch causes the difference.

## Drawing and completed frame rate

Each backend has two unpaced 600-frame trials, in A/B/B/A order. Every trial
renders the complete angle sequence. Pooling those 1,200 samples per backend:

| Measurement | Bespoke A | VDPlet B |
| --- | ---: | ---: |
| Mean time to draw the pose | **30.701 ms** | **91.560 ms** |
| Median draw time | 30.652 ms | 91.391 ms |
| 95th percentile draw time | 32.941 ms | 92.697 ms |
| Maximum draw time | 33.428 ms | 92.901 ms |
| Mean fully received command through render return | 30.705 ms | 92.144 ms |
| Mean complete active frame, including eZ80 work | 33.028 ms | 95.028 ms |
| Unpaced completed frames/s | **30.271** | **10.522** |

Milliseconds in the native brackets convert raw CCOUNT at the source-configured
240 MHz. Frame rates use the eZ80's nominal 1 ms PRT ticks. No external clock
calibration was performed. The separate MOS 120 Hz measurement gives unpaced
30.227 and 10.503 frames/s, respectively.

The draw bracket covers the actual renderer: raycasting and the background,
walls, statics, HUD, weapon and synchronous framebuffer writes. A ends after its
final drawing drain. B brackets `render_world_direct`, with the acquired direct
row pointers already available. B's broader scope, including row acquisition
and release, averages 92.030 ms; the fully received command bracket averages
92.144 ms. Thus only about **0.584 ms** separates B's draw and command-return
means. The large A/B difference is already inside drawing.

These are elapsed execution intervals, including preemption and service calls,
not exclusive CPU profiles. Serial receive time precedes the fully received
command bracket; reply transmission and presentation follow it.

## Paced output

Each paced run requests 600 nominal 30 Hz quanta across two full rotations,
starting east at E1L1 tile (34,36). It submits the newest pose when ready and
coalesces older poses rather than building a queue. The final step must be 600.
Two warm-up frames precede measurement; neither rotation is discarded.

| Measurement | Bespoke A | VDPlet B |
| --- | ---: | ---: |
| Completed frames in the two trials | 490 + 488 | 201 + 201 |
| Pooled elapsed PRT time | 40.067 s | 40.182 s |
| Completed frames/s | **24.409** | **10.004** |
| Coalesced quanta, out of 1,200 | 222 | 798 |
| Median completion/presentation interval | 34 ms | 100 ms |
| 95th percentile interval | 50 ms | 100 ms |

Bespoke drawing alone fits most of the 33.33 ms budget. The complete active
frame averages about 33.03 ms even without pacing, leaving almost no margin.
The paced scheduling and presentation path therefore matters: being under
budget on average inside the drawing call does not establish sustained 30 Hz.
B's drawing alone consumes roughly three 30 Hz budgets.

These rates count acknowledged completion and the presentation fence. They are
not optical measurements of scanout or a new human judgment of smoothness.
Paced arms retain different headings because of coalescing, so the full-angle
unpaced arms above provide the matched drawing comparison.

## eZ80 and serial accounting

The CPU-only arms prepare 600 scripted poses without per-pose UART submission
or VDP backpressure. Across two trials each, A averages **1.121 ms** and B
**2.163 ms** of active preparation. Their shared pose-plus-packing portions
average **1.117 ms** and **1.102 ms**. B's additional CPU-only `submit` bucket is
serializer lifecycle bookkeeping; no UART transmission occurs in that arm.
These are not full populated-world AI or game simulation timings.

In the actual unpaced render arms, the synchronous eZ80 sender bucket averages
0.244 ms for A and 1.653 ms for B. Those calls include CTS/backpressure. The
following wait buckets average 31.651 and 92.263 ms, including drawing and the
reply path. They overlap the native drawing interval and must not be added to
it as independent costs.

Subtracting mean native draw time from complete active frame time leaves
2.327 ms for A and 3.468 ms for B. This remainder includes preparation,
submission, command overhead, reply handling and presentation. **It is not a
measurement of pure RX/TX or wire transfer time.** No logic-analyzer serial
trace was collected in this cohort. Actual frame request batches are 24 bytes
for A and 65 bytes for B; the paced presentation fence is separate.

## What was qualified

Frozen source commit: `9e191aa625c7fd771cdd2a80a4323dd675eb3976`.
The unchanged [hardware09 plan](HARDWARE-RUN-09.md) selected fourteen guests:
A control/CPU/unpaced/paced, B control and two CPU/unpaced/paced sets, then
A CPU/unpaced/paced. Eight B resource probes run outside the timed intervals.

- All fourteen guests and eight probes passed. Every measured arm reached
  closing step 600, with matching record index/angle/native count, bounded
  counter differences, clean return, stack and timer/vector restoration checks.
- All fourteen asset loads completed 470 records and 952 breadcrumb fences,
  with zero timeouts, recoveries or loading errors. This includes the actual
  full-render history missing from the earlier loading-only check.
- B's minimum reported stack headroom settled at 1,956 bytes, above the frozen
  512-byte refusal threshold. The full native A 600-record run followed by the
  next guest's warm-up also passed, qualifying the recorder-lifetime correction.
- Both instrumented paths read Xtensa PRID. All eight render reports retain
  `0xCDCD`: the installed SDK's `xtensa_context.h` identifies this as PRO/core 0,
  not an invalid numeric core index. Same-core guards run around the measured
  calls. Raw CCOUNT intervals and the independent guest bounds retain the
  original wrap checks. Clock/PM settings remain source evidence, not a new
  physical calibration.
- Fixture: zero-based tile (34,36), center (34.5,36.5), east then CCW 720 degrees;
  no enemies, 22 closed doors, 121 statics and fixed HUD/weapon. Mode 136 is
  320×240 with a 256×160 viewport at (32,20). Both use the corrected map binding
  and identical canonical assets. Earlier corrected Fab/human visual evidence
  is retained; this headless hardware cohort adds no optical pixel review.

Native A SHA-256 is
`c5cfaaed91a0d294bbe30811ca57ff36a585d070946f0813a469412f57d77fcc`;
native B is
`7593b9cf9a2dc60e81221d998527d4ac0d1c3f51077348ea03e869016aa0581d`;
production module is
`1907ce1711f68676dc1c0c6eb70b8f55ae03d0934aee537329edcf77fe652610`.
The module uses safe SDK Os/PIC/manual helpers and direct rows, whereas A uses
O2/builtins and Canvas scratch bitmaps. This is the performance of those exact
implementations as packaged, not an isolated compiler, allocator or dispatch
experiment. No rendering optimization was included.

## Restoration and remaining work

The exact original native app and touched tail were restored and independently
read back across the full 1,105,920-byte span. Original P4/EMOS, startup and
listener were retained. Fresh mode 0, callback 0, Legacy 0, CLI/read/EXIT,
neutral input, idle/offline state, free USB ports and joined actors passed.
SD remained mounted. **Actual Olimex generation 54 released at
2026-11-06 09:31:19 UTC (04:31:19 EST)**; the scheduler/actual successor received
the complete handback before offline analysis. Wolf holds no bench lease.

Two additional final-handback host checks needed correction after the main
controller had already restored the board: a prompt wait while mirroring was
off, and reuse of a retired listener metadata journal. The original SAVE was
retrieved without repetition; a fresh journal completed EXIT. Both failures
and their resolutions remain in the private release evidence. No guest,
measurement or uncertain firmware write was repeated.

WOLF-PERF-003-04, -06 and -07 now have physical qualification/report evidence.
Smith's acceptance (-08) remains pending. The historical intermittent loading
fault (-16) has not been explained or proved repaired by these successful
loads. The separately specified corrected-runtime matched emulator timing
cohort (-05) remains incomplete; the earlier twelve four-way functional passes
do not substitute for it. Hardware remains the primary target. If emulator
issues persist at the end of this arc, hand them to Flexe and move Wolf to
other useful work, as Smith requested.

The parked wall-column allocation investigation (-18) remains a candidate for
separate profiling. These measurements do not yet say which drawing operations
cause the B gap. No optimization or additional test is selected by this report.

## Evidence

[Per-case table](results/hardware09/cases.csv),
[pooled results and per-case reports](results/hardware09/comparison.json),
[retained raw-file hashes](results/hardware09/retained-raw-sha256.json), and
twelve per-sample CSV files in [results/hardware09](results/hardware09) are
checked in. Pooled p95 uses the nearest-rank method over all samples. The
device-free [curation script](hardware/summarize09.py) reproduces these exports
from retained receipts and checks their counts/loading/core metadata.
An independent fresh decode of all twelve measured raw guest/native outputs
matches all 6,180 exported samples exactly; pooled means/p95 and all retained
raw-file hashes also match. `git diff --check` passes.

Full unmodified raw output, RAM/stack dumps, source/kit pins, bootstrap,
write/readback, retrieval and release journals remain locally under
`build/hardware09` (ignored; no lease token or raw RAM is published). The generic
analyzer's original per-case clock label says "emulator"; originals remain
unchanged, and the curated copies explicitly identify this actual physical
execution and preserve that inherited label in a separate field.
