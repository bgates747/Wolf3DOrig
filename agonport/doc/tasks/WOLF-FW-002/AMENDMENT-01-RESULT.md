# WOLF-FW-002 amendment 01 — Amended release refresh complete

The current default is VDPlet `v0.1.2-alpha`, selection
`0.1.2-alpha-async-r1`, firmware SHA256
`dc43ecb8b1c324ffd1a032e6cc0c56d8c05dd33a355ce170c23adb35ffb533ab`
(1115568 bytes). The tag was replaced in place. The b004 image, original audit,
r01–r05 results and earlier profiles remain superseded historical evidence.
The amendment contract was pushed as `9c0c575` before inspection or changes.

All 13 downloaded assets match authenticated GitHub sizes/digests; all 12
SHA256SUMS entries match. Its checksum-list SHA256 is
`52438920e70480cd1c0f0c9543fbf2e0f7771ce937b92f422ef2f6ea394f79ba`.
The decompressed release ELF is
`576b69f3a0a4fbb676b2108b06437d1ae6d0b459fa7976c8508a4815e55f0a40`.
All 109 source-freeze inputs match tagged source
`60e5b4ebafa3e1c8bb740e45260d78cdb6125e30`. Eirene's exact RC3 ZIP/member
identity is unchanged and verified by the preparation checks.

The ordinary async worker is now enabled (ABI 1.7, capabilities 799). The
source retains the old ABI 0–6 host views; all 19 retained Wolf module images
still pass the limited synchronous ABI/capability/ELF/resource screen.
Wolf's synchronous modules and current preparation subset remain unchanged.
Private witnesses/count-return/quiet polling/PCM sink remain excluded. This
refresh does not implement or qualify an async Wolf consumer.

## Refreshed preparation and checks

- The verifier selects the replacement assets/cache and rejects old checksums.
  Packaging now also rejects stale firmware pins in a build receipt, including
  a stale receipt bearing the same release version.
- Four real application assemblies pass. The normal game, optimized profiling
  game and corrected finite client binaries reproduce their prior bytes;
  only release metadata/payload/profile bindings changed. The standalone
  disabled-profile control remains byte-identical as well.
- 37 preparation/profile checks plus 23 finite-client wire/storage/ownership
  checks pass (60 total). Actual compiler generation 725 was released after
  all owned children joined; peak recorded CPU temperature was 57.3°C.
- Current payloads are `tgt/wolf3d-standard-async-r1`,
  `tgt/wolf3d-optimized-profile-async-r1` and
  `tgt/wolf-finite-client-async-r1`. Each game includes all ten levels and its
  module/receipt. General deployment now selects the first payload.
- Fresh stopped profiles are under `tgt/profiles/normal-release-x86-async-r1`,
  `optimized-profile-release-x86-async-r1` and `finite-release-x86-async-r1`.
  They contain the exact replacement VDP BIN/ELF and Eirene RC3 BIN/map;
  startup loads without RUN. Old profiles were not overwritten.
- The Olimex owner's maintained desired selector has also moved to dc43ecb8
  with the same approved a25f EMOS. Our selector helper verifies that join.
  This is not an installed-state observation or a hardware grant.

[Compact evidence](AMENDMENT-01-EVIDENCE.json) includes actual commands,
source/assets/module hashes, payload/profile identities, unchanged application
hashes and cleanup. [Current commands](../../../../tools/README.md) select the
new paths. Original audit/qualification evidence is preserved separately.

No emulator, loader, game or firmware ran; no device, SD deployment, firmware
flash or bench reservation occurred. Runtime allocation/stack/controller and
new-image performance acceptance remain unproven. Existing human-start and
actual resource admission rules apply to any later selected execution.
The optimization goal remains paused; no resource lease is held.
