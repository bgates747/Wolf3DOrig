# FX-153 design review and bounded implementation disposition

WOLF-PERF-003-09 consumer review,2026-11-05. This is necessary diagnostic work
within Smith's authorized matched-benchmark implementation/debug task. Flexe
retains its component ownership; Wolf does not edit emulator/model source.

## Reviewed evidence

Verified FX-153/DESIGN.md SHA ef30e7fd2ec2b3a5e220942daa3748d7c629db8baec49c334dc52c263c6aae20
and design.json SHA db74167eb03630bd74befce5a4b19717692fe3c73701b1526b51ed583275eac9.
All five proposed source pins match the retained625d source export. Read the
actual Writer/Progress publication, bounded reader and existing tests in that
export. No tests or compiler were run by this review.

The proposed split is sound for the existing single writer: phase updates
modify only phase, phase CTS, completed sends and persistent CTS history;
batch updates publish the full record under the same SeqCst version. Closing
the entered publication before calling the original callback preserves useful
blocked-call observation. An unchanged-value batch still publishes a new tag,
and None/epoch transitions remain explicit. The reader's whole-record version
check preserves coherence while batch fields retain their declared earlier
snapshot. Separate VDP getters still have no receiver/global-time coherence.
Passing Snapshot by reference also avoids a redundant full TX-array parameter
copy; this remains a source property to verify in implementation.

No design change requested. The proposed phase atomic count28to8 is a source
count, not measured overhead, timing equivalence or repair. Keep the new
fx153-tx-v1 schema/owner_batch marker and distinct opt-in/reader so old cohorts
cannot be silently relabeled.

## Next selected component work

Request Flexe implement this exact design in a private export from the retained
625d source freeze, with production changes confined to src/uart_progress.rs.
Keep UART counter/capture paths, machine, serial calls, backend, firmware,
dependencies and unrelated fixes unchanged. Test hooks must compile out of the
release artifact; do not add release per-byte counters to measure the hooks.

Select one bounded serial compiler/ordinary host-qualification tranche, using
the canonical Pi compiler FIFO, normal80C/unavailable-sensor stop and512MiB RAM
floor. At most20minutes total; stop on the first unexpected failure, retain it
and return its disposition. Preserve any stricter component limits. Run the
design's actual store/coherence/blocked-callback/forwarding/accounting tests,
existing UART tests and strict versioned serializer/reader checks. Retain real
commands, output, counts, source hashes, telemetry and any unavailable result;
do not claim tests from a shadow implementation or repeat a passing suite
without a new change/failure justifying it.

Build at most one private release frontend for Oryx's x86_64 architecture ONLY
through an already-qualified toolchain route compatible with current canonical
compiler routing. Native Pi host tests do not qualify an ARM64 executable for
Oryx. If the required build route is unavailable, preserve completed source/
host checks and return the concrete toolchain blocker before selecting a new
machine/route. Do not execute a guest/emulator or silently build on Oryx under
a Pi compiler lease. Record actual compiler/target/flags and any differences
from625d; no performance equivalence is inferred.

Return exact frozen source transformation/diff, unchanged-source audit, actual
footprint assertions, host evidence, strict new reader and its hash, and the
private artifact hash/ELF dependency identity if built. No artifact exists or
is accepted merely because the design has been accepted.

No target cohort/profile adoption, shared deployment, firmware/hardware action,
rescue, public release or commit/push is selected by this disposition. Those
remain later concrete decisions after returned host/artifact evidence. Original
7e7d failures and625d zero-sample nonreproduction remain separate and unresolved.
