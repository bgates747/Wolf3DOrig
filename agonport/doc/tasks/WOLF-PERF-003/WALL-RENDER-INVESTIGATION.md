# Wall-column overhead investigation — WOLF-PERF-003-18

Smith identified per-column scratch/bitmap/completion work as an optimization
candidate on2026-11-05. Source investigation complete below; measurement and
candidate qualification remain open. No frozen baseline, production source or
component firmware changed. No compiler/emulator/hardware run started here.

## What the retained source actually does

Bespoke A hardware03 nativec5cfaaed RenderWalls loops over the256 view columns.
For each valid textured wall span it allocates BufferStream(destHeight), samples
one texture column into it, creates a stack-local1xN Bitmap wrapper, draws the
bitmap and calls waitPlotCompletion(false), then destroys the wrapper/storage.
That means up to256 scratch allocation/release lifecycles per frame. Bitmap
construction itself defaults to copy=false, so it does not make a second pixel
allocation or copy. BufferStream requests PSRAM when available through
PreferPSRAMAlloc (including psramInit); otherwise malloc. Actual placement and
cost need measurement, not inference from the allocator's name.

There are two pixel passes in this route: texture-to-scratch sampling, then
scratch-to-framebuffer generic RGBA2222 bitmap drawing. Increasing span height
increases both. Fixed allocation/dispatch/flush overhead instead scales mainly
with the number of valid columns, so it cannot by itself explain every slowdown
near walls. Sprites and other frame work also vary with the view.

Important correction to the earlier conversational explanation: double-buffered
BitmappedDisplayController::addPrimitive executes ordinary DrawBitmap immediately.
Only SwapBuffers follows its special queued/notification path in that mode.
waitPlotCompletion(false) calls Canvas::waitCompletion(false), which calls
processPrimitives rather than waiting for vsync. It suspends background primitive
execution, drains the queue, shows sprites, resumes and adds a Refresh primitive.
The VGA implementation includes interrupt-control work on suspend/resume.
Thus the per-column call may be redundant work in this mode, but is not evidence
of256 scheduler sleeps or256 vsync waits. Its true cost remains unmeasured.
Queued modes still need valid bitmap descriptors and pixels until consumption;
removing a drain generally without preserving ownership would be incorrect.

VDPlet B's retained production draw_walls samples texture bytes directly into
acquired hidden framebuffer rows. It acquires/releases a texture once per used
texture ID and loops over that texture's columns. It has neither A's per-column
scratch allocation nor its Canvas bitmap/flush calls. Whole B rendering still
has row/asset lease/setup costs, different compiler flags/layout and other work;
this source difference is not a measured A/B speedup or pure dispatch comparison.

## Proposed staged investigation

First use a separately identified diagnostic copy, preserving the original
matched A/B benchmark inputs. Count DDA cell visits, valid wall columns and
summed visible wall pixels. Record disjoint CCOUNT phase totals for raycasting,
scratch allocation/release, texture sampling, drawBitmap execution and explicit
completion calls, plus the existing full-render interval. Drawing already runs
inside drawBitmap in this mode, so do not count it again as queue-wait time.
Report profiling overhead and compare an uninstrumented baseline; do not print
inside these brackets. Retain same-core/wrap bounds and raw counters.

Use fixed poses from the existing rotation to start. A separately identified
near/far-wall fixture can test wall-area versus ray-step cost later; geometry,
visible sprites and other changes must be recorded. Do not silently change the
canonical34,36 fixture or compare different scenes as an optimization speedup.

Candidate1: allocate one maximum-height column scratch buffer outside the wall
loop and reuse it, retaining per-column drawing and completion calls. Match its
memory pool to baseline initially so allocation count is the isolated change.
Prove allocation failure behavior and descriptor/pixel lifetime, and keep an
explicit final drain before releasing storage. This does not remove pixel copies.

Candidate2: separately test avoiding redundant per-column processPrimitives only
on a source-verified synchronous double-buffer path. Preserve the queued-mode
fallback and the final renderer completion contract. Keep this separate from
scratch reuse to attribute any difference. A source-only claim that it is safe
for all modes is insufficient.

Larger options include tiled/batched persistent storage or a direct-row bespoke
path. These change memory/dispatch architecture and need their own pixel/lifetime/
resource qualification. B already supplies a direct-row reference; it does not
need the per-column scratch optimization described for A.

## Qualification and status

Require exact geometry/low-six-bit frame parity against baseline at separated
headings, doors/statics/HUD/weapon and near-wall clipping; exercise repeated
frames and failure cleanup. Use Fab for visual correctness, not ESP32 timing.
Only a fresh admitted hardware run can establish speed/cost here. Current
loading-query blocker003-16 and changed bench components still need resolution/
reconciliation; do not replay the failed suite or borrow another owner's slot.
Keep original A/B comparison and optimization results separately identified.

No candidate is implemented or selected for physical deployment by this note.
The next concrete deliverable is a frozen profiling/candidate plan after the
source findings and current component context are reconciled.

## Retained source pins

Paths below are relative to this task directory; source hashes identify what
was inspected, not a new build or runtime qualification.

| Source | SHA256 |
| --- | --- |
| `build/hardware03/native-a/video/wolf3d.h` | `43c02c09712519001e10ff1c8cc44af1b77fa1c64e99c2052a6045aeca24a8bd` |
| `build/hardware03/native-a/video/buffer_stream.h` | `6b57aedf9e7fee1b8fdb84660e4eaade788c185ec540f94b00f965f2024c418d` |
| `build/hardware03/native-a/video/types.h` | `0b14cd7fd375145d537335e465459c119c0ba23fa4594f7aeb6709aafd8fb2a5` |
| `build/hardware03/native-a/video/agon_screen.h` | `648dbc7d0ba9d98a3115a4ba307ff7585c6c5e28189c1e8961eff7a3c3d60343` |
| `build/hardware03/native-a/deps/vdp-gl/src/canvas.cpp` | `3626baa0df539ed5a8fde03d67d236c5a38636cd914764eca702b5310bde3271` |
| `build/hardware03/native-a/deps/vdp-gl/src/displaycontroller.cpp` | `f3588a684647ef258c024251d17b029e2877c8363b28a570432376f353232902` |
| `build/hardware03/native-a/deps/vdp-gl/src/displaycontroller.h` | `603bac727fd1ab61d6f36a8d1a0e533471b849d6c30159b5f95ed4260e9d5c23` |
| `build/hardware03/native-a/deps/vdp-gl/src/dispdrivers/vgacontroller.cpp` | `77cbb352a896c7d1464fba8dbc1cd4cc33dab6d513d818742aa582868a66b541` |
| `build/r04/vdplet/native-source/wolf3d_renderer.cpp` | `aee6ed184b0d29e090b2f869559110d1c13fa801b735b1cbd5f36f53e43a3107` |
