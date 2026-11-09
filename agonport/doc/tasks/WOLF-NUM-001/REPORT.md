# WOLF-NUM-001 — Numerical methods and wire-boundary review

November 9, 2026. **Read-only review complete; stopped for Smith’s report review.**
Task preparation was committed/pushed as `dcfef76`. Smith then directly approved
proceeding with this review/report. That releases the previous review hold, not
implementation, experiments, builds, benchmarks, reservations, device work,
optimization adoption or the paused WOLF-GOAL-001.

The shared references remain VDPL-037 **NUM-06/FUP-004/WIRE-001..005** and
CMP-001..005. This report reviews Wolf’s current source, retained target
artifacts and earlier results. It does not choose a cross-project winner.
[Read-time identities and evidence distinctions](SOURCE-PINS.json) accompany it.

## Findings for discussion

1. **Wolf already uses an integer pipeline across both processors.** The eZ80
   uses degree-indexed movement deltas; the current wire carries fixed-point
   coordinates and degree angles; VDP view/ray/projection/texture work is integer.
   There is no active radians-to-phase/half/float conversion chain here to
   remove. Host-side floating-point table generation is a different operation.
2. **The exact degree-table reduction is valid in the restored-ray candidate,
   not a drop-in replacement for the production default’s fine-ray sine table.**
   Its proven saving is 2164 B resident data and 64 B text. Its isolated timing
   benefit remains unmeasured. Coarser table use must not change fine ray angles.
3. **Bounded arithmetic has already produced a concrete reusable example.**
   PERF017 preserves the signed/wide contract and uses one hardware unsigned
   divide when both magnitudes fit 32 bits. Retained source bounds cover current
   validated sprite projections; emitted native instructions confirm the path.
   Neither a general integer-over-float winner nor a new library is established.
4. **A shared angle256 format is an interoperability proposal, not an immediate
   Wolf packet-size optimization.** Its proposed 16-bit phase consumes the same
   two angle bytes. Wolf would gain conversions unless its callers also change.
   Three-byte position fields are a separate, bounded lossless wire proposal.
5. **The maintained production module and fastest completed experimental module
   remain different selections.** The default is `266f809f`; combined `8d3d19bb`
   has the strongest completed later comparison. Later `b181a8fd` has no completed
   candidate timing result. No default is changed by this review.
6. **There is a source-level portability defect in the older/default fixed
   divider.** It left-shifts a possibly negative signed value under C++17.
   This warrants a correctness disposition before generic reuse; it is not an
   observed crash, explanation for prior stalls, or a newly executed test.

## Exact source and build selections

| Selection | What is active or retained | Review disposition |
| --- | --- | --- |
| Routine CLI/current payload | `tools/wolf_firmware.py` selects production module `266f809ff76e56733251da202e5c4747cd9c12d247d799d486471a262c0404b7`; CLI defaults to `vdplet-direct` | Source wrapper, renderer, mirror, contract and tables hash-match its retained build receipt; module bytes also match. Package 18636 B, resident text 13144 B/data 9720 B. This is current preparation selection, not a live-board observation. |
| Manual tracked assembly selector | `wolf3d_backend.inc` still says standalone | Historical bespoke/manual path; FIRMWARE.md and CLI override it for routine preparation. It is not evidence that a routine package uses bespoke firmware. |
| Original-ray numeric comparison control | `a926b48a…`, 24420 B, text 15360 B/data 13348 B | Retained optimized experiment control, not the older production default. Numeric comparisons must retain this exact predecessor. |
| Isolated degree table | PERF015 `2844fda5…`, 22180 B, text 15296 B/data 11184 B | Correctness/footprint-qualified candidate; isolated physical timing still pending. |
| Isolated guarded divider | PERF017 `12857ecf…`, 24424 B, text 15364 B/data 13348 B | Qualified arithmetic/native body; completed historical physical comparison has drift limits below. |
| Combined experiment | PERF021 `8d3d19bb…`, 22572 B, text 15676 B/data 11184 B | Combines cyan extent, degree table, narrow divider, full-height setup cache and column chains. Completed in actual95; not production-default adoption. |
| Later byte-span arm | PERF023 `b181a8fd…`, 22620 B, text 15724 B/data 11184 B | Numeric bodies unchanged; host/target-code qualified. Actual99 did not collect candidate timing, so “later” does not mean faster. |

The production source/package join was checked from existing files during this
review, without rebuilding. Historical performance used its own older firmware
and native timing environment. The current dc43ecb8 async-r1 release is not that
historical environment. Old numerical evidence is reusable with its scope;
current firmware/whole-task/runtime performance acceptance is still separate.

## Active methods and numeric domains

| Unit and source | Representation and work | Frequency, costs and limits |
| --- | --- | --- |
| eZ80 player motion: `wolf3d_motion.inc:1004–1125`, `wolf3d_motion_table.inc`, `gen_motion_table.py` | Persistent angle is a little-endian u16 degree value 0..359. Ordinary turn is ±3 degrees. A 360-entry table supplies signed 24-bit dx/dy; each raw coordinate unit is 1/65536 tile, canonical distance 0x1000. Heading 0=east, 90=north, map +Y=south. | 2160 table bytes. Movement lookup uses adds for angle×6 and no runtime trig. Python math/round is used only when generating the table. Scaled movement uses the existing signed 16×16→32 helper and arithmetic shift by 12; generic reuse must retain actual caller bounds. |
| eZ80 arithmetic/line of sight: `wolf3d_math.inc`, `wolf3d_sight.inc:199–238` | Byte MLT-based unsigned/signed 16×16→32; signed 8.8 slope with nonzero denominator, truncation and ±32767 clamp; partial multiplication uses arithmetic floor. | The slope division is a 16-round restoring loop used by AI sight boundary scanning. It is not VDP per-column rendering. Dynamic call counts and CPU time share were not measured here. |
| Production view/rays: `production/wolf3d_renderer.cpp:112–137,221–228,370–539` | int32 Q16.16 coordinates/trig outputs; degree×10 gives fine angles, 3600 units/turn. Quarter-wave 901×int32 sine samples; cosine offsets by 900. Per-column reciprocal-distance DDA uses fixed division, additions and 128-crossing bound. | View setup has two trig calls, but this older/default raycaster also has two trig calls and up to two setup divisions for each of 256 columns; doors/pushwalls add work. The quarter table is needed at fine, not just whole-degree, angles. |
| Restored ray method: PERF021 candidate `original_raywalk.h:11–59,89–147` | 900 int32 half-bin tangent/reciprocal entries, signed quadrant slopes, partial-tile products and explicitly expressed word/wrap/high-word comparisons. Fine view angle plus per-column offset remains. | 3600 tangent bytes and 512 bytes of 256 int16 pixel angles. Per-ray reciprocal setup divisions and analytic slab cast are removed. Traversal/door/corner/texture decisions intentionally restore original-method behavior and are not byte-identical to the old DDA. |
| Candidate view: PERF021 renderer `setup_view:229–236` | Exact 360-entry int32 degree table; cosine uses degree+90. Same focal multiplication and signs. | 1440 table bytes, two setup lookups/frame. The 901-entry quarter table can disappear because this ray walk uses tangents, not per-ray sine/cosine. Fine tangent/pixel-angle bytes remain unchanged. |
| Projection: production renderer `361–368,604–620`; candidate `295–301,442–458` | Camera/object differences and depth remain Q16.16 int32. Products widen to int64 before right-shift 16. Sprite screen X uses int64 lateral×87/depth. Near-depth guard is 0x5800; height uses a separate integer division after shifting depth by 8. | Up to one transform for each active actor/static; not one wide division per wall ray after the original-ray restoration. Existing source bounds and observed caller populations are below. There is wall-height/sprite-depth metadata, not a general triangle per-pixel depth buffer. |
| Texture sampling: production renderer `579–595,715–750` and candidate wall cache | Integer clipped pixel extents; 64×64 texture steps use 16 fractional bits and scalar increments. No trig/float in the pixel sampler. Cache reuses setup only for equal **full** wall heights. | At most 256 wall-column setups before reuse; fill/sprite pixel work still scales with actual covered area. Retain clipping, masks, pointer/asset lifetime and alias ordering; arithmetic equality alone does not authorize reordered memory access. |
| Simulation/time: `wolf3d_motion.inc:4–7,30–33`, `wolf3d.asm:1259–1358` | Four MOS 120 Hz ticks per fixed update, bounded catch-up; dirty world snapshot only after catch-up and prior render completion. | The ordinary full game remains capped by its 30 Hz simulation/render scheduling. Uncapped benchmark fixtures are separate. Numeric kernel gains do not themselves remove this client scheduling limit or establish an async newest-pose pipeline. |

No target `sinf`, `cosf` or half-precision interpolation is used in these
reviewed Wolf paths. The generation scripts use host sin/cos/atan/tan and exact
recorded integerization rules. These should not be counted as runtime FPU work.

## NUM-06: what the table evidence actually proves

The retained PERF015 test includes the actual candidate `setup_view` and an
independent retained quarter-table reconstruction. Its loop visits all 65536
u16 angle words at four positions; the saved log reports **262144** passing
setup cases. Those positions include values outside validated world coordinates:
this is a helper-domain check, not permission to accept such network poses.
The existing renderer/module/failure checks and 600 scripted frame/state outputs
agree; 600 scripted frames are not all possible gameplay states or all headings.
None of those tests were rerun for this review.

The retained final map contains `kWolfSinDegree` size `0x5a0` (1440 B), fine
pixel angles `0x200` (512 B), and tangent table `0xe10` (3600 B). Original
qualification records the removed quarter-table symbol and exact retained
values. Package size falls 24420→22180 B (2240 B); resident data falls
13348→11184 B (2164 B), and text falls 15360→15296 B (64 B).

This saving requires the restored-ray context. Removing the fine sine table
from the routine production renderer would remove data its rays still use.
Nor can a generic angle256 lookup/interpolation replace degree/fine methods
under the label “same table”: normalization, quantization, focal rounding,
texture face ownership and generated-code footprint need explicit controls.

## Bounded arithmetic and generated native code

The retained projection-domain argument assumes validated player/actor raw
coordinates in `[0,64×65536)` and trig magnitude ≤65536. With focal offset
F=22272, coordinate difference magnitude is bounded by G=4216575; lateral
magnitude ≤8433150, forward magnitude ≤8449534. After the positive-depth guard,
`abs(lateral×87) ≤733684050 <2^32`, and the positive denominator also fits u32.
The widening in the existing products remains part of that proof.

PERF017 therefore keeps the general helper but adds a guarded u32 path **after**
the zero check. The saved candidate disassembly shows denominator-zero branch
at 0x3c94, high-word branch at 0x3c9a, and unsigned **QUOU at 0x3c9c**; the
48-byte-frame helper has no recursive CALL/CALLX path. Source high words and
zero-extension preserve unsigned results above INT32_MAX; the original signed
magnitude wrapper and wide fallback remain. The baseline production disassembly
instead shows the original software loop with 64 iterations.

The prior independent extracted-body qualification reports 1000576 unsigned/
signed pairs with explicit exceptional-bit oracles. That is finite coverage,
not exhaustive 64-bit-domain native execution. The saved 600-pose room coverage
has 35992 actual-source projection input pairs (~60/frame), all narrow-eligible;
the eight-static fixture has 2072 (~3.45/frame). Those are host/source input
counts with target call binding, not native sampled hit counters. Old claims
of 512 avoided wide ray divides/frame are obsolete for the restored-ray build.

Actual85 measured control/candidate inclusive draw means 25.136/24.602 ms,
2.125% lower in that cohort, while control drift was 3.111%. Both candidates
were below both controls, but that is not a precise isolated effect estimate;
presentation remained ~30.06 fps. The +4 B package cost and reduced repeated
arithmetic remain useful evidence even without an FPS gain.

These guarded integer helpers are a better grounded Wolf reuse candidate than
an unmeasured wholesale float replacement. This is a comparison priority, not
a selection/adoption. A generic libgcc provider remains separately blocked by
its retained allocated `.eh_frame` admission issue; no stripping or guard
relaxation is proposed.

## Source correctness issue to resolve before broad reuse

The routine/default renderer’s `fixed_div` at lines 117–119 uses
`(int64_t(a) << 16) / b`. Door-plane calls (lines 455/468) and pushwall slab
calls (323–336) allow negative coordinate differences. Under the recorded
C++17 build mode, shifting a negative signed operand left has undefined
behavior; widening to int64 first does not make that defined. See the
[C++17 draft shift rules](https://timsong-cpp.github.io/cppwp/n4659/expr.shift).
This is a concrete source defect when such a negative argument is reached;
no new target reproduction or causal link to historical rendering/loading
failures is claimed.

The newer restored-ray candidate removes this helper/call family rather than
reusing it. Any selected correction of the old helper should specify defined
scaled arithmetic, denominator/range and narrowing behavior, and compare exact
existing geometry/door/pushwall controls. No fix is made in this review.
Similarly, negative signed right shifts in `fixed_mul` rely on the pinned
compiler’s arithmetic-shift behavior under C++17; a shared implementation must
state floor-versus-truncation explicitly instead of relying on a different
processor/compiler to make the same choice.

## WIRE-001..005: current contract and opportunities

The active VDPlet route uses the exact W3P schema-2 descriptor and W3DU batches,
not FSIM’s F060 encoding. `wolf3d_vdplet_batch.inc:299–305` copies the 10-byte
player pose without numeric conversion; its generic append is a byte copy.
`wolf3d_world_mirror.cpp:28–52,244–249,403–406` decodes explicit little-endian
u16/u32 fields, validates them, then stores typed mirror fields. It does not
serialize native C structs. The bespoke historical route also copies this pose
under its private 4A commands; that is a different firmware/protocol path.

| Domain | Current wire contract | Consequence for shared formats |
| --- | --- | --- |
| Player | x:i32, y:i32 in Q16.16 tile coordinates; angle:u16 whole degrees; 10 payload bytes | Position acceptance is 0≤raw<4194304; degree acceptance is 0≤angle<360. There is already direct numeric agreement across CPUs. |
| Actor | 15-byte record: id:u16, shape:i16, x:i32, y:i32, facing:u16 degrees, rotations:u8 | Rotation uses 0/2/8 sprite directions; no reason to reinterpret all fields as one Q format. Actor position/angle validation has the same bounds. |
| Door | id:u8 plus 8-byte established record, including u16 aperture | Aperture is a 16-bit tile fraction, not an angle. Preserve endpoint/equality semantics; old DDA and restored original method deliberately differ. |
| Static/mesh-like data | Tile coordinates are explicit bytes; shape identifiers are integers | Wolf has no F060 1/32767 mesh/pose scale decode on this route. Those survey constants must not be assigned to Wolf by analogy. |
| Pushwall | Cardinal direction codes and u8 fractional position 0..63 | Offset uses position×1024 in Q16.16. A common container does not make these angle256 or ordinary u16 fractions. |
| Time/depth/texture | Simulation tick state stays local; projected depth and texture increments stay renderer-local | Avoid sending or converting them merely to force one cross-project format. Preserve the actual boundary first. |

**Angle256 proposal:** a u16 8.8 angle256 phase has quarter-turn 0x4000 and
step 360/65536 degrees, with modulo-65536 wrap. It is finer than Wolf’s current
integer-degree pose, but occupies the same two bytes. One degree is not an
integer number of these phase steps. Exact current angle/fine-table behavior
therefore needs an explicit mapping/rounding contract, not reinterpretation.
Keeping current degree-based motion, actor facing and ray setup would add
conversions; migrating them all is a gameplay/precision change, not a free
serialization optimization. Signed shortest-difference must specify the
half-turn tie and wrap. No phase encoding is selected here.

**Position packing proposal:** validated map positions need only 22 raw bits.
An explicitly encoded signed 24-bit container can represent every accepted
current position without losing any of its 16 fractional bits. Two coordinates
would occupy six bytes instead of eight: player payload 10→8 bytes, actor
record 15→13 bytes. This is a domain argument, not tested encoder/decoder code.
A player-only batch would shrink 16-byte header + 2-byte record header +
10-byte payload =28 bytes to26 bytes, about7.14% of that batch, not7.14% of
whole UART traffic/frame time. Upload/consolidation/RUN/response overhead stays.
The current assembly already uses signed 24-bit motion deltas, but it extends
and applies them to four-byte persistent coordinates; those are distinct uses.

Any future packed-coordinate/phase contract needs explicit byte order, sign
extension, exact valid ranges, negative rounding, overflow/saturation-or-failure,
alignment and independent encode/decode vectors on both CPUs. Reject invalid
inputs before mutation; retain whole-batch generation/duplicate/retry semantics.
Do not let eZ80 24-bit int or ESP32 32-bit int/native padding define the wire.

## What existing performance can and cannot establish

| Evidence | Established result | Limit relevant to this review |
| --- | --- | --- |
| PERF015 isolated | Exact view/retained output parity; resource savings above | No isolated hardware speed measurement; actual84 stopped before any room. |
| PERF017 actual85 | 2400 poses; guarded divider draw result above | Control drift; no native branch counter or exact per-call time share. |
| PERF018 actual87 | Full-height setup cache: 25.137→25.247 ms pooled, 0.438% increase amid 3.134% control drift | No established gain or precise regression. Opportunity counts are not speed evidence. |
| PERF019 actual89 | Startup failed before room/probe execution | No isolated chain/trig timing verdict. |
| Combined021 in actual95 | 3600 poses: original24.9555, cyan21.7146, combined20.9025 ms; ~30.06 fps for all. Combined is16.24% below original and3.74% below cyan. | Remaining four units are combined, not separately attributed or proved additive. Nominal 240 MHz inclusive draw includes preemption/services; fences are not optical scanout. |
| PERF023 actual99 | Control collected600 poses; candidate returned to CLI | Candidate timing not retrieved after observer interruption; no speed verdict. |
| Full-game profile actual105 | 250 populated game submissions, native draw mean22.19 ms, logging-excluded ordered completions ~30.06/s | Different workload/normal scheduling, not a new maximum-rate pipeline. Suite failed later during listener retirement; valid saved samples and cleanup are separate. Logging hitches affect play. |

Numerical work reduction, memory footprint, render time and visible cadence
are separate results. Unchanged FPS alone is not a reason to discard reduced
inner-loop work; nor does reduced source work prove a timing share. No new
measurements, report-decoder replay or target execution were performed here.

## Provenance and reusable units

- Movement table: project generator, Python host trig and `round`, explicit
  signed24 output. Renderer quarter sine/pixel angles: `generate_fixture.py`
  uses its own lround and scale. Matching domains does not establish identical
  generated bytes between those generators; retain exact controls.
- Tangent method: PERF007 generation follows the pinned WL_MAIN.C formula with
  original PI constant and binary32 radtoint narrowing. Its record explicitly
  does not claim historical Borland-libm byte identity or personal authorship
  of every original function. Preserve quadrant/grid/door/face tie decisions.
- eZ80 arithmetic’s source attributes a subset to project-owned AgonMaths work.
  That comment is provenance, not a complete separately packaged helper licence.
  README licensing/attribution and the ignored original source’s LICENSE.DOC
  must remain part of any extraction decision; original game reference/assets
  do not acquire the project’s own-contribution rights waiver.
- Prefer optional linked helpers, shared exact table generators and explicit
  wire definitions, with processor-specific kernels where appropriate. Do not
  add every method permanently to base firmware. External survey candidates
  were not freshly audited here; their owner’s range/licence/active-caller
  evidence is still required before importing one. No code was imported.

## Ranked comparison proposals — not assignments or experiments

1. **Close numerical contracts and the old signed-shift defect first.** Small,
   well-defined scope; prevents a shared helper from reproducing undefined or
   processor-dependent behavior. Preserve current output controls and failure
   domains. This report does not select the correction.
2. **Evaluate extracting the already-qualified bounded integer helper pattern.**
   Guard→narrow unsigned divide→exact fallback, signed wrapper and actual native
   lowering provide a concrete model. Test whole caller/conversion costs on each
   CPU before calling it a shared winner. Preserve zero/exceptional patterns.
3. **Compare exact degree table representation as a resource option in its
   proper ray context.** Reuse PERF015’s independent oracle and source controls;
   evaluate cache/data/stack and frame contribution without claiming an FPS win.
   Do not replace fine rays with degree sampling or repeat the existing task.
4. **Consider precise 24-bit position packing only if wire cost is material.**
   Bind a new explicit serializer/decoder schema and measure total transactions.
   Preserving all fractional bits makes this more concrete for Wolf than merely
   adopting a new angle container, but byte savings alone do not select it.
5. **Evaluate shared angle256/interpolation or float alternatives only with a
   consumer reason and an agreed precision budget.** Wolf currently needs no
   runtime float/half conversion. Include the cost of changing motion/facing,
   conversion endpoints and ray/table semantics. No FPU-based winner assumed.

## Proposed future measurement and stop rules

After Smith selects a concrete comparison, freeze its exact original/candidate
source, tables, provider, compiler flags, package and actual producer operands.
Separate arithmetic, representation, storage width and table changes. Do not
combine a wire redesign, new trig approximation and scheduler change and then
attribute the result to one multiply instruction.

Use existing exact-angle and helper oracles where their domains match, plus
independent wire vectors for wrap/quadrants/half-turn ties, coordinate extrema,
negative values, zero denominator, saturation/refusal and narrowing. Measure
both actual processors with the same caller populations; include a canonical
room and a separately justified actor-rich workload if projection is the axis.
Capture input/simulation/encode/upload/decode/render/presentation boundaries,
clock frequency/wrap and actual call/branch populations. Count packet/framing
bytes and memory traffic; record code/data and whole-task stack constraints.
Keep disk/cue/retrieval phases marked and excluded from timing intervals while
acknowledging their effect on play/catch-up/cache state.

Performance fixtures must be uncapped. Normal-game scheduling and optional
paced presentation are separate selections. Alexe supports correctness, not
ESP32 wall-time performance. Preserve incomplete cohorts, control drift,
preemption/inclusive timing, ordered-fence versus scanout distinctions and
separate human visual acceptance. Use current FIRMWARE.md/actual admission,
finite bounds, first unexpected stop and normal cleanup; no old kit/token or
routine private-firmware installation is selected by this report.

**Stopped for Smith’s review.** No implementation, test, compiler/bench/Oryx
reservation, device action, default adoption or goal resumption is selected.
The substantive central-survey return is held until Smith reviews this report;
its findings remain linked to the existing NUM/FUP/WIRE IDs rather than a new
cross-project follow-up register.
