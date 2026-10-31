# Generation 31 production-client failure amendment

This amendment freezes the first production-client target failure and its
minimal eZ80-only correction. It does not revise the accepted bounded renderer,
shared runtime, wire contract, standalone default, or any physical result.

## Frozen failed candidate

- Oryx generation: 31
- lease: `07205039d9a742d4ab956a6eecaffcf8`
- client: 2,286 bytes, SHA-256
  `9657fdb2d63e8d3425b1db723bc3c62a6c0ea986109fe362e3810c82d11ed484`
- module: 7,952 bytes, SHA-256
  `57b635fc1807d9108e576cfff4c79c7f57ade48164fc5be97d75a3562e54b1be`
- runtime pins: firmware `b42ae55f...`, ELF `a10f7989...`, backend
  `108ec5b0...`
- preserved ignored evidence:
  `tgt/oryx-failure-gen31/`

The one authorized headless run did not display the expected scene within 180
seconds. No retry occurred. The owned frontend was stopped, a fresh inspection
showed Oryx empty at epoch `1793415366.1113734`, and the lease was released at
`2026-10-31T02:56:19.055742+00:00` before analysis.

## Actual result and wire path

`client.dat` is the exact 16-byte record:

```text
57 56 50 43 01 04 00 00 00 00 00 00 01 00 01 00
```

It decodes as result 1, incompatible status 4, no pending transaction, no
callback overlap, no handle, no native error, last token 1, result schema 1.
The reverse wire contains a valid IDENT/token-0 reply with capability value
`0x001F`, followed by a valid VALUE/token-1 INFO0 reply with identity `0x0100`.
The forward wire then contains no INFO1 request: the guest immediately clears
only its owned buffers, restores the saved mode and returns failure to MOS.
The MOS prompt is present and backend failure/unhandled/unregistered/unmapped
counters are zero. This was a clean client-side false incompatibility, not a
module execution, native cleanup failure, runtime patch need, or ownership
leak.

## Root cause and minimal correction

`w3d_vdplet_wait_reply` documented its returned value as a zero-extended u16
in HL, but wrote only L and H. HLU therefore retained an unrelated value. INFO0
then compared HL with `0x000100` using ADL-mode 24-bit `sbc hl,de`; a nonzero
HLU made the correct runtime identity appear incompatible.

The correction inserts `ld hl,0` before loading reply bytes 8 and 9. It changes
no packet, timeout, token, handle, cleanup, runtime or module behavior. A new
source regression requires that exact zero-extension before the ADL comparison.

## Corrected stopped candidate

- client: 2,290 bytes, SHA-256
  `ece412e25ea536dc15a93b2b4a2c45ce14df78231aede041bb81a8202dba14e5`
- client include SHA-256:
  `e857fd548466f33fc07e35efe9583e78a0245351156548711620c5e7bf7a179e`
- module: unchanged `57b635fc...`
- standalone rollback: unchanged 106,434-byte
  `2dee8b17ac83b8e7a43d7e1dcbd6962b1d24274ca489c145ef44a5fd1c0ea258`
- proportional host tests: 16 passed
- ADL audit: zero definite hazards; the only two review items remain the
  intentional 24-bit MOS clock reads
- Oryx profile: rebuilt, pin-verified, source-visible and stopped at
  `.emulator/vdplet-client`; no corrected target run has occurred

The prematurely queued corrected request `d28ebc1b0270` was canceled after the
offline-only coordination note was read. A new request may be created only
after this amendment and its frozen readiness evidence are sent to Golem.
