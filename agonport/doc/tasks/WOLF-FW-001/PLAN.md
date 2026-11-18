# WOLF-FW-001 — Audit the pinned production firmware compatibility

Completed source/artifact audit: [RESULT.md](RESULT.md). Contract `52a1d8f`
was pushed before the audit. No build, emulator or physical operation occurred;
candidate migration/runtime qualification remains separate.

Release authorities:

- https://github.com/bgates747/agon-vdplet/releases/tag/v0.1.2-alpha
- https://github.com/bgates747/eirene-mos/releases/tag/3.1.0_uart0_rc_3

## Sequence and scope

Commit and push this contract before performing the audit. Then immediately
audit current production and retained test candidates, including the normal
bespoke and VDPlet clients, optimized module arms, rotating/static fixtures,
full-game profiler, Fab adapters and hardware/emulator preparation paths.
Group historical closed cohorts rather than rewriting their evidence or
treating old tokens/readiness as current admission. Include paused candidates
as retained candidates without resuming their implementation or tests.

This is a release-artifact, source/interface and retained-evidence audit.
Download release inputs into an ignored task-local evidence directory, verify
checksums and pin metadata/source identity. File reads, hashes, archive inspection
and focused non-executing analysis are allowed. Do not imply a new physical
qualification from source compatibility or old measurements. Compilation,
emulation, deployment, resets and device access retain their existing resource
and task-specific permissions; this audit does not start those workloads.

## Immutable subtasks

## Completion and ownership

The audit is complete when release verification, inventory, compatibility and
exception dispositions are reviewable with exact evidence, including explicit
unknowns. A candidate need not be migrated or run to finish this audit; any
necessary source/build/runtime work must remain clearly identified. New future
dispatch must bind these defaults or an explicitly justified exception in its
normal scheduler request. No old experimental firmware becomes a default.

For all Olimex bench procedures, use the sole authoritative [bench guide](/Agon/mystuff/agon-extender/docs/operations/olimex-bench/README.md).
