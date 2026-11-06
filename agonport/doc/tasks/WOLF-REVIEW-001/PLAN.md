# WOLF-REVIEW-001 — Self-review of bespoke-to-VDPlet conversion drift

Review how Wolf's conversion changed renderer work, generated code and observed
behavior, and why our qualification did not expose the differences sooner.
Supply concrete examples and detection/correction methods to VDPlet's related
VDPL-032 conversion study, and ask for advice about the remaining uncertainties.
Smith requested this review and sharing on 2026-11-06, then instructed that the
tasks be written first. Freeze this plan before performing the review.

## Tracking and deliverables

Root TODO.md is the authoritative checklist. Immutable IDs WOLF-REVIEW-001-01
through -05 are never renumbered or reused. Record dispositions and evidence in
the dated development log. Keep the frozen plan unchanged; put the freeze hash,
review findings, provenance and communication receipts in separate artifacts.

- **-01: Task freeze.** Publish this plan and its TODO entries in a dedicated
  commit before the review. Preserve unrelated work and accepted baselines.
- **-02: Conversion history and implementation trace.** Inspect the existing
  migration/direct-row plans, dated logs, source history, production source and
  retained source/ELF analysis. Identify when and why important substitutions
  entered, distinguishing recorded rationale from inference or absent evidence.
- **-03: Qualification and review failures.** Compare actual acceptance criteria
  with the evidence produced. Examine algorithm/work parity, independent
  oracles, scene binding, double-buffer progress, generated helpers and compiler
  policy, target measurements and performance claims. Identify both useful
  checks and missed checks; do not equate visual parity with equal work.
- **-04: Correction and prevention examples.** For each supported divergence,
  record original and replacement mechanisms, concrete source/binary pins,
  required interface adaptation versus avoidable change, a detection method,
  and a smallest separately testable correction with correctness/resource
  constraints. Mark unmeasured timing shares and unimplemented candidates.
  Include focused questions for the SDK/runtime owner where advice is needed.
- **-05: Share and close the review.** Send the retained findings and advice
  questions to VDPlet using the existing mailbox/thread, with immediate chat
  notification. Preserve the delivery receipt and report back to Smith. Record
  any later substantive advice separately; an acknowledgment is not required
  to finish this finite review. Do not edit VDPlet's task or central digest.

## Fixed evidence and limits

Start from Wolf's physical comparison commit
`32dc1ee24ab1cc276d9063230a616ac3fae9c2af`,
`WOLF-PERF-003/HARDWARE-R09-RESULT.md`, its exact native/module identities and
6,180 exported samples. Drawing means 30.701/91.560 ms are the aggregate
bespoke/VDPlet result at configured clocks. VDPlet's VDPL-031 contract freeze
is `6755f39175989ad93901d915de48e100c20b4f43`; its initial source/ELF findings
and finite measurement proposals are supporting evidence, not causal timing.
Record content hashes for any evolving source/advice documents actually used.

The review may read history/source/manifests/disassembly and perform bounded
device-free counts on existing artifacts. No compilation, emulator/hardware
run, reservation, firmware change, consumer optimization, ABI change or shared
policy adoption is part of this task. Do not mutate retained raw evidence or
make benchmark comparisons from newly selected workloads. Proposed safeguards
are review recommendations, not new standing policies or automatic gates.

Preserve scoped row lifetimes, x-XOR mapping, sync bits, fixed-point semantics,
compiler PSRAM correctness safeguards, canonical pixels/state and resource
limits in every correction proposal. Do not hardcode firmware ROM addresses
into a module or claim that different helper names prove a speed difference.
Separate source facts, generated-code observations, measured aggregate results,
inferences and candidates. Stop a claim when artifact identity cannot be bound;
record the missing evidence instead of filling the gap with a plausible story.

Deliver a concise findings report and a provenance ledger here. The report must
include Wolf-owned review failures and concrete examples useful beyond Wolf,
with advice requests that respect VDPL-032's actual scope. No peer build,
implementation, run or protocol adoption is commissioned by sharing the review.
