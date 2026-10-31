# Wolf3D production VDPlet contract — schema 1

This is the frozen application/module boundary for TODO 8e's first production
renderer. It replaces the bounded proof's static scene without changing the
accepted standalone renderer, which remains the default oracle and rollback
path. The generated numeric authorities are:

- `agonport/vdplet/production/wolf3d_production_contract.h`
- `src/asm/wolf3d/src/wolf3d_vdplet_contract.inc`

Both come from `agonport/vdplet/production/contract.py`; hand-maintained
parallel constants are forbidden. Wire schema 1 is versioned independently of
the module's release version.

## Runtime and entry contract

The module requires VDPlet ABI 1.3 with capability mask `0x0011` (ordinary
buffers plus copied pixels). Every requested RUN supplies the same exact
24-byte resource descriptor. CONFIG copies validated values into module state
and retains no caller pointer or lease.

| Entry | ID | Contract |
|---|---:|---|
| CONFIG | 0 | Validate/copy the descriptor and initialize an unready mirror at the generation seed. |
| APPLY_AND_RENDER | 1 | Validate the complete update buffer, apply it atomically, render, and publish one hidden RGB222 frame. |
| FIZZLE_BEGIN | 2 | Require a published frame, seed the original red-fizzle order, and retain no external pointer. |
| FIZZLE_STEP | 3 | Advance one of 60 fixed cumulative slices and publish it; the app controls cadence and Escape. |
| RESET | 4 | Clear config, mirror, pending publication, and fizzle state without touching caller-owned buffers. |
| SELFTEST | 5 | Optional deterministic diagnostics; no gameplay mutation. |

APPLY_AND_RENDER is the only ordinary frame producer. The application submits
at most one requested RUN at a time and presents C3 only after DONE. Fizzle
never races APPLY_AND_RENDER: Escape stops scheduling new steps, waits for the
one in-flight request, then resets or unloads through the normal ownership
path.

## Resource descriptor

All values are little-endian. Flags must be exactly copied-pixel bit 0 for
schema 1. Workspace, update, and tilemap IDs must be nonzero and pairwise
distinct. The three asset bases are deliberately pinned to the already loaded
application assets.

| Offset | Bytes | Meaning |
|---:|---:|---|
| 0 | 4 | Magic `W3PA`. |
| 4 | 1 | Schema version 1. |
| 5 | 1 | Descriptor bytes, exactly 24. |
| 6 | 2 | Flags, exactly `0x0001`. |
| 8 | 2 | Writable 92,160-byte workspace buffer. |
| 10 | 2 | Consolidated update-batch buffer. |
| 12 | 2 | Current 4,096-byte tilemap buffer. |
| 14 | 2 | Wall texture base, exactly `0x1000`. |
| 16 | 2 | Sprite texture base, exactly `0x2000`. |
| 18 | 2 | HUD chunk base, exactly `0x4000`. |
| 20 | 2 | Generation seed; `0xffff` is invalid. |
| 22 | 2 | Reserved zero. |

A level transition supplies a new descriptor/tilemap and generation seed,
then a complete snapshot. CONFIG invalidates the old mirror; the first batch
must therefore be full and its level record must name the configured tilemap.

## Update batch

The update buffer is exact-sized, consolidated, at most 6,912 bytes, and
contains at most 617 records. Its 16-byte header is:

| Offset | Bytes | Meaning |
|---:|---:|---|
| 0 | 4 | Magic `W3DU`. |
| 4 | 1 | Schema version 1. |
| 5 | 1 | Header bytes, exactly 16. |
| 6 | 2 | Flags; bit 0 means complete snapshot. |
| 8 | 2 | Exact total buffer bytes. |
| 10 | 2 | Record count. |
| 12 | 2 | Nonzero generation. |
| 14 | 2 | Reserved zero. |

Each record is `type:u8, payloadBytes:u8, payload...`. Unknown types, wrong
fixed payload sizes, trailing bytes, duplicate singleton/slot records, invalid
values, and out-of-range IDs reject the entire batch before any mirror byte is
changed.

| Type | Payload bytes | Payload |
|---|---:|---|
| LEVEL (1) | 6 | `tilemap:u16, doorCount:u8, staticCount:u16, zero:u8`. Full-only and first. |
| PLAYER (2) | 10 | Existing `x:i32, y:i32, angle:u16` pose. |
| DOOR (3) | 9 | `id:u8` plus the existing eight-byte door wire record. |
| ACTOR_SET (4) | 15 | Existing actor wire record: `id:u16, shape:i16, x:i32, y:i32, facing:u16, rotations:u8`. The base shape plus its maximum 2/8-way rotation offset must remain at or below 8191. |
| ACTOR_REMOVE (5) | 2 | `id:u16`; partial batches only. |
| STATIC (6) | 7 | `id:u16` plus the existing five-byte static wire record; shape -1 removes it. |
| HUD (7) | 12 | `health, ammo, keys, weapon, score:u32, level, face, lives, zero`. |
| VIEW_WEAPON (8) | 2 | `shape:i16`; -1 suppresses the overlay. |

A complete snapshot must contain exactly one LEVEL, PLAYER, HUD, and
VIEW_WEAPON record, every door `0..doorCount-1`, and every static
`0..staticCount-1`. Live actors are sparse ACTOR_SET records; absent slots are
cleared. ACTOR_REMOVE is unnecessary and forbidden in a full snapshot. The
largest legal snapshot—64 doors, actor slots 1..149, and 400 statics—is 6,891
bytes and 617 records.

## Generation and publication failure

Ordinary batches must be exactly the last applied generation plus one; zero,
skips, stale values, and wrap are rejected. Applying a valid batch records a
pending publication. The module commits `presentedGeneration` only after
copied-pixel publication succeeds.

If rendering or publication fails after application, the eZ80 retains all
dirty state and the exact consolidated batch. While publication is pending,
the module accepts only that same generation with the same full-buffer FNV-1a
fingerprint. It reapplies the idempotent records and retries rendering. An
altered same-generation batch and every newer generation are rejected. This
keeps retry possible without a second 5,360-byte mirror while preventing a
half-old/half-new world or silent loss of authoritative changes.

## Compact mirror and workspace

The validated mirror is 5,360 bytes on the host ABI and has a hard 5,500-byte
resident ceiling. It contains only render-facing player, door, actor, static,
HUD, view-weapon, generation, and retry state. Gameplay, collision, AI, item
ownership, and actor state machines remain exclusively eZ80-owned.

The first production arm retains the accepted copied-pixel workspace:

| Offset | Bytes | Use |
|---:|---:|---|
| 0 | 76,800 | Complete 320x240 RGB222 frame. |
| 76,800 | 1,024 | 256 signed wall heights. |
| 77,824 | 256 | Wall/door IDs. |
| 78,080 | 256 | Texture U coordinates. |
| 78,336 | 256 | Wall-side flags. |
| 78,592 | 8,800 | Sprite sorting/scaling arena. |
| 87,392 | 4,768 | Alignment and bounded headroom. |

Wall texture `n` is buffer `0x1000+n`; sprite shape `n` is `0x2000+n`; HUD
chunk `n` is `0x4000+n`. Assets are leased only for the bounded interval in
which they are sampled and are released before the requested RUN returns.

## Pure renderer extraction

`wolf3d_renderer.cpp` is the first production render core over this mirror. It
accepts a caller-owned 4,096-byte tilemap span, 92,160-byte workspace, and a
narrow acquire/release asset provider. It retains no span or lease. Wall
textures are discovered from the completed DDA metadata and grouped by ID, so
each distinct wall/door texture is leased once per frame rather than once per
column. Sprites are leased one at a time. The fixed 8,800-byte arena holds all
150 actor plus 400 static projection records and an in-place far-to-near heap
sort; scaled pixels are written directly to the RGB222 frame without a second
sprite bitmap.

The extracted scope currently includes the 320x200 play surround, centered
256x160 view, quarter-wave fixed-point projection, bounded DDA, exact
center-plane moving doors, perpendicular jamb selection, nearest-neighbor wall
columns, actor 2/8-way rotation selection, statics, sprite depth ordering,
RGBA2222 transparency, and strict wall occlusion. It retains no asset pointer
between calls. The final composition passes add the
161-pixel unoccluded first-person weapon, original 320x40 status bar, numbers,
damage/death face, keys, and HUD weapon icon. Repeated HUD chunks are grouped
so each distinct chunk is leased once per frame.

The durable host build renders three deterministic scenes through both the
new core and the accepted standalone `Wolf3dRenderer`. All 230,400 RGB222
frame bytes and 5,376 DDA bytes match exactly. Their SHA-256 values are
`d04684a952fe4e918774b7f433d16d2888bc27ec98f97573b630b6dcbdeafbd9`
and `fb7e03def15e8debd7eb31ddada6b43c123b3e0b1f3e021bb3857b3cc617a82a`.
The same suite covers unready/short resources, missing and short assets,
release failure across wall/weapon/HUD paths, invalid map-to-door references,
lease balance, and workspace guards. It also verifies all 41 gameplay HUD
chunks and payload sizes against the generated real-asset manifest. A
sanitizer-backed maximum scene projects all 149 legal actor slots and all 400
statics at once without truncation or arena overrun.

A pinned Xtensa freestanding object audit found 4,778 text bytes, 4,163
read-only table/string bytes, no BSS/data, and a largest source stack frame of
352 bytes. Its only undefined symbols are the already understood
`__divdi3`, `__udivdi3`, and `memset` helpers.

## Module wrapper and first admission

`wolf3d_module.cpp` is the real single-translation-unit ABI 1.3 wrapper. CONFIG
copies and validates the exact descriptor before replacing state.
APPLY_AND_RENDER requires that same descriptor, validates the pixel surface,
leases and atomically applies the consolidated update, leases the workspace
and tilemap, acquires at most one asset at a time, publishes one complete
hidden frame, and commits the presented generation only after publication and
cleanup succeed. RESET requires the same descriptor and clears module state;
INIT and FINI are idempotent. FIZZLE_BEGIN, FIZZLE_STEP, and SELFTEST remain
explicitly unsupported until their later tranches.

The host lifecycle suite covers CONFIG, full and partial APPLY_AND_RENDER,
RESET, FINI, malformed-batch rejection, pixel-publication failure, altered
same-generation refusal, exact retry, missing-asset recovery, balanced cleanup,
and the three-lease maximum. The first published 76,800-byte frame matches the
pure renderer and standalone oracle exactly; its SHA-256 is
`a20c0387435f480ff7b551896d4cc02c0539bac40a6af3753148252fb81fdaf6`.

The pinned SDK admits the linked package under the contract's limits. The
package is 14,008 bytes with 8,832 resident text bytes, 9,504 resident data
bytes, 29 relative relocations, no undefined symbols, and SHA-256
`badfb6e398cbebc8a1fe843578512c9631ad61551c66625c19053064f35bf734`.
The largest compiler-reported source frame is 704 bytes. The largest
conservative visible module-owned call-chain sum is 992 bytes against the
2,048-byte limit; target INFO17 remains the authority for runtime and
compiler-generated overhead. This is host and linked-package evidence, not
runtime-emulator, performance, full-game, or physical-hardware qualification.

The exact package subsequently passed its finite JIT runtime-emulator gate.
The full snapshot and exact retry produced all 76,800 oracle pixels, with frame
SHA-256 values
`a20c0387435f480ff7b551896d4cc02c0539bac40a6af3753148252fb81fdaf6`
and
`554dcfdb164c79058762cc0c0aa6394409c9df40412ab872341d2b8ba81f3e95`.
The exercised native failures were a missing HUD asset after update
application, an altered same-generation retry, the deliberately deferred
fizzle entry, and rendering after RESET. Restoring the asset and exact batch
published the second frame. UNLOAD, stale-handle rejection, reload, final
UNLOAD, and an empty slot all passed. INFO17 remained at 2,152 free bytes
before and after the path. The first requested APPLY_AND_RENDER reply measured
3,920,000 emulated VDP cycles and 0.015407 host seconds; this is not physical
frame time. Backend failure, unhandled, unregistered, and unmapped counters
were all zero. The ignored evidence receipt has SHA-256
`bee886ccd052ea335c9fc6b63ed0d1d400c4cba1e1835c7f98a96291891968f8`.
Full-game integration and physical qualification remain open.

## Error and ownership semantics

- Bad entry IDs return `VDPL_E_UNSUPPORTED`.
- Missing buffers return `VDPL_E_BUFFER`; short spans and malformed declared
  lengths return `VDPL_E_BOUNDS`.
- Bad schema, flags, generations, ordering, duplicates, coverage, IDs, or
  values return `VDPL_E_ARGUMENT`.
- ABI/capability, lease, pixel-service, and cleanup errors propagate their
  native VDPlet status.
- A rejected CONFIG preserves the last complete config/mirror. A rejected
  batch mutates nothing. A publication failure retains the pending exact-retry
  state described above.
- No module path retains a leased pointer across RUN or FINI.

`agonport/vdplet/production/build.py` regenerates nothing implicitly: it first
requires both generated consumers to match `contract.py`, then compiles and
runs the mirror, renderer, standalone-oracle, and module-wrapper regressions.
It builds the actual package, pins its hash and components, verifies admission,
ABI/capabilities, relocations, undefined symbols, stack receipts, and exact
module-to-oracle pixels. These are host and package-admission results, not
runtime-emulator, gameplay, or physical-hardware qualification.
