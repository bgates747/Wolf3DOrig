# Loading-query diagnostic design — WOLF-PERF-003-16

Status: initial source proposal after Olimex42, now implemented as the separately
identified [loading04 preparation](HARDWARE-LOADING-R04.md). That record owns the
selected finite plan/current readiness. Preserve hardware03 source/RAM/serial.

The question is why a loading-only mode query fails after a breadcrumb flip,
with one printed0x86 and no recognized reply. Longer waits did not recover it.
The sender descriptor is intact; actual receiver timing and grammar are unknown.
See HARDWARE-R03-RESULT.md for exact evidence and both source-owner returns.

## Proposed task-owned observation

Keep current asset bytes, header/payload boundaries, synchronous RST18 sends,
C3 ordering, both-page paint, one flag clear/query and bounded same-pending wait.
Do not split the three-byte query into per-byte calls or insert debug VDU text.
Keep interrupts enabled. No extra flag clear, query resubmit, asset replay or
render-loop timing change. Observation overhead can still perturb the failure.

Use a new RAM record/version, leaving WPL2 and old parsers intact. Retain a fixed
ring of the last32 completed fences plus the current in-progress fence; freeze
at the first failure. Save only after normal loader close/return, and preserve
full RAM before any LOAD if abnormal. No file/serial diagnostics inside callbacks.
Record stage/count/total/fence/phase and raw MOS low24 timestamps around existing
paint/C3/query call boundaries, mode-flag clear/send/wait results and pass count.
Preserve exact query pointer/bytes/length and runtime MBASE at query entry. Add
asset ID/declared size/block size/remaining and sender-completed byte accounting
at the callback boundary. Pin offsets/layout and verify ring wrap/freeze decoding
before compiling a target candidate. Capture only source-proved side-effect-free
state; do not read UART receive/data/status registers speculatively.

MOS resolution is nominal8.33ms; modulo24 subtraction is adequate for the bounded
setup window. A query call lasting at least200ms would make a sender stall worth
investigating, but cannot locate an inter-byte gap. A shorter call cannot prove
correct wire delivery, prefix interpretation or parser state. A mode flag set
proves only a same-type reply, without request identity. Do not promote these
observations to a transport diagnosis or performance result.

## Evidence and admission needed before implementation/run selection

- Reconcile Extender's current generic carrier investigation first. Obtain full
  current EMOS/P4/native/startup/listener pins, supported API contracts, read-only
  state definitions and addresses. Old5735812 addresses/contracts are historical.
- Bind any candidate to the current task-owned loader and exact A native image;
  demonstrate source diff leaves asset sends/draw/timed paths unchanged. Review
  current rollback and storage/stack/resource fit before a fresh grant.
- Select a finite loading-only tranche with explicit invocation/time bounds and
  no timed renders. Stop on first failure, preserve evidence before LOAD, then
  restore the actual incoming native app/tail and perform normal handback.
  Success would be bounded observation, not proof the intermittent fault is fixed.
- If sender observations cannot separate the possibilities, request a separately
  reviewed receiver trace design from its owner: command-entry/parameter-wait/
  payload-remaining/C3 transitions and receive timestamps, without logging on
  the measured/shared transport. No shared firmware patch is selected here.

Remain within003-16; do not mark it resolved or restart the paired cohort from
this design. Hardware is the main target. The old Flexe loading issue is separate.
