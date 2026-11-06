# Setup blocker: consumer requirements for a less intrusive diagnostic

WOLF-PERF-003-09 is a dependency of the existing matched benchmark. Smith's
authorized benchmark/debug work continues; this addendum preserves the frozen
plan5599f43 and every failed/successful cohort. Flexe owns model/adapter and
telemetry changes. Wolf requests a component-owned source/design review before
selecting any implementation, build, new diagnostic artifact or target cohort.

## Evidence and limits

Original7e7d0e1b/0866265b setup failures occur in B's diagnostic zero upload,
A's SFX upload and A's shell upload. The latest1,030,018-byte failed host stream
exactly prefixes the successful2,362,684-byte s01 A stream. Flexe independently
confirmed the comparison. Equal host bytes exclude a payload difference before
truncation; they do not establish admission timing, guest receipt, parser state
or a common cause. Output equals delivery and final backend faults are zero;
final cumulative cycle totals do not prove progress late in the stalled window.

The625d08b7 FX-152 diagnostic completed both s01 cases with zero observer samples.
No live stalled producer/TX state was captured. Flexe's source review finds it
republishes the retained15-word TX array plus CTS history on every phase update.
That extra atomic work could affect scheduling; it has not been shown to cause
nonreproduction or fix a race. No performance-equivalence or repair claim follows.
The latest control never reached PRT initialization, so restoration is untested.

Source of this finding and proposed next boundary:
2026-11-05_13-08-36_flexe_wolf-perf003-prefix-source-advice-107 and
flexe-agon-emulator/docs/tasks/FX-152/WOLF-PERF003-ADVICE.md. No already-qualified
transport repair is established for the exact composition. HALT and MOS-clock
changes are separate. Historical firmware UART recovery work needs exact source/
driver ordering review by the relevant firmware/UART owners before applicability.

## Requested design review

Return a concrete source/contract proposal for publishing retained TX state only
when its owner-batch snapshot changes. Keep the original forwarding/status calls,
arguments and return values unchanged. Preserve one coherent publication/version
boundary, the TX snapshot batch tag and epoch, persistent completed CTS history,
and readable entered-call state while a call blocks. A reader must distinguish
old batch state from current phase state. Avoid holding an odd version across a
potentially blocking call or silently substituting cached phase data.

Retain bounded atomic data, four snapshot attempts with explicit unavailable/
null/overflow states, the existing fixed trigger/sample/lifetime/output ceilings,
and no observer process, busy poll, extra CTS query, per-byte allocation/file I/O,
lock acquisition in the reader or guest/native probe. Disabled diagnostics must
preserve forwarding semantics and avoid telemetry work where the contract allows.
Describe remaining unavoidable producer/publication work honestly; less atomic
work is not proof of zero scheduling effect or performance equivalence.

Identify real-path host checks needed before a later implementation is selected:
owner-batch TX accounting/epoch/flush/shift behavior, phase/CTS history across a
blocked call, concurrent coherent reads and unavailable snapshots, and enabled/
disabled forwarding/status parity. Specify exact source base, intended schema
and reader compatibility/versioning, footprint and proposed transformation pins.
Design review alone supplies neither host-test results nor a candidate identity.

Return the proposal for consumer disposition. This request selects no compiler
reservation, executable build, emulator replay, firmware change, hardware slot,
runtime adoption or publication. A later selected consumer cohort requires its
own finite schedule, exact freeze and normal fresh FIFO checkout. Original setup
failures remain failures; benchmark ranking and physical performance stay pending.
