# WOLF-PERF-001 — Deterministic frame-performance measurement

Measure how quickly the eZ80 prepares Wolf's next state, how quickly the ESP32
renders it, and how consistently completed frames can be presented. Adapt
Rally's existing benchmark code and measurement boundaries to a repeatable
Episode 1, floor 1 room-and-door rotation fixture. The result should explain
Wolf's capacity and provide a qualified comparison with Rally, rather than
equating the game's configured 30 Hz cadence with measured throughput.

Status: implementation and headless Oryx execution authorized by the Author
on 2026-11-04. The subsequently authorized frozen hardware cohort completed.
Its visual workload validity is provisional after the Author reported no visible
rotation; WOLF-PERF-002 investigates. No new physical run or publication is
selected by this document.
The R06 headless cohort is now qualified; [RESULTS.md](RESULTS.md) records
measured boundaries, clock disagreement and the remaining physical gate.

## Tracking and code location

The root `TODO.md` is the sole actionable checklist and owns the immutable
`WOLF-PERF-001-01` through `WOLF-PERF-001-08` subtask IDs. This document defines
their requirements without duplicating their checkboxes. Never renumber or
reuse an ID. Mark completion or other disposition with evidence and rationale
in the dated development log before removing a resolved entry from TODO.

Keep fixture source, adapted timer/protocol code, build tools, manifests,
analysis, run instructions and retained results siloed in this task directory.
Generated outputs must be clearly separated from maintained source. Prefer
including production routines over copying gameplay or renderer implementations.
Any necessary production seam must be explicit and disabled in normal builds.
Do not modify Rally's owned tree or shared runtime source as part of this task.

## Existing evidence and reuse targets

1. Rally's `docs/tasks/RALLY-27/TIMING-PLAN.md` and
   `docs/tasks/RALLY-27/timing/README.md` define completed-frame counting,
   removal of CPU deadlines and VDP vblank pacing, ordered completion, PRT1
   stage timing, guest-created CSV output and diagnostic capability checks.
   Its `rally-game/src/timing_prt.asm` supplies the reusable timer donor.
2. Prefer the newer Rally measurement boundaries and physical qualification in
   `docs/tasks/RALLY-28/standard-vdp/bitmap-spans/SPAN-001-09/HARDWARE-RESULTS.md`
   and its package/analyzer. These distinguish geometry, packing, synchronous
   submission, completion wait, VDP-local work and stopped-record readout.
   Locate and inspect the exact underlying recorder/firmware code before reuse.
3. Rally's physical on-demand polygon road case reports 9.761 nominal PRT FPS
   and 70.883 ms mean VDP completion. That is a road-only diagnostic workload,
   not full-game FPS. Earlier R27 interpreter results were emulator-only;
   later MOS/PRT disagreements prevent treating nominal emulator 60 FPS as a
   verified speed. Carry those qualifications into every comparison.
4. Wolf's production loop in `src/asm/wolf3d/src/wolf3d.asm` fixes simulation
   at four 120 Hz MOS ticks, permits one render in flight and drops stale
   snapshots. This establishes scheduling policy, not hardware capacity.
5. Historical search, superseded by the Author's tile (34,36) selection below:
   Recover the Author's existing siloed fixture: spawn in a large E1L1 room
   near a door, then rotate through 360 degrees. Search the retired chat
   **Wolf3DOrig Retired 01**, including history before its oversized turn,
   for the task-directory path; inspect that directory and its provenance.
   It was not located during this planning pass. The history tool rejected
   an oversized turn even with a one-turn request; older history is partly
   readable. Do not claim the fixture is missing or silently replace it with
   the normal tile (29,57) player start.

6. The closer full-race precedent is Rally's
   `docs/tasks/RALLY-28/custom-vdp/direct-rows/RESULTS.md`: reversed-order
   paired 900-frame runs, identical eZ80 wire traffic, nominal PRT throughput
   36.28/39.16 FPS and unresolved MOS/PRT disagreement. Inspect its recorder
   and shared-cost notes before adapting code. Wolf's bounded copied/direct
   comparison in `agonport/vdplet/review-rows/REVIEW.md` measured 3.31/4.40
   million modeled transaction cycles; neither establishes physical game FPS.

Rally references above are rooted at `/Agon/mystuff/AgonArcade/`.

## Required fixture and experiment design

The Author selects canonical E1L1, zero-based tile **(34,36)**. Park the
player at the tile center **(34.5,36.5)**, 16.16 coordinates **x=0x228000,
y=0x248000**. Rotate **720 degrees over twenty seconds**, without
translation. Explicit defaults: start east (0 degrees), turn counterclockwise
at 36 degrees/second. Tile-center placement, heading and direction are stated
defaults; tile, two revolutions and duration are direct Author selections.

**Suppress all enemy spawns** in this fixture. Retain canonical geometry,
doors and static scenery, with door states pinned. No enemy AI, attacks,
movement or enemy sprite drawing may contaminate the rendering baseline.
Report zero active enemies and assert it in the fixture. This is a rendering
isolation workload, not a claim of full populated-game CPU capacity. Any later
populated gameplay benchmark requires a separately identified workload.

Use 600 fixed quanta at the normal 30 Hz simulation cadence. Derive integer
headings cumulatively, e.g. `floor(720*n/600) mod 360`, n=0..600, retaining the
revolution count. This prevents rounding drift and proves full-turn closure.
Freeze whether initial/final poses are timed submissions or endpoint-only
checks; 601 endpoint samples represent 600 intervals, not 601 intervals.

The normal-cadence arm lasts twenty nominal game seconds (2,400 MOS ticks), plus
separately reported warm-up and final drain. CPU and unpaced arms replay the
same indexed workload without intentional twenty-second waiting; report actual
elapsed time and throughput. Any additional cycles for timer resolution must
be explicit. Do not confuse the scripted cadence with measured capacity.

Freeze map/assets, adjacent door IDs/states, static population, RNG seed,
HUD/weapon/palette/audio settings, and frame-indexed pose/state digests in a
manifest. Keep production maps and spawn data unchanged: apply placement and
enemy suppression only in task-owned fixture code. Historical fixture recovery
is superseded by the Author's concrete selection and is no longer a blocker.

Use the current production VDPlet direct-row renderer as the primary subject.
Identify its firmware, SDK, module and application hashes; keep standalone or
copied-pixel variants out of the initial matrix unless needed as a named control.
Freeze finite counts, repeats, warm-up and watchdogs before execution. The starting
workload is the twenty-second two-revolution rotation selected above; retain complete cycles
if additional timer-resolution samples are necessary. Do not make the pose
sequence depend on host elapsed time or renderer speed.

The experiment has three distinct measurement modes:

| Mode | Work and required result |
| --- | --- |
| CPU capacity | Execute production simulation and render-state preparation without UART/render backpressure. Time simulation, visibility/dirty-state work and serialization separately where practical. Verify resulting states/bytes against the deterministic reference. Report pose generation separately from full-world simulation. |
| Completed-frame capacity | Feed the fixed pose sequence through production upload/render/completion with intentional CPU frame pacing and VDP vblank waits removed in a diagnostic build. Require every requested frame to complete; report submission count, completion count and actual elapsed denominator including final drain. |
| Production cadence | Replay the agreed scripted rotation with normal 30 Hz simulation and normal presentation fences. Record simulation steps, submissions, completions, presentations, coalesced poses and presentation intervals to quantify the smoothness observed in play. |

Warm assets and both buffers outside timed intervals. Preserve valid hidden
buffer ownership, direct-row lease lifetime and completion guarantees when
removing pacing. Unpaced throughput can tear and must be labelled accordingly.
Capability failure must stop the fixture rather than silently measuring a
paced path. Reuse Rally's code with recorded donor provenance and adapt its
completion protocol to Wolf's actual VDPlet lifecycle; do not copy a selector
or swap hook without verifying compatibility and ownership.

## Timing and output contract

Record raw PRT and MOS counts, nominal frequencies, timer/vector ownership,
overflow limits and restoration. Compare independent clocks over sufficiently
long batches. Clock disagreement must block an unqualified milliseconds/FPS
claim. Measure timer/marker overhead with a named empty control; retain it
without automatically subtracting it from results.

On the eZ80, distinguish computation/packing from synchronous UART submission
and completion waiting. Submission can include CTS backpressure and is not
pure CPU work. On the ESP32, use Rally-style local ordered timestamps and a
completion fence; distinguish parsing/dispatch/queue/drain from the Wolf
renderer interval. Add entry/exit timing around the actual renderer if needed
to answer isolated render cost. If that boundary cannot be instrumented,
report the broader interval honestly and leave isolated cost unresolved.
Do not add overlapping CPU and VDP times to invent an end-to-end duration.

Keep per-frame results in bounded RAM, with capacity/overflow counters.
No SD writes, printing or host telemetry calls in measured intervals. Write
guest-owned machine-readable output after final completion, then analyze
offline. Preserve raw samples, frame IDs, bytes submitted, failure/status and
completion evidence, timer settings and exact build/runtime identities.
Reject missing/duplicate frames, count mismatches, timeouts, clock wrap errors,
truncated files and sample overflow. Report mean, median, p95, maximum and
distribution of intervals, total completed FPS, per-stage milliseconds and
the fraction exceeding the 33.3 ms game budget. Keep presentation counts
distinct from optical display refresh.

## Validation, comparison and review boundary

Host checks must validate deterministic sequence/state, arithmetic, schema,
completion counts and timer cleanup, including failure paths. Qualify finite
emulator runs separately from physical results. Use matched clocks, runtime,
mode/resolution, instrumentation and pacing semantics where possible when
comparing Rally and Wolf; disclose scene, pixel count and architecture
differences. This compares measured workloads, not equal visual complexity.

Real Agon hardware owns the final speed conclusion. A physical runbook must
identify required diagnostic firmware, rollback, exact commands, expected
duration and output. Follow canonical bench and SD procedures. Pi heavy work,
Oryx custody, firmware flashing and physical invocation retain their applicable
authorization gates. Never launch the Author's GUI or commit emulator-related
changes before the required human acceptance and explicit publication approval.

Deliver a concise results report answering: eZ80 pose/full-state capacity;
ESP32 render and broader completion costs; unpaced completed throughput;
normal presentation regularity; limiting stage; and qualified Rally comparison.
Retain limitations and raw evidence alongside the report. Optimization is a
later decision; this task first establishes a trustworthy baseline.

**Execution boundary:** implement and qualify the selected fixture headlessly
on Oryx under the shared FIFO; preserve results and release after owned cleanup.
The Author also explicitly authorized scheduling notifications to queued agents.


## Initial implementation decision

The unpaced arm measures completed hidden renders without per-frame C3, then
presents once after the timed interval. This removes VSync pacing without
changing shared firmware; it is not unpaced display FPS. The paced arm retains
C3 and an ordered INFO fence. Native CCOUNT brackets isolate the render call,
colour-row scope and full module call separately; log readout occurs afterward.
The workload is 600 indexed poses: first revolution indices 1..300, second
301..600. Report both, never silently discard the first. Audio is disabled for
render isolation; geometry, authored doors and statics are retained.
