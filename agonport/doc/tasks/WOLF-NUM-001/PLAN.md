# WOLF-NUM-001 — Numerical methods and wire-boundary review

**Status: task prepared; review execution held for Smith’s direct discussion.**
Only this task preparation is released. No source audit, comparison execution,
implementation, build, test, benchmark, reservation, device/firmware action,
adoption, peer dispatch or paused-goal resumption follows from writing it.
No automatic continuation after task preparation or elapsed time.

## Authority and shared record

Coordinator request:
`2026-11-09_17-31-46_vdplet_vdpl037-local-review-task-preparation-wolf3dorig`,
thread `vdpl037-numeric-methods`. Smith completed the survey and requests local
review task preparation, then a stop until he speaks with each owner directly.

Central survey:
`/Agon/mystuff/agon-vdplet/docs/tasks/VDPL-037/NUMERIC-METHODS-SURVEY.md`,
read-time SHA256
`1a9062d79ea513ffb6b1de5b13cdaa03f01254851e0cce1b2aa77789a155e42f`.
Exact surveyed source pins remain in its adjacent
`NUMERIC-METHODS-SOURCE-PINS.json`. Cross-project discussion/follow-ups remain
centralized there; this is Wolf’s future local review, not another shared
follow-up register.

Relevant IDs: **NUM-06, FUP-004, WIRE-001 through WIRE-005**; comparison
criteria CMP-001 through CMP-005. Other projects’ NUM items are contextual
comparison candidates, not assignments to inspect or modify their projects.

## Existing work to reuse rather than repeat

- [WOLF-PERF-015](../WOLF-PERF-015/PLAN.md) owns the exact whole-degree
  view-table representation and its retained qualification/timing questions.
  NUM-06 reports 262144 setup cases and 600 scripted frames equal, 2164 B less
  resident data and 64 B less text. These are cited owner/survey records,
  **not independently reverified during preparation**. Footprint is distinct
  from an FPS gain. Retain the fine ray-angle/tangent domain separately.
- WOLF-PERF-007 owns the restored original ray method and its deliberate
  original-versus-port numerical differences; WOLF-PERF-017 owns the local
  division/projection evidence. Reconcile their existing records when review
  is released; do not create replacement optimization arms or replay cohorts.
- WOLF-PERF-021 and the later retained candidates provide composition and
  producer/control history. Determine actual active/default/experimental
  status during the future review rather than assuming a later name won.
- WOLF-GOAL-001 remains paused. Its outstanding work and the independent clean
  faithful-port work are not resumed or changed by this task.

## Future review checklist — all execution held

- [x] WOLF-NUM-001-01 — Read the coordinator request/survey, prepare this task
  and register it in TODO. Return path/ID and readiness, then stop.
- [ ] WOLF-NUM-001-02 — After Smith’s direct release, inventory exact current
  Wolf caller paths and retained controls: eZ80 simulation/input/pose producer,
  serialization, VDP decoding, view setup, trig, ray stepping, projection,
  texture increments and drawing. Record active versus unused helpers,
  build selection, source identity, table origin and evidence provenance.
- [ ] WOLF-NUM-001-03 — Reconcile existing correctness, code/data, stack,
  provider, hardware timing and visible-cadence records. Separate host/model
  coverage, actual native code and full hardware results; mark missing,
  interrupted, unmeasured or historical evidence explicitly.
- [ ] WOLF-NUM-001-04 — Trace representation and conversion boundaries by
  domain; answer the questions below without selecting a new format/kernel.
- [ ] WOLF-NUM-001-05 — Specify accuracy/range/overflow and generated-code
  evidence needed for a fair future comparison. Locate licences/attribution
  and original-method provenance before proposing any reuse/import.
- [ ] WOLF-NUM-001-06 — Propose a bounded matched processor/wire/caller
  measurement plan and failure controls. No run or reservation is selected
  by this checklist; freeze any later selected experiment separately.
- [ ] WOLF-NUM-001-07 — Return the local ledger, evidence gaps and comparison
  proposal to the VDPL-037 coordinator for the central survey. Distinguish
  demonstrated facts, hypotheses and deferred work; no presumed winner.

## Questions and required local ledger

For each actual method/caller, record its source/hash/build identity, original
control, input/output representation, call frequency, table/resource placement,
conversions, helper/provider calls, code/data/stack cost and existing outcome.
Separate the algorithm, table generation, representation and processor kernel.

1. NUM-06: Where are exact whole-degree samples sufficient, and where are finer
   ray-angle tables essential? Keep existing source-domain normalization,
   quarter-turn signs/endpoints and the independent original-table oracle.
   Never infer a speed gain from smaller tables or two setup lookups/frame.
2. WIRE-001: What angle representation actually crosses Wolf’s boundary?
   Compare, as proposals, explicit angle256 phase contracts and the existing
   representation: width, signedness, fractional bits, wrap, shortest signed
   difference, quarter-turn and byte order. Do not equate degrees, fine angles,
   angle256 or an ambiguously named 16.16 value.
3. WIRE-002/003: Inventory positions, local offsets, directions, angles, time,
   depth and texture increments separately. Determine whether any F060-style
   scaling is actually used by Wolf; its surveyed constants are not a Wolf
   contract by inference. Do not silently change original controls.
4. WIRE-004: Where could compatible representations remove boundary
   conversions, packet bytes or widening without losing required precision?
   Compare complete encode/decode/caller/draw costs. Neither ESP32 FPU presence
   nor eZ80 integer convenience establishes the best end-to-end method.
5. WIRE-005: Specify exact widths, ranges, scales, negative rounding, overflow,
   saturation versus failure, endian and alignment. Account for eZ80 24-bit
   int versus ESP32 32-bit int; native C struct layout is not a wire contract.

## Accuracy and generated-code requirements for later proposals

Preserve exact controls where exact equivalence is required. Any deliberately
approximate alternative needs a separately agreed error budget and downstream
geometry/state/visible consequences. Cover wrap/quadrants, signed extrema,
zero denominators, narrowing, shifts/products, exceptional helper inputs and
fallback domains. State whether a boundary is proved or merely sampled.

Inspect actual compiled target bodies, provider/helper resolution and table
placement; host-only bodies or optimized-away unused code do not prove native
cost. Include setup versus per-column/per-pixel frequency, widening/narrowing,
lookup memory traffic, package/resident bytes and whole-task stack. Current
firmware limits and original table/geometry controls remain requirements.

## Proposed measurement and failure controls — not dispatched

Any later selected experiment should preserve identical input states, scene,
call frequency, producer operands and resource placement, with original and
candidate arms bound independently. Separate arithmetic cost, storage width,
table/cache footprint and overdraw. Include both actual CPUs and wire
encoding/decoding/bytes, pose responsiveness, complete frame contribution and
presentation cadence. Use maximum uncapped rate for any selected performance
fixture; an optional paced presentation arm would need its own explicit scope.
Alexe can support correctness checks; its wall time is not ESP32 performance.
Human visual acceptance remains separate from numerical and timing results.

Before a future run: prove exact producer/package joins, define correctness
oracles and negative controls, freeze current firmware/source/resource limits,
set finite bounds/first-unexpected-stop and normal owned cleanup. Preserve
failures, missed responses, incomplete cohorts and controls; do not replay or
promote automatically. Apply FIRMWARE.md/current actual admission, including
explicit justified firmware exceptions if inherently needed. No resource
reservation or new target scope is authorized by this document.

## Deliverables and stop boundary

Future review returns an active-method/conversion ledger, retained-evidence
index, range/precision/licence constraints, unanswered questions and ranked
comparison proposals linked to the central IDs. Any later code, import, SDK,
wire or firmware promotion requires its own selected contract and qualification.

**Preparation return now: WOLF-NUM-001, this PLAN.md, ready for Smith discussion.
STOP here until Smith speaks with Wolf directly. No review has begun.**
