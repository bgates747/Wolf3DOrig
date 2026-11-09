# WOLF-FW-001 — Audit the pinned production firmware compatibility

Completed source/artifact audit: [RESULT.md](RESULT.md). Contract `52a1d8f`
was pushed before the audit. No build, emulator or physical operation occurred;
candidate migration/runtime qualification remains separate.

Smith's direct instruction, November 8, 2026: use VDPlet v0.1.2-alpha release
firmware on Alexe, Olimex and Console8, verifying its SHA256SUMS. Alexe and
Console8 use Eirene MOS 3.1.0_uart0_rc_3, specifically the release ZIP's
100879-byte mos-rc3.bin with SHA256
`d7a51147f3381cd68d56f3fbe4605434a897dfae1b049269afeba09ec2b7eb50`.
Olimex's scheduler maintains this VDPlet release and latest approved EMOS with
current Eirene enhancements. Required firmware exceptions must be identified
and justified in the scheduling request. These pins persist until Smith changes
them; older environment guidance does not override this instruction.

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

- [x] WOLF-FW-001-01 — Freeze/push this plan and register it in TODO.md.
- [x] WOLF-FW-001-02 — Retrieve exact release metadata/checksum manifests and
  selected firmware; independently verify VDP assets against SHA256SUMS and
  the Eirene ZIP member against Smith's exact filename, size and SHA256.
  Record source commit, asset identity, target variants and evidence paths.
- [x] WOLF-FW-001-03 — Inventory production/test candidate families and their
  exact source/artifact identities. Identify firmware ABI/capability, callback,
  package, transport, timing, memory-map and private/bespoke dependencies.
- [x] WOLF-FW-001-04 — Compare each family against the pinned release source
  and maintained Olimex owner's defaults. Classify source-compatible,
  requires preparation repin, justified inherent exception, incompatible or
  unresolved. Keep actual runtime qualification as a separate evidence column.
- [x] WOLF-FW-001-05 — Record each required exception, its exact reason and
  permitted scope; identify migration blockers and owner questions. Do not
  adopt an exception, silently substitute old firmware or revive a closed kit.
- [x] WOLF-FW-001-06 — Update current project firmware guidance/preparation
  status with the new defaults and audit findings, preserving historical pins.
  Publish a compatibility matrix, actionable disposition and checksum/source
  evidence. Commit/push results and report remaining unqualified boundaries.

## Completion and ownership

The audit is complete when release verification, inventory, compatibility and
exception dispositions are reviewable with exact evidence, including explicit
unknowns. A candidate need not be migrated or run to finish this audit; any
necessary source/build/runtime work must remain clearly identified. New future
dispatch must bind these defaults or an explicitly justified exception in its
normal scheduler request. No old experimental firmware becomes a default.

Wolf owns its clients/candidates and this report. VDPlet/Eirene/EMOS owners
remain authorities for their runtime/firmware and source contracts. Olimex
requires current owner-reconciled components, fresh actual checkout and stopped
handoff. Existing cleanup/restoration, SD-mounted and human-start constraints
remain. WOLF-GOAL-001 stays paused; no bench/emulator reservation or firmware
operation is selected here.
