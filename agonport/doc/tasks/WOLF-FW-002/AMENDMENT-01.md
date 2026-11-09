# WOLF-FW-002 amendment 01 — Refresh replaced release assets

Smith's existing pinned-version/default-maintenance direction applies to the
published replacement of the same v0.1.2-alpha tag. Coordinator mail
`2026-11-08_23-56-55_vdplet_vdpl044-async-release-updated-wolf3dorig` supplies
selection `0.1.2-alpha-async-r1`, source `60e5b4eb`, BIN 1115568 bytes,
SHA256 `dc43ecb8b1c324ffd1a032e6cc0c56d8c05dd33a355ce170c23adb35ffb533ab`.
Eirene/EMOS policy is unchanged. Freeze/push this amendment before inspection.

- [x] Download the actual amended release into a fresh local cache. Verify
  published asset digests/sizes, SHA256SUMS, source freeze and exact BIN/ELF.
  Preserve b004 assets and the completed r01–r05 results as superseded evidence.
- [x] Update current verifier/build/deployment defaults and instructions to
  the amended selection. Keep Wolf's existing synchronous modules/ABI support;
  enabling async in firmware does not select a consumer async rewrite.
- [x] Refresh future complete payloads and stopped profiles into fresh paths.
  Do not execute them or replace already preserved old profiles. Do not infer
  actual Olimex state from its desired selector; any stale owner selection is
  an explicit reconciliation result, with no device action.
- [x] Through the normal serial compiler FIFO, refresh affected build receipts
  and focused checks. Reuse unchanged source/binary controls where justified.
  Same 80°C/512 MiB/180-second child/900-second tranche bounds and owned cleanup.
- [x] Publish amended evidence/limits and commit/push. Notify coordinators of
  the superseded prior completion note. No goal resumption, consumer algorithm
  change, async adoption, emulator/bench run, flash or SD deployment is selected.

Completed: [result](AMENDMENT-01-RESULT.md), [evidence](AMENDMENT-01-EVIDENCE.json).
