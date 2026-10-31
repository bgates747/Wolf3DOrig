# Wolf3D bounded colour-row adaptation plan

Status: immutable implementation plan for TODO 8a / G057-WLF-002
Frozen: 2026-10-30
Execution boundary: source, host regression, and package evidence only

## Purpose and non-goals

Prepare a separate optional adaptation of the already accepted bounded Wolf3D
representative-scene VDPlet. The candidate will direct its final RGB222 stores
into borrowed hidden SBGR2222 row groups supplied by the generic ABI 1.6 colour
frame service. It must retain the accepted scene, DDA column geometry, sprite,
textures, fixed-point math, and standalone-firmware oracle.

This work does not replace or modify the accepted copied-pixel candidate, ask
for another human review, run a target emulator, touch a shared profile, flash
hardware, integrate the full game, redesign the renderer, publish artifacts,
or infer a speed improvement. Any target qualification is a later separately
granted task.

## Pinned inputs

| Input | SHA-256 |
| --- | --- |
| ABI 1.6 colour-row contract | `5172702f7ebc7dea77efb487d9ffafc99514981c7600ffc11d769835f44f267e` |
| Contract clarifications | `db2012b778701ee95cf71b2d06e7fb469fa386702631ea63de88f77a1973c5f1` |
| Immutable SDK `vdplet.h` | `92a6bbc403ecc51e165c103cfd16fd071f3d644ad52f83a4a7cb4fe088a5a2d6` |
| Immutable SDK `vdplet_protocol.h` | `a55dce6ca09a32da736e43416207a1e5c3d1bceea6c70c1229764696f622f5ef` |
| Immutable SDK `vdplet_services.h` | `00844d5220bf05d329c4f66f6fb3653d8bcca3f60eafc51c820820f1203f394f` |
| Accepted copied source | `9624187304c62af3436937283402f1ceaad2f83968d1914f97b6d80c027aeb59` |
| Accepted copied contract header | `f5bdef3e8324d4fb682330451309c2c8460c0595770f8f9315b1f1338e53d78c` |
| Generated trigonometry/projection tables | `6e3353cebd8d69849bbde39abd536018b1ee403f599ae45acc51fb8c64303e5d` |
| Accepted copied package | `57b635fc1807d9108e576cfff4c79c7f57ade48164fc5be97d75a3562e54b1be` |
| Standalone oracle frame | `6b569190c057996d4c50c1cc182c5b210a05a5e8c6fc7f9e60059d892363bf93` |
| Standalone oracle geometry | `2a15866957fa06d34f72067b2b1ff42325b3c3d0f02403059d43dc9a6812d820` |

The SDK root is
`/Agon/mystuff/agon-vdplet/build/vdpl-012/sdk`. The candidate requires ABI
minor 6 and capability mask 273 (`BUFFERS | PIXELS | COLOR_FRAME`). PIXELS is
retained as an advertised compatibility requirement even though the direct
entry must not call `pixels_write`.

## Frozen implementation shape

1. Add a separate `wolf3d_scene_rows.cpp`; do not edit
   `wolf3d_scene.cpp` or change its copied build and review controls.
2. Keep CONFIG bytes and entry IDs identical so the same fixture can drive
   both candidates.
3. Acquire the existing application-owned workspace, map, and texture buffers.
   BEGIN one physical 320x240 rectangle at (0,0), then request every row.
4. Validate every returned descriptor: active lease, requested rectangle and
   row, raw native format 64, non-null data, 4-byte alignment, sufficient row
   bytes, `x_bias`, `pixel_xor`, `color_mask`, and `preserve_mask`.
5. Store the 240 independent row-group pointers as `uintptr_t` values in the
   caller workspace. No row-contiguity or row-zero-plus-stride assumption is
   allowed. All cached pointers expire before END and never survive RUN.
6. Route the unchanged background, wall, and sprite math through a final-store
   accessor equivalent to
   `row[(x_bias + x) ^ pixel_xor] = (old & preserve_mask) |
   (rgb222 & color_mask)`.
7. END exactly once on every path after a successful BEGIN, including ROW or
   render failure. Do not request presentation or C3. Release ordinary buffer
   leases in reverse order while preserving the first failure status.

## Workspace contract

The direct target workspace is laid out as:

| Region | Target bytes |
| --- | ---: |
| 240 cached 32-bit row pointers | 960 |
| 256 signed wall heights | 1,024 |
| wall tile, texture-U, and side columns | 768 |
| reserved sprite arena retained from copied proof | 8,800 |
| **Minimum target workspace** | **11,552** |

The host executable uses native `uintptr_t`, so its pointer-table region is
1,920 bytes and its minimum is 12,512 bytes. The target build must contain a
compile-time assertion for 11,552 bytes. Neither layout contains a 76,800-byte
colour frame. The accepted copied control remains at 92,160 bytes.

## Finite host qualification

The warning-clean exact-source host runner will use deliberately independent,
noncontiguous row allocations and seeded native bytes. It must prove:

1. all 76,800 low-six-bit pixels equal the frozen standalone oracle;
2. all 1,792 DDA geometry bytes equal the frozen oracle;
3. every byte's pre-existing top two sync bits remain unchanged;
4. guard bytes and bytes outside the admitted row group remain unchanged; the
   full-width rectangle has zero group-padding bytes by contract;
5. BEGIN, all 240 ROW calls, and one END occur, with no copied-pixel write;
6. no row data is accessed before ROW, after END, or after RUN;
7. absent capability, old/truncated host table, and null callback return an ABI
   error without touching output;
8. BEGIN failure, failure at selected ROWs, END failure, and each ordinary
   buffer acquisition/release failure return the first applicable error and
   leave no frame transaction or ordinary lease active;
9. failed CONFIG preserves the previous complete configuration and FINI clears
   persistent state; and
10. the original copied host suite still passes with byte-identical pinned
    source and package.

The generic service already owns stale-token, cross-kind, duplicate-BEGIN,
pending-swap, and runtime auto-cleanup qualification. The consumer runner will
still assert its own balanced BEGIN/END and pointer lifetime; it will not
duplicate the runtime's complete generic matrix.

## Package and stack gates

Build the direct candidate with the immutable SDK, ABI minor 6, capabilities
273, 65,536-byte text, 16,384-byte resident-data, 2,048-byte declared stack,
and 131,072-byte package limits. Record package SHA-256 and bytes, resident
text/data, ELF sections, all relocations and undefined symbols, every `.su`
source frame, and the largest reachable source call-chain sum under the
renderer-owned call graph. `.su` is not target task-stack proof; a later target
grant must independently record runtime INFO high-water evidence.

The evidence must report measured deltas against the accepted copied package
and workspace. It must not predict performance from workspace or code size.

## Stop condition

Stop with the direct source, host evidence, package receipt, copied-control
rerun, and an explicit list of any remaining target-only gates. Do not stage or
request a target run merely because these checks pass. A concrete package,
workspace, and stack pin is required before any later target request.
