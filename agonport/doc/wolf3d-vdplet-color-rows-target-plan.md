# Wolf3D direct-row finite target preparation

The source and host proof establishes exact output and a much smaller caller
workspace, but not actual runtime behavior or speed. This frozen G057-WLF-003
plan prepares a matched copied/direct target comparison and a new review
fixture while leaving every emulator stopped. Execution requires a later
explicit Golem grant.

Status: immutable execution and staging plan for TODO 8b
Frozen: 2026-10-30
Boundary: target/review preparation only; no launch or profile mutation

## Pinned cohort

| Item | Pin |
| --- | --- |
| rows-r1 firmware | `/home/smith/Agon/mystuff/agon-vdplet/build/vdpl-012/rows-r1/firmware.bin`, SHA-256 `8d980025f891484cf7e6cc5f2992cf517cb80e0123ff7de712ae8d7f2dc1c807` |
| rows-r1 ELF | adjacent `firmware.elf`, SHA-256 `1a7c44482d4ba8c5bfb49976c0bd664b9a9c2a635c7027b30954929ca567f814` |
| x86 backend | `/home/smith/Agon/mystuff/flexe-agon-emulator/build/fx072/maintained-r02/flexe-vdp-maintained.so`, SHA-256 `0866265bd6f3d73ad572f31dc1bb954f308ed9a5d857efa9414d37e1ade13374` |
| copied package | SHA-256 `57b635fc1807d9108e576cfff4c79c7f57ade48164fc5be97d75a3562e54b1be` |
| direct package | SHA-256 `c32381bc659b6e1fcc479eef22168a77eea22da310202da794234f172ccab670` |
| oracle frame | SHA-256 `6b569190c057996d4c50c1cc182c5b210a05a5e8c6fc7f9e60059d892363bf93` |
| oracle geometry | SHA-256 `2a15866957fa06d34f72067b2b1ff42325b3c3d0f02403059d43dc9a6812d820` |

The immutable ABI 1.6 SDK and contract pins remain those in
`wolf3d-vdplet-color-rows-plan.md`. Do not substitute an older backend, bypass
an architecture gate, or use the pending ARM64 build before Golem delivers its
qualified pin. The initial preparation targets the supplied x86 Oryx backend.

## Finite automated cohort

Each engine (`jit`, `interp`) runs in a fresh process under one central Oryx
lease. The runner will:

1. verify every file pin before starting the backend, discover capabilities,
   record INFO17 and heap/task resource values, select physical double-buffered
   320x240 RGB222, and capture a known visible baseline;
2. run the byte-identical copied package with its 92,160-byte workspace, then
   the primary direct package with its 11,552-byte workspace, using identical
   map, textures, CONFIG, mode, fences, and oracle;
3. for each arm prove hidden output before host C3, exact 76,800 decoded pixels
   after C3, and exact 1,792 DDA bytes read from the arm's workspace only after
   RUN completion;
4. exercise a finite identical failure set for both packages: render before
   CONFIG, short workspace, short map, short textures, recovery to an exact
   frame, invalid reconfigure preserving the prior valid state, and unsupported
   entry; verify no failed frame is presented;
5. unload, reject the stale handle, reload and unload again, verify an empty
   slot, and record final resources and backend failed/unhandled/unregistered/
   unmapped counters;
6. record that the production images expose no intentional forgotten-END
   entry. Runtime automatic forgotten-lease cleanup remains covered by the
   generic VDPL-012 qualifier rather than changing either accepted control;
7. perform six bounded alternating copied/direct rounds, five same-scene
   RENDER RUNs per arm per round, with load, CONFIG, decoded-frame capture, C3,
   and teardown outside every timed interval; DDA READ16 extraction occurs in
   the separate correctness arm rather than being repeated in timing; and
8. retain every first-failure receipt and shut down only the owned backend by
   its normal close path.

The reported timing is host foreground submit-to-requested-RUN-reply duration
and corresponding emulated VDP-cycle delta. It includes wire transport and
runtime dispatch/completion, is not isolated renderer time or native CCOUNT,
and makes no physical-speed claim. Report both raw sample arrays and summary
statistics; do not subtract wall time or add a profiling ABI.

## Prepared review boundary

After both automated engine receipts pass—and not before—a separate
`.emulator/vdplet-rows-review` profile may be staged under its own later grant.
It will upload the exact direct package and 11,552-byte workspace, show the
same recognizable module-only scene, wait for one key, unload, clear buffers
and callback state, restore the saved single-buffered MOS mode and cursor, and
return to the prompt. Its package will include both copied and direct source,
package hashes, the accepted reference image, and plain-language role text:
the direct module is under review, the copied module is the already accepted
control, and the host draws no scene pixels.

The original `.emulator/vdplet-review` profile, source package, and human
acceptance remain untouched. Preparation must not launch a GUI or ask the
Author for another terminal command or verifier. Staging and human review each
remain later centrally leased actions.

## Readiness and stop condition

Preparation may syntax-check scripts, verify local pins, build deterministic
review inputs, and emit a readiness manifest. It must not load the backend,
contact Oryx to mutate a profile, request a lease, or start an emulator. Return
the exact runner, packages, firmware/backend pins, expected duration, proposed
profile path, and remaining architecture/lease gates to Golem. Stop pending a
fresh execution grant.
