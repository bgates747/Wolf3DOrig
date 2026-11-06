# Wolf conversion self-review

Our conversion preserved a great deal of visible output and ownership behavior,
but changed the implementation enough that those checks could not establish
performance parity. We replaced private Canvas operations with a software
compositor, introduced arithmetic support and a generic output abstraction,
then carried those choices through later stages. We did not account for their
hot-path cost against the original renderer before confidence in playability
became confidence in preserved performance. That is a Wolf review failure.

The current physical comparison establishes 30.701 ms bespoke versus 91.560 ms
VDPlet mean drawing time for this fixture. It does **not** establish each
substitution's timing share, or a universal architectural penalty for VDPlets.
My recent chat shorthand should retain that distinction.

## Review identity and method

Task frozen/pushed as `316c262e4b273b8a0b33b10c483c995630fd5408` before this
review. [EVIDENCE.json](EVIDENCE.json) pins 24 documents/source inputs and four
historical commits. The current production renderer is byte-identical to the
renderer source used in the measured B package. Production module source is
reviewed alongside the separately pinned instrumented benchmark wrapper.

This review reads source, history, qualification code and existing receipts.
It checks fill-request arithmetic without running a renderer. Packaged binary
observations below are attributed to VDPlet's retained VDPL-031 source/ELF
audit; no new compilation, disassembly, benchmark, reservation or device access
was performed. These are project-owned findings and prose, not copied code or
assets for a generic SDK template.

## SR-001 — A complete-frame compositor retained redundant work

**Trace.** The bounded copied proof in commit `42e9d82` initializes the complete
320×240 RGB222 workspace, then paints the 320×200 play surround and view over
it (`wolf3d_scene.cpp:compose_background`). Production extraction `dd906f9`
retained that organization. Production direct-row commit `52ddd51` changed
the destination but retained the complete-screen initialization
(`production/wolf3d_renderer.cpp:compose_background`).

**Divergence.** B requests 182,600 background pixel writes, counting overwritten
pixels. A's equivalent play/view/bevel fills plus its later 320×40 HUD clear
request 118,600: **64,000 additional fill requests in B per frame**. Whole-frame
initialization gives a simple complete workspace image; preserving the lower
panel's background is necessary. Repainting the top 200 rows immediately
afterward is not required by the VDPlet interface.

**Why checks missed it.** Exact final pixels cannot see overwritten work. Our
host oracle's background compositor also initializes a whole vector before
painting the scene. It remains a useful pixel reference, but is not an
independent measure of the original native command stream or work count.
The oracle directly uses native DDA code; that does not make every manually
reconstructed surrounding pass an untouched native implementation.

**Detection/correction example.** Compare draw-pass coverage and write counts
with the original, in addition to final pixels. A candidate could initialize
only the lower 40 rows before retaining the later play/view fills. Test the
entire 320×240 output, including uncovered/transparent HUD regions, sync bits
and multiple poses. Do not merely delete all initialization. This candidate
is unimplemented here; saved milliseconds remain unknown.

## SR-002 — The direct-row adapter changed the unit of abstraction

**Trace.** `52ddd51` introduces `RenderTarget`, `target_pixel`, `put_pixel` and
`fill_span` to serve both linear copied output and borrowed native rows. Its
diff shows a linear span clear becoming a per-pixel `put_pixel` loop on the
direct path. The earlier bounded direct proof likewise used nested loops.

**Divergence.** VDPL-031 verifies that the actual packaged B loop retains
`fill_span → put_pixel → target_pixel` calls per background pixel. The helper
selects layout/address and preserves the destination sync bits. Its generated
byte-store path contains two consecutive `memw` instructions. These are local
module calls, not per-pixel runtime services. The count of 182,600 background
pixels implies 365,200 nested helper calls and 365,200 writer barriers on that
successful path; it does not imply a cycle cost.

**Required versus chosen.** Borrowed noncontiguous rows, lane XOR, low colour
bits, preserved high sync bits, clipping and row lifetime are required. A
runtime/linear choice inside every pixel write is our implementation choice.
The direct-row plan's instruction to keep the math unchanged and replace the
final-store accessor did not preserve the span's computational structure.

**Detection/correction example.** Review the changed inner loop and its actual
packaged disassembly, rather than inferring inlining from C++ source or an O2
host build. Select row/layout once per span where the contract permits it;
keep a separate qualified copied control. Preserve required PSRAM safeguards
and sync bits; safe aligned/word stores need their own proof. Compare one
span-only candidate with the unchanged control before combining fill removal,
compiler changes or arithmetic work.

## SR-003 — A build workaround became permanent arithmetic infrastructure

**Trace.** The 2026-10-30 log and VDPlet README explicitly record the pinned
linker's failure with the broad libm/libgcc link. The bounded proof supplied
local `__divdi3`/`__udivdi3` helpers to make the finite module fit and link.
The production wrapper `4b8fb1f` carries that family of implementation into
`production/wolf3d_module.cpp`.

**Divergence.** VDPL-031 verifies B's local fixed 64-iteration divider and A's
ROM-resolved helper in the actual retained ELFs. Similar fixed-point source
expressions therefore use different arithmetic implementations. The API does
not require this specific divider. The recorded linker failure explains the
choice; it is not performance qualification or proof that no supported
alternative exists.

**Missed evidence.** `WOLF3D_HOST_TEST` excludes the local memory/division helper
block. The host wrapper suite exercises renderer/lifecycle logic with host
arithmetic, not this actual Xtensa helper implementation. Target scene passes
exercise some real helper inputs, but are not exhaustive signed-division
correctness or performance tests. Do not describe host output parity as proof
of identical target arithmetic support.

**Detection/correction example.** Record helper providers and resolved call
targets as dependencies at conversion time. A supported narrowly linked static
helper is a candidate, with explicit signed/unsigned/zero/overflow semantics,
target code size, stack and safe compiler policy. Preserve the present helper
as a control. Do not insert ROM addresses into a module or replace fixed-point
division with floating point simply because the native binary has a ROM call.
No relative divider timing is established by this review.

## SR-004 — Fewer resources and services did not mean less total work

**Trace.** Production extraction groups walls by texture, acquiring one texture
span and scanning 256 columns for each needed texture. It replaces native
column scratch allocation/bitmap/drain behavior. The original migration also
compresses full trig tables into a quarter-wave representation to meet the
static-data ceiling. These are substantive organization/representation changes,
even when the projected geometry and final pixels match.

**Review failure.** We emphasized module fit, reduced frame workspace, balanced
leases and removal of copied publication without a corresponding accounting
of extra scans, table reconstruction, per-pixel work or cache behavior. Those
resource gains are real; they do not establish a frame-time gain. The bounded
copied/direct comparison already recorded about **32.93% higher modeled median
transaction cost for direct rows**, alongside an 80,608-byte workspace saving.
It was accurately labeled an emulator result, not a physical or full-game
benchmark. We should have kept that warning visible when discussing migration
performance, rather than treating direct output as inherently faster.

**Detection/correction example.** Keep resource and operation deltas side by
side: work per visible texture, scans, spans, source samples, helper calls,
copies and peak lifetimes. Measure the relevant phases before selecting a
traversal/table change. Neither the native allocator path nor the grouped
module path is automatically preferable. This review proposes no reversal of
the valid lease/memory design without measured evidence.

## SR-005 — A correct kernel harness did not validate guest initialization

**Evidence.** WOLF-PERF-003 r06 records that A's benchmark warm-up omitted
`INIT_LEVEL`. Its map remained unbound, and the missing-map fallback rendered
solid walls. Correct camera coordinates and correct host oracle geometry did
not establish the intended end-to-end scene; the host had initialized the map
directly. Smith spotted the wrong location during visible review.

**Correction already made.** A now performs the ordinary level reset before
the second warm-up. Earlier A performance results were explicitly disqualified
as canonical-room comparisons. Corrected Fab views and the later full physical
cohort are separate retained evidence.

**Reusable method.** Exercise the actual producer's initialization/update
sequence and bind it to the measured renderer's map/state. Require expected
room landmarks and changing headings, not only valid wire pose fields or a
successful completion packet. An invalid control must be invalidated, not
explained away by a backend performance theory.

## SR-006 — Double buffering applies to diagnostics and lifecycle too

**Evidence.** Initial loading dots/text could remain hidden or diverge between
pages. WOLF-PERF-003 r07 reconstructs the entire panel from one authoritative
stage/count on both pages. Its proof captures compare both sides of an actual
swap, and its asset count matches container records. Visible progress is part
of the application behavior, even though it is outside rendering benchmarks.

The diagnostic native A recorder also retained a borrowed buffer pointer/count
after the buffer was deleted. A single successful batch did not exercise the
next guest's warm-up. The subsequent lifetime correction and actual54's full
600-record-to-next-warm-up transition provide the missing evidence. This was
a benchmark-instrumentation bug, not a newly discovered VDPlet renderer defect.

**Reusable method.** Compare full lifecycle sequences, including repeated
use, buffer retirement, abort/re-entry and both pages. Adapt state/ownership
at the boundary instead of letting page-local histories or borrowed pointers
survive implicitly. Keep diagnostics out of timed work and quantify observers
when phase instrumentation is later selected.

## What our process did well, and what I would change

The records did explicitly say physical performance was unmeasured. We retained
the native control, exact source/package identities, meaningful pixel/geometry
oracles, noncontiguous-row tests, failure cleanup, sync-bit checks, target stack
evidence and negative results. Those enabled the current diagnosis. The problem
was not a complete absence of tests; it was confidence exceeding what those
tests established, plus a conversion review centered on output and admission.

For this conversion I would require the following evidence before claiming
performance preservation, as a proposal rather than a newly adopted policy:

1. An immutable native control plus a short difference ledger for changed hot
   loops, fill/copy passes, numeric helpers, table/layouts and completion model.
   If the kernel is substantially rewritten, say so and retain that extra arm.
2. Exact output/state and lifecycle evidence through the real producer path,
   alongside work/resource accounting. Avoid rebuilding the oracle in the same
   abstraction whose extra work is under review.
3. Actual target helper/call/store inspection for surprising paths. Host
   conditional compilation and optimizer differences must be explicit.
4. A deterministic full-angle hardware comparison before a hardware parity
   claim. Separate unpaced capacity from paced delivery and nominal clocks
   from calibration. Expose unexplained regressions and ask for a disposition;
   do not infer preserved performance from playability or memory savings.
5. Nested phase attribution with observer controls, then one changed mechanism
   per candidate, exact pixels/state and resource/stack checks. Keep old
   evidence and negative results when correcting a fixture or implementation.

These recommendations complement VDPL-032's existing ideas; they are concrete
Wolf examples, not a request to expand that task or impose a universal dossier.

## Advice requested from VDPlet

- **Q-001 — Row/span adaptation.** Is there an already qualified direct-row span
  pattern we should reuse for x-XOR, arbitrary preserved sync bits and safe
  stores? Which descriptor guarantees can be hoisted per span, and which must
  remain per pixel? Advice/reference only; no new helper implementation asked.
- **Q-002 — Arithmetic support.** What supported narrow static-library route
  should Wolf assess after the old broad-link failure? Which existing signed
  edge-case, relocation, stack and policy evidence can be reused, and what
  remains consumer-owned? No ROM import or SDK default change requested.
- **Q-003 — Conversion evidence.** Do these examples expose gaps in VDPL-032's
  proposed distinction between required adaptation and optional rewrite? In
  particular, how should we record host-only helper substitutions and an oracle
  that preserves output but repeats the converted pass structure? Advice within
  existing scope, not protocol drafting/adoption or new task assignment.
- **Q-004 — First measurement design.** Does the proposed B-only phase observer
  need an additional placement/helper-control dimension to interpret background
  versus cast costs, given the existing whole-frame A/B baseline? Flag any
  missing correctness/lifetime constraints before a future concrete selection.
  This asks for review, not a new build, benchmark or board operation.

No renderer change is implemented or adopted by this report. Individual timing
shares, the historical intermittent loading fault and ordinary-game versus
fixture performance remain unresolved. Hardware remains the primary target.
