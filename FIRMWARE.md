# Pinned firmware for Wolf testing and deployment

Smith's November 8, 2026 instruction applies until he changes it. Read this
before preparing any test, emulator profile, SD payload or scheduling request.

| Target | VDP | MOS |
| --- | --- | --- |
| Agon Lexe (executables may still be named `flexe`) | VDPlet v0.1.2-alpha release | Eirene MOS 3.1.0_uart0_rc_3 release ZIP's `mos-rc3.bin` |
| Console8 | Same VDPlet release | Same Eirene release member |
| Olimex | Same VDPlet release | Scheduler's latest approved integrated EMOS, resolved at admission |

The VDP release firmware is `vdp-vdplet-0.1.2-alpha.bin`, 1100304 bytes,
SHA256 `b004570b607b45bbd6e87a3c704b65b23d3221981db3aac6cf2578aa22d766e3`.
Verify the release's `SHA256SUMS` as well as this hash. Release source commit:
`b6c7c58331bf4cbbd54dbc4a1301c124e5963622`.

Eirene's exact `mos-rc3.bin` is 100879 bytes, SHA256
`d7a51147f3381cd68d56f3fbe4605434a897dfae1b049269afeba09ec2b7eb50`,
source commit `97311c437093e416342a6c836cf9914f2ced027d`.
Use the release ZIP member, not a locally rebuilt or padded substitute.

- [VDPlet release](https://github.com/bgates747/agon-vdplet/releases/tag/v0.1.2-alpha)
- [Eirene release](https://github.com/bgates747/eirene-mos/releases/tag/3.1.0_uart0_rc_3)
- [Artifact verification and compatibility audit](agonport/doc/tasks/WOLF-FW-001/RESULT.md)

For Olimex, the maintained selector is
`/Agon/mystuff/agon-extender/docs/olimex-firmware-standard.json` and its policy is
`/Agon/mystuff/agon-extender/docs/procedures/olimex-firmware.md`.
At this audit the approved EMOS is full 131072-byte ROM `a25f1612…`, source
`2c79c600…`, RFC25 profile. Its retained map hash is `11a296f0…`.
This is a selector observation, not a live installed-state check. Resolve the
actual current selector, installation provenance and fresh normal admission
with the scheduler. Eirene's standalone RC3 binary is not an Olimex EMOS image.

The release includes repaired UART RX recovery, pixels, text96, borrowed colour
rows and READ_BYTES. It does **not** enable the optional async worker, counted
return, overlap witness, quiet async polling or PCM sink. Ordinary synchronous
Wolf modules do not require those disabled options. SDK source inclusion does
not enable a firmware feature.

## Candidate preparation

The tracked `standalone` backend depends on bespoke Wolf firmware. It remains
historical source/default evidence; it is **not eligible for routine dispatch**
on the selected VDP release. Use an explicitly prepared `vdplet-direct` payload
with its matching module for routine release-based work. This instruction does
not silently promote an experimental renderer or authorize a new run.

Old Alexe/Fab profiles, regression runners and closed hardware kits retain their
original firmware pins for provenance. Their old readiness and example commands
do not satisfy the new defaults. See the audit's family dispositions before
reusing them. In particular, a source-modeled Fab userspace `.so` is not the
ESP32 release binary and cannot provide qualification of its UART RX repair.
The migrated general deployment bundle requires a verified complete VDPlet
payload, including its module. See [current preparation commands](tools/README.md)
and the [migration task](agonport/doc/tasks/WOLF-FW-002/PLAN.md). The ordinary
CLI build defaults to the maintained production VDPlet module; the tracked
standalone assembly selector remains historical source, not deployment choice.

For a necessary firmware exception, the normal scheduling request must state
the actual purpose, exact alternate image/source/hash, missing or changed API
or layout, target and finite authorized scope, and cleanup to current standards.
Examples are a bespoke-versus-VDPlet compatibility comparison or a specifically
selected Fab source-model visual check. Frozen old hashes alone are not a reason
for an exception. No exception or new workload is selected by this document.

Native timing in combined021 is module-owned WPN1 data, ordinary READ16 and
RUN100; it does not inherently require the old private `7593…` VDP image.
Replace that historical harness binding through a new preparation, rather than
requesting an unnecessary firmware exception.

## Custody and cleanup

Existing resource, test, deployment and human-start permissions remain.
Reuse verified installed standard firmware; no routine unchanged-device backup,
readback or reflash. A nonstandard test restores affected components to the
**current standard**, with appropriate verification and normal handback, rather
than automatically restoring obsolete incoming firmware. Old kits that hardcode
the latter require a new freeze. P4, startup/listener, bootloader/partitions and
unrelated storage are not selected for replacement. Leave the SD card mounted.

The optimization goal stays paused. Static compatibility and verified release
bytes are not a new hardware/emulator pass or production renderer adoption.
