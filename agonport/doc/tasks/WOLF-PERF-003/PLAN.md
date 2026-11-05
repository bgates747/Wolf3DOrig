# WOLF-PERF-003 — Matched bespoke VDP and VDPlet frame benchmark

Measure the cost of rendering the same Wolf3D pose through the bespoke VDP
and the production direct-row VDPlet. Answer how long each VDP takes to draw
it, how much submission/completion adds, and how many completed frames each
path sustains. Smith authorized this task, a commit/push of its plan, and
implementation on 2026-11-05. Freeze the plan before implementation.

## Tracking and preservation

Root TODO.md owns immutable IDs WOLF-PERF-003-01 through -08. This document
specifies their requirements without a second actionable checklist. Record
completion or other disposition with evidence in the dated development log;
never renumber or reuse IDs.

Keep new fixture adapters, diagnostic renderer wrappers, builders, manifests,
profiles, analysis and retained evidence in this directory. Generated output
belongs under ignored build/. Preserve PERF-001/002 source and results, the
accepted production game and renderer, and other agents' runtime trees. Reuse
production owners through copied source or explicit task-only inclusion; never
replace a renderer with a simplified benchmark implementation. Cross-project
source changes, if actually necessary, require coordination with that owner.
The queued WOLF-AUDIO-001 test retains its separate reservation and scope.

## Matched fixture

Use canonical Episode 1 floor 1, zero-based tile (34,36), centered at
(34.5,36.5), x=0x228000/y=0x248000 in 16.16. Start east, rotate counterclockwise
720 degrees over 600 nominal 30 Hz quanta (20 seconds), without translation.
For indices n=1..600 use floor(720*n/600) modulo 360. Pose zero is warm-up;
pose 600 is the timed closing pose. Report revolutions 1..300 and 301..600
separately as well as pooled; retain the first revolution in the evidence.

Suppress all enemy spawns and assert zero active enemies. Pin original map,
closed doors, statics, RNG seed, view/HUD/weapon/palette settings and asset
hashes identically across both backends. Match 320x240 double-buffered mode
and the actual 256x160 world viewport. Disable music, SFX and speech during
measurement. Retain equivalent startup/asset allocation history, warm both
pages with two untimed frames, and reset diagnostic counters after warm-up.
Reuse PERF-001's canonical package transformation and verify identical pose
and world-state sequences. Do not modify production maps.

## Backends and comparison controls

A is the maintained standalone bespoke Wolf renderer selected by the normal
standalone eZ80 backend. B is the production VDPlet direct-row renderer.
Inventory exact source commits, dirty-source hashes, generated tables,
compiler versions/flags, framebuffer layout, firmware features and runtime
identities before choosing build inputs. Build both clients from the same
frozen production source; select only the backend and required transport.
Use the same assets, MOS, emulator frontend/backend and clocks where compatible.
Report differing command bytes, completion protocols and resident allocations.

Use quiet task-owned diagnostic variants: bounded RAM records and readout only
after timing, with no per-call RX/TX printing or SD traffic in timed intervals.
Freeze optimization, ESP32 clock/core, PSRAM placement and services explicitly.
Record necessary platform differences rather than attributing every difference
to VDPlet dispatch. The older noisy r2 hardware results are historical context,
not the matched B arm. Re-run B alongside A. No performance optimization is
part of the first comparison.

If render math or pixel output differs, identify that before interpreting speed.
Compare canonical geometry and low-six-bit pixels at useful separated headings
on both paths, including doors/statics/HUD. Preserve screenshots and digests;
show that both turns actually produce changing displayed views. If exact pixel
parity is not attainable, document the concrete difference and qualify the
comparison; do not silently call different scenes equivalent.

## Measurement arms and timing boundaries

| Arm | Required behavior |
| --- | --- |
| CPU capacity | Generate all 600 poses and prepare each backend's real state/serialization without per-pose UART or render backpressure. Separate shared pose work from backend-specific packing. This is an enemy-free fixture, not full populated-game CPU capacity. |
| Completed-frame capacity | Submit and complete every indexed hidden render, without intentional CPU pacing or per-frame C3. Count only completed frames; include final drain in elapsed time. Present once outside timing. This measures hidden-frame capacity, not display FPS. |
| Paced presentation | Run the same 20 nominal second timeline with one render in flight, latest-pose coalescing, normal C3 and an ordered completion fence. Record submitted/completed/presented IDs, skipped quanta and presentation intervals. The endpoint must close both turns. |

The primary VDP number is **time to draw the pose**: bracket the real renderer
entry immediately before drawing through completion of all its synchronous
framebuffer writes. State whether HUD/weapon drawing is in that call and match
it. Retain a second bracket from dispatch of the fully received frame command
through finished drawing, before reply serialization, plus any actual async
worker completion if relevant. Record core ID and raw CCOUNT; reject migration,
invalid wrap, missing/duplicate IDs and failed renders. Keep parsing, logging,
UART response and presentation waits distinguishable from drawing. Do not label
command-queue acceptance as completed rendering.

On eZ80 reuse Rally-derived PRT1 instrumentation and independent MOS ticks from
PERF-001. Record pose generation, packing, synchronous submission (including
CTS stalls), completion wait and presentation fence. Record wire byte counts.
Do not add nested or overlapping intervals. Show a simple draw-time result
first, then submission/completion and completed throughput separately.

Use finite RAM capacity, explicit overflow checks and guest-created raw output
only after measurement. Keep raw timer values and clock assumptions. Compare
PRT, MOS and independent elapsed observations; unresolved disagreement blocks
unqualified hardware milliseconds/FPS. CCOUNT-to-ms needs a verified ESP32 clock
and includes elapsed preemption. Empty/control overhead is reported without
automatic subtraction. Report mean, median, p95, maximum, complete-batch elapsed
and per-revolution values; keep observed presentation count separate from
optical refresh and ordinary-game performance.

## Qualification and finite execution

First validate source bindings, deterministic assets, backend selectors,
frame/state identity, recorder bounds, schema rejection and timer/vector cleanup
on the host. Test actual production paths and meaningful failures. Avoid tests
that merely repeat constants without checking the generated inputs or outputs.

Use canonical Pi serial-build FIFO for compilation and normal Oryx FIFO for
headless emulator execution. Follow canonical guidance in agon-dev-env/codex/
(emulator.md, bespoke-vdp-emulator.md and environment.md); do not duplicate
network recipes here. Create stopped, separate task profiles with explicit
frozen frontend/backend/MOS/module inputs and fail-closed loaders. No GUI.

Initial emulator qualification is one run per backend/arm plus one bounded
cleanup control per backend: eight invocations, each at most 300 seconds.
After all pass, the comparison cohort is A then B then B then A for each of
three arms: twelve invocations at the same bound. Freeze exact inputs and
schedule before starting each cohort. Stop on the first unexpected failure;
retain it and make a new identified revision for a necessary fix. Require
normal guest teardown, restored timer/vector, actual MOS return, ordinary host
Quit and zero backend faults. Retrieve/hash results, prove whole-host idle,
release Oryx and notify its actual successor before extended analysis.

Emulator results establish correctness and emulator-relative behavior. Final
physical performance requires the same board, exact component/build identities,
fresh Extender checkout and a concrete firmware/staging/restoration runbook.
Prepare that finite matched A/B/B/A hardware matrix after headless qualification;
coordinate any required diagnostic firmware with its owner and Extender before
installation. The audio-only slot authorizes no benchmark or firmware change.
Preserve incoming firmware/startup/card contents and leave SD mounted. Record
restoration and a fresh clean release before any physical speed conclusion.

## Deliverable and acceptance

Deliver reproducible task-owned preparation, source/artifact manifests, matched
raw records and a concise report: bespoke draw time versus VDPlet draw time,
ratio/delta, eZ80 preparation and submission costs, completed throughput, paced
regularity, scene parity, overhead and concrete confounders. Distinguish hardware
from emulator and capacity from paced presentation. Retain failures and unknowns.
Do not infer a universal VDPlet penalty from this one Wolf workload. Record
Smith's acceptance/disposition by immutable ID. This task-plan publication does
not promote unreviewed runtime binaries, profiles or later implementation.
