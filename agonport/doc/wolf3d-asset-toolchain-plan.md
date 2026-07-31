# Wolf3D asset conversion toolchain: research notes + plan

Status: **Stages A-D implemented and validated against real shareware data
(2026-07-31).** Originally written as a plan-only research doc; the Author
reviewed it, answered the open questions below, and authorized
implementation ("you are free to code unless you have outstanding
questions"). See "Implementation status" near the end for what's built,
what's tested, and what's still open (Stage E viewer).

## Goal

Convert real game art (initially decoded Wolf3D shareware `VSWAP.WL1`
textures/sprites; later, arbitrary hand-drawn PNGs for custom content) into
RGBA2222 Agon VDP bitmap buffers, at the exact buffer IDs the VDP renderer
already expects (`agon-vdp-wolf3d`'s `Wolf3dWallBufferId()`/
`Wolf3dSpriteBufferId()` formulas), packaged so the eZ80 side can load them
efficiently, with a visual review step before anything ships.

## Buffer-id contract (already settled and implemented, drives everything below)

From `agonport/doc/handoff_ez80_ai_raycaster.md` (`VDP_AGENT_UPDATE` round):

```
wallBufferId(textureId)  = 0x1000 + textureId   // textureId 1-127 -> 0x1001-0x107F
spriteBufferId(shapenum) = 0x2000 + shapenum    // shapenum 0-8191 -> 0x2000-0x3FFF
```

Format is RGBA2222 (format code `1`) exclusively, end to end -- already the
project-wide mandate, no exceptions.

## Reuse inventory: what already exists in `agon-utils` (don't reinvent)

All under `/home/smith/Agon/mystuff/agon-utils`:

1. **`agonutils` Python extension module** (`src/agonutils.c`/`images.c`,
   built as `agonutils*.so`, importable from that repo's own `.venv`):
   - `convert_to_palette(src_file, tgt_file, palette_file, method, transparent_color=None)`
     -- reduces a PNG to a given palette. `method` (case-insensitive) is one
     of `RGB` (nearest-color, no dithering), `HSV` (nearest in HSV space),
     `atkinson`, `bayer`, `floyd` (Floyd-Steinberg dithering). Verified by
     reading `_convert_to_palette()` in `src/images.c` directly.
   - `img_to_rgba2(src_file, tgt_file, palette_file, method, transparent_color=None)`
     -- same conversion, but writes packed on-disk RGBA2222 bytes (the
     `.rgba2` payload format) instead of a palettized PNG.
   - `rgba2_to_img` / `rgba8_to_img` -- reverse direction, for spot-checking.
   - **Author's stated preference (2026-07-31): default to `"RGB"` (plain
     nearest-color, no dithering) rather than `"HSV"` or `"floyd"` --
     "let's not dither for now" / "rgb method works better than hsv
     typically." Treat this as the working default, but keep the method
     trivially swappable via a CLI flag so the Author can A/B compare
     visually in the viewer app (Stage E below) -- final call is by eye,
     not by this doc.
2. **`Agon64.gpl`** (`examples/slideshow/palettes/Agon64.gpl`): the canonical
   64-color GIMP palette file matching Agon mode 136's RGB222 physical
   palette (channel steps 0/85/170/255). This is the palette file to hand to
   both functions above for all Wolf3D assets.
3. **`.agnb` RIFF container format** (`examples/agnb/docs/`
   `agon-buffer-file-format-specification.md`): a RIFF container
   (`RIFF...AGNB`, one `VERS` chunk, then one or more `LIST BUFR` records
   each holding exactly `BHDR`(explicit u16 buffer ID) + `IMAG`(width,
   height, format byte) + `DATA`(raw pixel bytes)). Explicit buffer IDs only
   -- readers never allocate/remap them, which is exactly what our fixed
   formula needs. Full spec already written and stable (draft 0.1).
4. **`api/agnb_api.inc`**: the canonical, general-purpose eZ80 ADL assembly
   loader for `.agnb` files. Public entry points `agnb_load_images` (DE =
   filename pointer) and `agnb_load_images_with_callback`. This already
   implements the entire read/validate/clear-buffer/stream-upload/
   create-bitmap sequence from the spec, including error codes
   (`agnb_error_*`) for every validation failure. **We do not need to write
   a new eZ80 loader** -- the eZ80 app just needs to link this file (plus
   its documented `agnb_dependencies.inc`) and call `agnb_load_images` with
   the path to our packed file. This is the "sample loaders in assembly"
   the Author referred to, and it's already a complete, reusable
   implementation, not a sketch.
5. **`docs/agnb-loader-agon-api-precis.md`**: cross-references the loader
   against official MOS/VDP docs (`mos_fopen`/`mos_fread` streaming pattern,
   `RST.LIL 18h` bulk-write semantics, buffer/bitmap VDU command shapes).
   Useful background if the eZ80 side needs to adapt anything, but no
   changes needed for our use case.
6. **Packer pattern**: `examples/agnb/images/container/scripts/do_assembly.py`
   builds a conforming `.agnb` file from a manifest + individual `.rgba2`
   files (`make_chunk`/`make_buffer_record`/`build_container` helpers do the
   RIFF bookkeeping: sizes, 4-byte alignment/padding, chunk nesting). It also
   generates an eZ80 `images.inc` with named `equ` buffer-id constants and
   lookup tables -- **we don't need that part**, since our buffer IDs are
   formula-derived from `textureId`/`shapenum`, not named per-asset like the
   demo's arbitrary `256 + index` scheme.
7. **Manifest pattern**: `examples/agnb/images/shared/scripts/image_manifest.py`
   -- a line-oriented JSONL manifest (`images.jsonl`), one entry per image:
   `include`, `source`, `name`, `bufferId`, `width`, `height`, `format`,
   `png`, `rgba2`, `dataSize`, with `validate_entries()` enforcing
   uniqueness of names/bufferIds/filenames, `format == 1`, and
   `dataSize == width*height`. Directly reusable schema; only the
   `bufferId` computation changes (formula instead of arbitrary index).
8. **`prepare_images.py`** (same `shared/scripts/` dir): the PNG-ingestion +
   palette-conversion + manifest-writing driver for the demo (crops/scales
   arbitrary photos to 320x240, then calls `convert_to_palette` then
   `img_to_rgba2`). Not directly reusable as-is -- our wall tiles are fixed
   64x64 and sprites keep native size, no crop/scale step -- but it's the
   right shape to model our own driver script on.
9. **Visual review app**: `examples/agnb/images/container/scripts/view_agnb.py`
   -- a Tkinter app that parses a `.agnb` file directly (own independent
   RIFF parser, doesn't trust the packer) plus its shared manifest, and lets
   you page through every image record, zoom (1x-32x), and inspect
   individual pixel values. This is the "tkinter app... to review converted
   assets for visual correctness" the Author mentioned. Reusable near-
   verbatim if our manifest matches its expected schema; otherwise a small
   fork with `CONTAINER_DIR`/`SHARED_PROCESSED_DIR`-equivalent constants
   repointed at our own paths.

## Reuse inventory: real Wolf3D art decoding (separate sibling project)

`/home/smith/Agon/mystuff/Wolf3dOrig/src/toolchain/formats/vswap.py`
(part of the **already-complete, separate** WL1 map-authoring toolchain
project -- own venv/tests, not to be modified in place for this task) already
has working, verified-correct VSWAP decoding:

- `read_vswap(data) -> VSwapFile` -- parses `VSWAP.WL1`'s chunk table
  (`numchunks`/`spritestart`/`soundstart` + offset/length tables).
- `wall_tile_to_chunks(tile_value) -> (horiz_chunk, vert_chunk)` -- maps a
  wall tile value (1-63 in the original engine) to its two VSWAP chunk
  indices, per `WL_MAIN.C SetupWalls()`: `horizwall[i]=(i-1)*2`,
  `vertwall[i]=(i-1)*2+1`.
- `chunk_to_image(chunk) -> PIL.Image` -- decodes a raw 64x64 column-major
  8bpp chunk to an RGB image using the hardcoded Wolf4SDL palette.
- `sprite_chunk_to_image(chunk) -> PIL.Image` -- decodes the `t_compshape`
  column/post sprite format to an RGBA image with a real transparent
  background (already handles the signed-pixelbase gotcha correctly, per
  that project's own memory notes).
- Already proven at scale: that project's `extract_sprite_sheet()`
  visually-verified whole-VSWAP-range sprite decoding, and its wall/door
  texture write-back round-trips byte-identically against real shareware
  data (both per that project's own status notes).

This is the best available *real, already-verified* source of Wolf3D art to
feed the new pipeline -- far preferable to starting from placeholder art or
re-deriving VSWAP decoding from scratch.

**Important nuance to resolve before building Stage A (see open questions):**
`wall_tile_to_chunks` returns a *pair* of chunks (horizontal-facing and
vertical-facing texture variants) per wall tile value, but our VDP-side
buffer-id formula assumes exactly *one* texture buffer per `textureId`. In
stock id Software content these two chunks are conventionally
pixel-identical, but this needs to be verified against the real shareware
data before collapsing them to one buffer per ID.

## Proposed pipeline (new code, not yet written)

**Stage A -- Extract real Wolf3D art as individual PNGs, one file per
texture ID / shapenum.** New script, built on top of `vswap.py`'s
`read_vswap`/`chunk_to_image`/`sprite_chunk_to_image`: iterate every wall
tile ID and every sprite shapenum actually present in a chosen `VSWAP.WL1`,
save one PNG per ID (transparent background for sprites).

**Stage B -- Palette-reduce + pack to RGBA2222.** New script, modeled on
`prepare_images.py` but simpler (no crop/scale needed -- wall tiles are
fixed 64x64, sprites keep native size): for each source PNG, call
`au.convert_to_palette(src, tmp, Agon64.gpl, "RGB", transparent_color=...)`
then `au.img_to_rgba2(...)` to produce the final `.rgba2` payload. Default
method `"RGB"` per the Author's stated preference above; keep `"floyd"`/
`"hsv"` as an easy override for visual A/B testing.

**Stage C -- Manifest.** Reuse `image_manifest.py`'s JSONL schema and
validation logic (copy/adapt, not cross-repo import -- see open question 5),
computing `bufferId` via the `Wolf3dWallBufferId()`/`Wolf3dSpriteBufferId()`
formulas instead of an arbitrary index. **Confirmed (2026-07-31):** add a
`kind` field (`wall`/`sprite`) to make later filtering/viewing easier.

**Stage D -- Pack.** Reuse `do_assembly.py`'s RIFF-writing helpers
(`make_chunk`/`make_buffer_record`/`build_container`) to build one packed
`.agnb` file from the manifest. Skip its `images.inc`-generation step
entirely -- unnecessary, since our IDs are formula-derived and need no named
`equ` constants.

**Stage E -- Visual QA.** Adapt `view_agnb.py` (repoint its path constants)
to page through every converted wall/sprite and eyeball it before shipping,
per the Author's explicit request for a review step.

**Stage F -- eZ80 loading (when that side is ready).** No new loader code
needed at all -- `agnb_api.inc`'s `agnb_load_images` already implements the
full read/validate/upload/bitmap-create sequence against our exact explicit
buffer IDs. The eZ80 app links `agnb_api.inc` (+ `agnb_dependencies.inc`) and
calls it once at level load with our packed file's path.

## Temporary carve-out location (outside the eZ80 asm source tree)

**`agonport/tools/wolf3d_assets/`** -- new subdirectory, sibling to the
already-established `agonport/tools/gen_dda_fixture.py` and
`setup_emulator.py` (existing precedent for "lightweight Python tooling
lives here, not under `src/asm/`, where the eZ80 agent is actively working").
All of Stage A-E's new scripts would live here. Output artifacts (converted
PNGs/`.rgba2`/manifest/`.agnb`) would land under `agonport/assets/generated/`
alongside the existing `dda_smoke_test_map.bin`, matching the generated-asset
convention already in use.

This avoids touching `agon-utils` itself (an external/shared tool -- read
from, don't fork in place), avoids `agonport/src/asm/` (the eZ80 agent's
active work area), and avoids modifying the separate, already-complete
`Wolf3dOrig/src/toolchain` map-authoring project (reuse its `vswap.py`
functions by import or by vendoring the specific needed functions -- see
open question 5 -- rather than expanding that project's own scope).

## Decisions (Author, 2026-07-31)

1. **Horiz/vert wall chunk duplication:** keep it simple, pick one and run
   with it, revisit if it doesn't look right. Implemented: Stage A exports
   only the horizontal-facing chunk of each wall/door pair.
2. **Sprite frame scope:** "we need to build the animation system from the
   jump so that we don't corner ourselves later." Implemented: Stage A
   exports every non-empty VSWAP sprite chunk unconditionally (not just one
   representative frame per creature type -- see "Sprite animation
   coverage" below for how per-level scoping still covers full per-kind
   animation).
3. **Source art scope:** priority is porting the shareware version only;
   custom/hand-drawn PNG ingestion is deferred.
4. **Container granularity:** granular -- one `.agnb` for tiles, one for
   sprites, split per level (episode split deferred until non-shareware
   data is in scope, since shareware only has episode 1). Implemented:
   Stage C scopes each of the real 10 levels' actual wall/door/sprite usage;
   Stage D packs `tiles.agnb` + `sprites.agnb` per level.
5. **Code provenance:** fork/vendor, don't cross-import. Implemented: all of
   `formats/{palette,vswap,mapfile,spritenames}.py` are vendored copies (see
   each file's "Forked 2026-07-31" header) with agonport-specific additions
   layered on top (door-texture helpers in `vswap.py`, the new
   `sprite_kinds.py` module); `agnb/{manifest,container}.py` are
   vendored/adapted from `agon-utils`'s equivalents, not imported.
6. **Palette method:** opaque walls and doors default to `floyd`;
   sprites default to nearest-colour `rgb` with no dithering. This split was
   selected by full-scene review: dithering retains wall texture detail, while
   RGB gives actors and statics cleaner silhouettes. `--method` still
   overrides both groups for A/B tests; `--wall-method` and `--sprite-method`
   can adjust them independently. HUD assets remain nearest-colour RGB.

## Door textures (grounded 2026-07-31, not covered by the original plan)

Unlike ordinary walls, a door's rendered texture is **not** its plane0 tile
value -- it depends on lock type. Grounded directly against
`orig/src/WOLFSRC/WL_DRAW.C` (read-only reference, names preserved per this
project's usual policy, not copied verbatim):

```c
#define DOORWALL (PMSpriteStart-8)
switch (doorobjlist[doornum].lock) {
    case dr_normal:                          doorpage = DOORWALL;   break;
    case dr_lock1..dr_lock4:                 doorpage = DOORWALL+6; break;
    case dr_elevator:                        doorpage = DOORWALL+4; break;
}
```

Only **4 distinct door textures** exist in the whole game -- normal, jamb/
frame (always shown for the door's side, any lock type), elevator, and
locked (all 4 lock colors render identically). `formats/vswap.py`'s
`door_kind_to_chunks()` implements this. Since door textures don't fit the
ordinary `wall_tile_to_chunks()` numbering (they live in the last 8 wall/
door chunks, disjoint from ordinary wall ids 1-49 in the real shareware
file), this project assigns them fixed `textureId`s in the unused 100+
range, comfortably clear of every real shareware wall id:

| textureId | door kind |
|-----------|-----------|
| 121 | normal |
| 122 | jamb/frame |
| 123 | elevator |
| 124 | locked (any of lock1-4) |

**eZ80-side note (not yet communicated to that agent):** whoever authors
`set_door()` calls needs this fixed table to pick the right `textureId` from
a door's lock type (`(tile - 90) // 2`: 0=normal, 1-4=locked, 5=elevator).

## Sprite animation coverage strategy

Exporting every VSWAP sprite chunk (decision 2 above) solves "a real buffer
exists for whichever shapenum the eZ80 actor state machine picks" without
needing to reverse-engineer `WL_ACT1.C`'s `statetype` tables. The remaining
question was per-level *pruning*: which of those exported shapenums does a
given level actually need? `formats/sprite_kinds.py` answers this with a
derived heuristic (documented in-file, not independently source-grounded
like the anchors it builds on): real VSWAP sprite chunks are laid out in
contiguous per-creature-type blocks, so sorting `spritenames.py`'s known
first-frame anchors (`SPR_GRD_S_1=50`, `SPR_DOG_W1_1=99`, etc.) by shapenum
and treating each as a block boundary yields every frame for a kind that
appears in a level (stand/patrol/pain/shoot/die, any facing, any difficulty
tier) without needing the harder, deferred statetype-table reverse-
engineering. Statics need no heuristic at all -- `spritenames.
STATIC_SHAPENUMS` is already an exact 1:1 mapping. Flagged for visual
revisit via the Stage E viewer (not yet built) if a block boundary turns
out wrong.

## Implementation status (2026-07-31)

All under `agonport/tools/wolf3d_assets/`, tested against the real
shareware `orig/data/{VSWAP,MAPHEAD,GAMEMAPS}.WL1`:

- **`formats/`** -- vendored `palette.py`, `vswap.py` (+ door-texture
  helpers), `mapfile.py`, `spritenames.py`, plus new `sprite_kinds.py`.
- **`agnb/manifest.py`** -- JSONL schema (`kind`+`assetId`-derived
  `bufferId`, validated).
- **`agnb/container.py`** -- RIFF writer (`align4`/`make_chunk`/
  `make_buffer_record`/`build_container`), byte-level validated against a
  produced file (RIFF/AGNB/VERS header, LIST BUFR record count and buffer
  ids all round-tripped correctly).
- **`scripts/export_vswap_art.py`** (Stage A) -- real run: 28/49 wall ids
  present (shareware only ships episode 1 art; ids 29-49 are zero-length
  placeholders), 4 door textures, 226/436 sprite chunks present.
- **`scripts/convert_assets.py`** (Stage B) -- real run: all 258 assets
  converted with `agonutils` at the Agon64 palette, default `rgb` method;
  spot-checked visually (wall texture and a guard sprite both look correct,
  sprite transparency preserved).
- **`scripts/build_level_manifest.py`** (Stage C) -- real run against all 10
  populated MAPHEAD slots (`Wolf1 Map1`-`Map8`, `Boss`, `Secret`); per-level
  tile-asset counts 12-20, sprite-asset counts 19 (Boss level) to 169.
- **`scripts/pack_agnb.py`** (Stage D) -- real run: 10 levels x 2 containers
  each. Sprite containers are large (up to ~700KB) since a level's sprite
  set now includes every animation frame for every creature kind that
  appears in it, not one representative frame -- a direct, expected
  consequence of decision 2 above, worth keeping in mind for ESP32 SRAM
  budgeting.
- **Stage E (visual QA viewer)** -- not yet built.
- **Stage F (eZ80 loading)** -- no new code needed, per the original plan
  (`agnb_api.inc` already implements this); still not yet wired up on the
  eZ80 side, and that side still needs the door-textureId table above.
