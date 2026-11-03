# Wolf3D production VDPlet contract — schema 2

This is the frozen application/module boundary for TODO 8e's first production
renderer. It replaces the bounded proof's static scene without changing the
accepted standalone renderer, which remains the default oracle and rollback
path. The generated numeric authorities are:

- `agonport/vdplet/production/wolf3d_production_contract.h`
- `src/asm/wolf3d/src/wolf3d_vdplet_contract.inc`

Both come from `agonport/vdplet/production/contract.py`; hand-maintained
parallel constants are forbidden. Wire schema 2 is versioned independently of
the module's release version.

## Runtime and entry contract

The production direct-row module requires VDPlet ABI 1.6 with capability mask
`0x0101` (ordinary buffers plus scoped native colour rows). The same package
retains a copied-pixel flag as its host-qualified fallback/oracle. Every
requested RUN supplies the same exact
24-byte resource descriptor. CONFIG copies validated values into module state
and retains no caller pointer or lease.

| Entry | ID | Contract |
|---|---:|---|
| CONFIG | 0 | Validate/copy the descriptor and initialize an unready mirror at the generation seed. |
| APPLY_AND_RENDER | 1 | Validate the complete update buffer, apply it atomically, render, and publish one hidden RGB222 frame. |
| FIZZLE_BEGIN | 2 | Require a published frame, seed the original red-fizzle order, and retain no external pointer. |
| FIZZLE_STEP | 3 | Advance one of 60 fixed cumulative slices on the hidden surface; the app controls C3 cadence and Escape, then requests one final unpresented step to synchronize the other physical surface. |
| RESET | 4 | Clear config, mirror, pending publication, and fizzle state without touching caller-owned buffers. |
| SELFTEST | 5 | Optional deterministic diagnostics; no gameplay mutation. |

APPLY_AND_RENDER is the only ordinary frame producer. The application submits
at most one requested RUN at a time and presents C3 only after DONE. Fizzle
never races APPLY_AND_RENDER. `FIZZLE_BEGIN` seeds an independent exact 17-bit
LFSR cursor for each physical surface. Sixty successful `FIZZLE_STEP` calls
are each followed by C3; the sixty-first successful step is deliberately not
presented and brings the other surface to the same all-red viewport. Escape
stops scheduling new steps after the current requested RUN completes, then
resets or unloads through the normal ownership path.

## Resource descriptor

All values are little-endian. Flags must be exactly one of copied-pixel bit 0
or direct-row bit 1 for schema 2; combining them is invalid. Workspace,
update, and tilemap IDs must be nonzero and pairwise
distinct. The three asset bases are deliberately pinned to the already loaded
application assets.

| Offset | Bytes | Meaning |
|---:|---:|---|
| 0 | 4 | Magic `W3PA`. |
| 4 | 1 | Schema version 2. |
| 5 | 1 | Descriptor bytes, exactly 24. |
| 6 | 2 | Flags, exactly copied `0x0001` or direct rows `0x0002`. |
| 8 | 2 | Writable workspace: 92,160 copied bytes or 11,552 direct-row bytes. |
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

The update buffer is exact-sized, consolidated, at most 7,168 bytes, and
contains at most 618 records. Its 16-byte header is:

| Offset | Bytes | Meaning |
|---:|---:|---|
| 0 | 4 | Magic `W3DU`. |
| 4 | 1 | Schema version 2. |
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
| STATIC (6) | 7 | `id:u16` plus the existing five-byte static wire record; shape -1 removes it. A partial batch may append non-removal records contiguously from the mirror's current `staticCount`, supporting actor item drops without a full snapshot. |
| HUD (7) | 12 | `health, ammo, keys, weapon, score:u32, level, face, lives, paletteShift`; face is ordinary 0..2 or `GOTGATLINGPIC` sentinel 3; palette shift is zero, red 1..6, or white `0x81..0x83`. |
| VIEW_WEAPON (8) | 2 | `shape:i16`; -1 suppresses the overlay. |
| PUSHWALL (9) | 89 | Complete live pushwall plus up to sixteen completed origin/current/texture overlays; required once in every full snapshot and whenever dirty. |

A complete snapshot must contain exactly one LEVEL, PLAYER, HUD,
VIEW_WEAPON, and PUSHWALL record, every door `0..doorCount-1`, and every static
`0..staticCount-1`. Live actors are sparse ACTOR_SET records; absent slots are
cleared. ACTOR_REMOVE is unnecessary and forbidden in a full snapshot. The
largest legal snapshot—64 doors, actor slots 1..149, 400 statics, and the
pushwall record—is 6,982 bytes and 618 records.

## Generation and publication failure

Ordinary batches must be exactly the last applied generation plus one; zero,
skips, stale values, and wrap are rejected. Applying a valid batch records a
pending publication. The module commits `presentedGeneration` only after
copied-pixel publication succeeds.

On first submission, the eZ80 consumes only the dirty snapshot represented by
the frozen consolidated batch. Simulation may then accumulate fresh dirt while
that requested RUN is in flight. If rendering or publication fails after
application, the exact batch and generation remain immutable and are retried;
old flags are never restored over newer simulation state, and retry submission
does not clear dirty state a second time. While publication is pending, the
module accepts only that same generation with the same full-buffer FNV-1a
fingerprint. It reapplies the idempotent records and retries rendering. An
altered same-generation batch and every newer generation are rejected. This
keeps retry possible without a second 5,448-byte mirror while preventing a
half-old/half-new world or silent loss of authoritative changes.

## eZ80 serializer

`wolf3d_vdplet_batch.inc` constructs the exact descriptor and serializes the
game's authoritative player, door, actor, static, HUD, and view-weapon state.
It shares the standalone actor-wire conversion routine rather than maintaining
a second shape/facing implementation. Full snapshots scan all live actor slots
and every active door/static. Dirty batches capture the existing dirty arrays
before serialization, then clear matching captured values only after RUN has
been armed and emitted.

A prepared batch owns its candidate generation and remains byte-for-byte frozen
until accepted. Failure releases only RUN ownership; the next prepare returns
the same buffer. Success commits the candidate generation and releases staging
for whatever fresh dirt accumulated during the flight. Generation wrap and
empty incremental batches are refused.

The finite full-MOS regression under `src/asm/wolf3d_vdplet_batch` executes the
production serializer on the eZ80. Its E1L1 full batch is 1,742 bytes and 168
records; its failed-RUN retry is byte-identical, SHA-256
`cdf0b7e2b79ed342d15f049182e609d19aa3cb227bbd4c78b1d653b2cd77a0cf`.
Changes injected while that batch owned RUN survive the retry and form one
70-byte generation-2 delta with PLAYER, DOOR, ACTOR_REMOVE, STATIC, HUD, and
VIEW_WEAPON records, SHA-256
`e42c1e35a41d18b4a26a9ab84fec6eeda3aa84c4af5a45b47623ad28e3276401`.

## Compact mirror and workspace

The validated mirror is 5,448 bytes on the host ABI and has a hard 5,500-byte
resident ceiling. It contains only render-facing player, door, actor, static,
HUD, view-weapon, generation, and retry state. Gameplay, collision, AI, item
ownership, and actor state machines remain exclusively eZ80-owned.

The copied-pixel fallback/oracle retains this workspace:

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

The production direct-row workspace is 11,552 bytes. Its first 960 bytes hold
240 temporary 32-bit native row pointers, followed by the same 1,024-byte wall
heights, three 256-byte DDA arrays, and 8,800-byte sprite arena. Every pointer
is zeroed before `COLOR_FRAME_END` and buffer release. The compositor writes
straight to the acquired hidden surface; no 320x240 intermediate exists.

## Pure renderer extraction

`wolf3d_renderer.cpp` is the production render core over this mirror. It
accepts a caller-owned 4,096-byte tilemap span, either production direct-row
scratch or the 92,160-byte copied workspace, and a narrow acquire/release asset
provider. It retains no span or lease. Wall
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
damage/death/chaingun-pickup face, transient palette shift, keys, and HUD
weapon icon. Repeated HUD chunks are grouped
so each distinct chunk is leased once per frame.

The durable host build renders six deterministic scenes through both the new
core and the accepted standalone `Wolf3dRenderer`. All 460,800 RGB222 frame
bytes and 10,752 DDA bytes match exactly. Their SHA-256 values are
`9d939640655e6317e37d85b9a446ad7984692cd480fea1efc3a8dab47a48f487`
and `4beb6013595a467ec0a5f659761a1164bdebccb2e1d83dbed7908e10dec22277`.
The same suite covers unready/short resources, missing and short assets,
release failure across wall/weapon/HUD paths, invalid map-to-door references,
lease balance, and workspace guards. It also verifies all 42 gameplay HUD
chunks and payload sizes against the generated real-asset manifest. A
sanitizer-backed maximum scene projects all 149 legal actor slots and all 400
statics at once without truncation or arena overrun.

## Module wrapper and first admission

`wolf3d_module.cpp` is the real single-translation-unit ABI 1.6 wrapper. CONFIG
copies and validates the exact descriptor before replacing state.
APPLY_AND_RENDER requires that same descriptor, validates the pixel surface,
leases and atomically applies the consolidated update, leases the workspace
and tilemap, acquires at most one asset at a time, writes one complete hidden
frame, and commits the presented generation only after publication and cleanup
succeed. RESET requires the same descriptor and clears module state; INIT and
FINI are idempotent. FIZZLE_BEGIN and FIZZLE_STEP implement the app-paced
original red transition. SELFTEST remains optional and unsupported.

The host lifecycle suite covers CONFIG, full and partial APPLY_AND_RENDER,
RESET, FINI, malformed-batch rejection, pixel-publication failure, altered
same-generation refusal, exact retry, missing-asset recovery, balanced cleanup,
dynamic dropped-item static growth, direct/copied equivalence, scoped-row and
mid-row failure cleanup, fizzle exact retry, and the three-lease maximum. The first
published 76,800-byte frame matches the
pure renderer and standalone oracle exactly; its SHA-256 is
`a20c0387435f480ff7b551896d4cc02c0539bac40a6af3753148252fb81fdaf6`.

The pinned SDK admits release 1.2.0 under the contract's limits. The package
is 18,636 bytes with 13,144 resident text bytes, 9,720 resident data bytes, 46
relative relocations, no undefined symbols, and SHA-256
`266f809ff76e56733251da202e5c4747cd9c12d247d799d486471a262c0404b7`.
The largest compiler-reported source frame is 736 bytes. The largest
conservative visible module-owned call-chain sum is 1,104 bytes against the
2,048-byte limit; target INFO17 remains the authority for runtime and
compiler-generated overhead. This is host and linked-package evidence, not
runtime-emulator, performance, full-game, or physical-hardware qualification.

The exact package subsequently passed its finite JIT runtime-emulator gate on
Oryx generation 161.
The full snapshot and exact retry produced all 76,800 oracle pixels, with frame
SHA-256 values
`a20c0387435f480ff7b551896d4cc02c0539bac40a6af3753148252fb81fdaf6`
and
`43dd54619cca5051bdf85a0bbde5907a2b4a4678927177d2d331510861a84b75`.
After synchronizing both source surfaces, the gate compared the original
17-bit LFSR order at slices 1, 15, 30, 45, and 60 across the whole frame,
proved the first slice remained hidden before C3, and verified the final
unpresented surface-sync step. Overlapping BEGIN returned BUSY and a step after
completion returned INIT. Missing-asset retry, altered-generation refusal,
RESET, UNLOAD, stale-handle rejection, reload, final UNLOAD, and an empty slot
also passed. INFO17 remained at 2,136 free bytes. The first render reply used
10,418,591 modeled VDP cycles; all fizzle replies used 314,014,262 cycles.
Backend failure, unhandled, unregistered, and unmapped counters were zero.
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
