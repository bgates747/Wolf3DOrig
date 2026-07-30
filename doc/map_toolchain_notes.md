# Map & Wall/Door Texture Toolchain Notes

## Scope (this phase)

Focused first goal: an **end-to-end toolchain for authoring novel maps** that run
under the real shareware `WOLF3D.EXE` (WL1 format only), covering:

- Map geometry: walls, doors, floor/area codes (GAMEMAPS plane 0).
- Wall & door textures (VSWAP wall-texture chunks).
- The bare minimum of plane 1 (info plane) needed for a level to be
  *playable at all* — i.e. a player start position/facing — is called out
  below as an open question, since strictly it's a "marker," not
  environment/texture data.

Explicitly **out of scope for now** (per Author): sprite bitmaps (actors,
items, decorations) and sound/music assets. These get their own pass later.

Format constraint: **WL1 shareware only** — 64×64 tile grid (hard-coded,
engine `Quit()`s if not exactly 64×64), `MAXWALLTILES` = 64 (63 usable wall
types), 10 level slots (Episode 1 only in the shareware data set).

## Community tooling survey

Searched for an existing Linux-native (or at least cross-platform) toolchain
for editing/authoring the *original binary* WL1 map/texture format, per the
Author's preference to reuse an existing pipeline before building one from
scratch.

**Finding: nothing found runs natively on Linux.** Every editor discovered
targets DOS or Windows. Summary (via
[wolfenvault.areyep.com/utilities.html](https://wolfenvault.areyep.com/utilities.html),
the most complete current archive of Wolf3D modding tools):

| Tool | Platform | Scope | Notes |
| --- | --- | --- | --- |
| **TED5** | DOS | Levels only | The actual original id Software level editor (per [ModdingWiki](https://moddingwiki.shikadi.net/wiki/Wolfenstein_3-D)). Ground truth for the format, but DOS-only and hard to source today. |
| **MapEdit 7.2** | DOS | Maps | Last version compatible with the **shareware** WL1 format specifically (later MapEdit versions target registered WL6 only). |
| **MapEdit 8.5** | DOS | Maps | Later/WL6-oriented; "mileage may vary on modern systems." |
| **Havoc's Wolfenstein 3D Editor** | Windows | Maps | Described as "the modern MapEdit," supports up to 128×128 maps. |
| **WDC 1.17.396** | Windows | Maps, sounds, graphics, music, help screens | "The most popular all-in-one editor," also supports Spear of Destiny, Blake Stone, Corridor 7. |
| **ChaosEdit** | Windows | Maps, graphics, sound | Has a live 3D preview pane. |
| **FloEdit II / 1.1** | Windows | Maps, graphics, sounds | Installer reportedly has issues on 64-bit Windows. |
| **Pixelformer** | Windows | 256-color image editing | Generic indexed-bitmap editor, "great for Wolf3D textures and sprites," not Wolf3D-specific. |

No web-based, Python, or Linux-native original-format editor turned up, and no
existing exporter from Tiled (or any modern tile-map tool) into
`MAPHEAD.WL1`/`GAMEMAPS.WL1` was found. (Note: two `wl6.fandom.com` wiki pages
that looked promising — `Linuxwolf` and `WLEdit` — redirected through an
ad-sync/tracking URL chain instead of returning real content; they were not
usable as a source and are not relied on above.)

Everything modern in the wider Wolf3D modding scene (Wolf4SDL, ECWolf, WLEdit,
"Wolf3d Modding: Mapping for ECWolf") targets **source-port** engines with
their own extended map formats (XLAT translation layer, etc.), not the literal
DOS `.EXE` + WL1 files this project runs.

### Recommendation

No ready-made Linux-compatible pipeline exists for the actual original format,
so build one, matching the Author's stated preference for Tiled:

1. **Tiled** (already cross-platform/Linux-native, actively maintained) as the
   map-editing GUI — author levels as an ordinary tile map.
2. A custom **Python compiler** (extends the already-scaffolded
   `src/toolchain/`) that translates Tiled's map export into
   `MAPHEAD.WL1`/`GAMEMAPS.WL1`, and a texture pipeline that converts PNGs
   (edited in any ordinary Linux raster tool — GIMP/Krita/Aseprite) into
   `VSWAP.WL1` wall-texture chunks.
3. Keep **MapEdit 7.2** in reserve, run via the existing
   `dosbox/wolf3d.conf` DOSBox setup, purely as an independent
   cross-validation tool (open our compiled files in a known-good original
   shareware-compatible editor) — not as the primary authoring tool.

### Decision: Tiled confirmed, MapEdit source-port rejected

Considered (and rejected) porting/modifying `MapEdit.exe`'s own Pascal source
(`tools/mapedit72/mapedit.pas`, bundled in the downloaded archive) to run
natively on Linux, instead of adopting Tiled. Verdict: **not worth it.**

- The source is plain, unobfuscated Turbo Pascal (2261 lines) — readily
  readable — but built directly on three DOS-specific units:
  `uses crt,dos,graph,mouse;`. `graph` is Borland Graphics Interface
  (`EGAVGA.BGI`, a real-mode VGA driver bundled alongside it), `dos` is raw
  DOS/BIOS interrupt access, and `mouse` (`MOUSE.PAS`) does raw `INT 33h`
  real-mode mouse-driver calls.
- These aren't confined to a swappable platform layer — display calls (e.g.
  `output(i, j, mapgraph[...])`) are interleaved directly throughout the
  editor/UI logic. Porting would mean rewriting essentially the entire
  display/input layer while untangling it from map logic it's woven into —
  comparable effort to writing a new editor from scratch, with the added
  cost of doing it inside 30-year-old single-file Pascal.
- Confirmed final choice: **Tiled**, both because it sidesteps building *any*
  bespoke editing GUI (no Tkinter/Qt/etc. needed on our side at all — Tiled's
  own mature, cross-platform UI already does tile picking, layers, undo,
  object placement, and custom properties), and because the Author already
  has hands-on Tiled experience from another project (an Agon Light game),
  lowering the learning curve.
- `MapEdit 7.2` remains solely a **read-only cross-validation viewer** (see
  "Implementation status" below for the export-blocking caveat that rules it
  out as a build path anyway) — never a source-port candidate or primary
  authoring tool.

## Grounded file-format facts

### MAPHEAD.WL1 / GAMEMAPS.WL1 (map geometry)

Source: [ModdingWiki – GameMaps Format](https://moddingwiki.shikadi.net/wiki/GameMaps_Format),
cross-checked against `orig/src/WOLFSRC/WL_GAME.C`.

- **MAPHEAD.WL1**: `UINT16LE magic` (RLEW tag, `0xABCD`) + `INT32LE[100] ptr`
  (byte offset into GAMEMAPS for each of 100 possible level slots; `<= 0`
  means "no level"). Wolfenstein 3-D has no tileinfo data appended, so the
  file is exactly 402 bytes.
- **GAMEMAPS.WL1**: literal string `"TED5v1.0"` followed by a series of
  compressed chunks. Each level has a 38-byte, *never*-compressed level
  header (usually followed by a `"!ID!"` signature marking it as v1.1+
  format, i.e. Carmack-compressed):
  - `offPlane0/1/2` (`INT32LE`), `lenPlane0/1/2` (`UINT16LE`) — plane 0
    is the wall/floor layer, plane 1 is the object/info layer, plane 2 is
    unused by Wolf3D (engine only loads planes 0 and 1).
  - `width`, `height` (`UINT16LE`, ignored by the engine — it always assumes
    64×64), `name` (`char[16]`, editor-only cosmetic level name).
- **Compression**: RLEW always applied; **Carmack compression** layered on
  top for v1.1+ (which the shareware files use). Carmack compression is
  detailed on its [own page](https://moddingwiki.shikadi.net/wiki/Carmack_compression) —
  near pointers (`len, 0xA7, backref`) and far pointers
  (`len, 0xA8, absolute-offset-u16`), with an escape sequence
  (`00 Ax yy`) for words that would otherwise collide with the `0xA7`/`0xA8`
  tag bytes. A working reference implementation exists in
  [gamecompjs' `cmp-carmackize.js`](https://github.com/Malvineous/gamecompjs/blob/master/formats/cmp-carmackize.js).
  Both directions (decompress for extraction/validation, compress for
  building new levels) will need implementing.

### Plane 0 tile value semantics (walls, doors, floors)

Grounded directly in `orig/src/WOLFSRC/`:

- `WL_DEF.H`: `MAXWALLTILES = 64` (values 1–63 = wall types), `AREATILE = 107`
  (first of `NUMAREAS = 37` open-floor codes, so 64–106 are floor-area
  variants), `ELEVATORTILE = 21` (a special plane-0 floor value).
- `WL_GAME.C` (`SetupGameLevel`, ~line 660): any plane-0 tile `< AREATILE`
  (i.e. 1–106) is solid/blocking; `>= AREATILE` is open floor.
- **Doors** are plane-0 values **90–101** (`WL_GAME.C` ~line 698): even values
  90/92/94/96/98/100 are vertical doors, odd values 91/93/…/101 are
  horizontal doors; `(tile-90)/2` or `(tile-91)/2` selects one of 6 door
  "lock" types (normal, gold key, silver key, etc.).
- **Wall → texture mapping** (`WL_MAIN.C`, `SetupWalls()`, confirmed at
  source): for wall tile value `i` (1..63),
  `horizwall[i] = (i-1)*2` and `vertwall[i] = (i-1)*2+1` — i.e. every wall
  type occupies **two consecutive VSWAP chunks** (a "light" side and
  "dark"/shaded side texture), selected depending on which side of the wall
  the ray hits.

### Plane 1 tile value semantics (info plane / markers)

Grounded in `WL_GAME.C` (`ScanInfoPlane`, ~line 221) — useful because it
directly answers the still-open devlog Q3/Q4 taxonomy questions for the
*original binary* format (separate from the PNG-overview extraction effort):

- `19–22`: player start position, facing N/E/S/W (`SpawnPlayer(x, y, NORTH + tile - 19)`).
- `23–74`: static objects/decorations (`SpawnStatic(x, y, tile - 23)`) — out
  of scope for this phase.
- `98`: secret pushwall marker (increments `secrettotal`) — plane 1, distinct
  from the plane-0 `PUSHABLETILE` constant of the same numeric value (98) in
  `WL_DEF.H`; the two never collide because they're read from different
  planes.
- `106`: `AMBUSHTILE` — marks a nearby guard as a silent ambush.
- `108+`: enemy spawns, tiered in blocks of 36 by difficulty
  (`108–111` = always, `144–147` = medium+, `180–183` = hard only, each
  offset selecting a facing direction) — out of scope for this phase.

For this phase, the **only** plane-1 content likely needed is the player
start marker (19–22), since a level needs one to be playable/testable at all
— flagged as an open question below rather than assumed.

### VSWAP.WL1 (wall & door textures)

Grounded in `orig/src/WOLFSRC/ID_PM.C` / `WL_DRAW.C`:

- Header: `UINT16LE numchunks`, `UINT16LE spritestart` (`PMSpriteStart`),
  `UINT16LE soundstart` (`PMSoundStart`), followed by `numchunks × UINT32LE`
  offsets and `numchunks × UINT16LE` lengths, then the raw chunk bytes.
- Chunks `0 .. spritestart-1` are wall/door textures: each is a raw,
  **uncompressed**, 64×64, 8-bit indexed (VGA 256-color palette) bitmap,
  stored **column-major** (each of the 64 columns is 64 contiguous bytes).
  Chunks `spritestart .. soundstart-1` are sprites (post/column-encoded,
  out of scope). Chunks `soundstart..` are digitized sounds (out of scope).
- `DOORWALL` is defined as `PMSpriteStart - 8`, i.e. the 8 chunks
  immediately before the sprite range are dedicated door-face textures.
- Implication for the texture pipeline: a PNG round-trip codec needs (a) the
  Wolf3D 256-color VGA palette to convert between indexed VSWAP bytes and a
  normal image, and (b) to preserve chunk **pairing** (light/dark variants
  per wall type) and the fixed door-texture block at the end of the wall
  range.

## Proposed implementation plan

1. **Codec layer** (`src/toolchain/formats/`):
   - `mapfile.py` — MAPHEAD/GAMEMAPS reader + writer: RLEW encode/decode,
     Carmack encode/decode, level header packing.
   - `vswap.py` — VSWAP reader + writer: chunk table I/O, wall-chunk
     ⇄ PNG conversion using a shared palette module.
   - `palette.py` — the Wolf3D VGA palette (extracted once from the
     shareware data or hard-coded from a verified reference), shared by
     texture import/export and by Tiled-tileset image generation.
2. **Extraction path first** (builds confidence + regression fixtures):
   `src/toolchain/cli/extract.py` — decode the existing shareware
   `MAPHEAD.WL1`/`GAMEMAPS.WL1`/`VSWAP.WL1` into (a) a Tiled-compatible
   tileset PNG of all wall/door textures and (b) one Tiled map file per
   existing level, using the tile-value semantics above. This also gives
   `tests/` real ground-truth data to round-trip against.
3. **Build path**: `src/toolchain/cli/build.py` — take an authored Tiled map
   (plus any new/edited wall texture PNGs) and re-encode into WL1-format
   binaries.
4. **Playtest loop**: point the existing `dosbox/wolf3d.conf` at a build
   output directory (or overwrite a scratch copy of `orig/data`) to confirm
   the shareware `.EXE` loads and renders the authored level correctly —
   reusing the already-validated DOSBox setup from this session.

## Decisions (answered)

1. **WL1 output target**: sandboxed `build/wl1/` output, copied over a
   scratch data dir for playtesting (not written in-place over `orig/data`).
2. **Player start marker**: yes — include plane-1 tiles 19-22 now, since a
   level needs one to be playable/testable at all.
3. **Palette source**: hard-code a known-good published Wolf3D palette
   constant rather than programmatically extracting it from VGAGRAPH.
   Implemented in `src/toolchain/formats/palette.py`, transcribed from
   Wolf4SDL's `wolfpal.inc` (an established open-source reproduction of id's
   VGA palette; distinct from that repo's `sodpal.inc` for Spear of Destiny).
4. **MapEdit 7.2**: set it up under DOSBox now, in parallel with the Python
   codec work, rather than deferring it. **Important caveat discovered**
   after downloading it (`tools/mapedit72/README.1ST`, "VERSION 7.1 NOTES"):
   since v7.1, MapEdit **deliberately refuses to write/export `.WL1`
   GAMEMAPS files usable by the shareware game** (an anti-piracy measure by
   its author, to stop free "shareware + fan levels" distribution from
   undercutting registration). It can still open/view/edit shareware levels
   on-screen and export individual floors in its own exchange format. This
   confirms MapEdit's role in this project is strictly a **read-only visual
   cross-validation tool** (e.g. eyeballing that our decoded/re-encoded
   levels look structurally sane) — it is *not* an alternate build path, so
   the custom Python codec remains the only way to produce new shareware-
   loadable GAMEMAPS/MAPHEAD files.
   Setup: `dosbox/mapedit.conf` mounts `tools/mapedit72/` (downloaded
   archive + copies of the real `MAPHEAD.WL1`/`GAMEMAPS.WL1`/`VSWAP.WL1`/
   VGA graphics files, gitignored) as `C:` and runs `MAPEDIT.EXE`. Launch
   with `dosbox -conf dosbox/mapedit.conf`.

## Implementation status

- `src/toolchain/formats/palette.py` — done. 256-entry 6-bit VGA palette +
  `to_rgb888()` scaling helper.
- `src/toolchain/formats/mapfile.py` — done. RLEW encode/decode, Carmack
  encode/decode, MAPHEAD/GAMEMAPS reader + writer. The Carmack *encoder* is a
  correct-but-unoptimized literal-word encoder (no back-reference search) —
  floppy-disk space savings aren't a constraint for this project, and the
  decoder (which does need to be fully correct, to read the real shareware
  data) is complete and round-trip tested.
- `src/toolchain/formats/vswap.py` — done. VSWAP reader/writer, wall/door
  chunk ⇄ PIL image conversion via the hard-coded palette. Requires Pillow
  (see below).
- `src/toolchain/cli/extract.py` — done (first pass). Decodes the real
  shareware `VSWAP.WL1` into a wall/door texture sheet PNG, and all 10
  Episode 1 levels' plane0/plane1 grids into JSON, under `build/extracted/`
  (gitignored, regenerated). Verified visually — produces a correct,
  recognizable Wolf3D texture sheet.
- **Tiled export** (`extract_tiled_maps`/`build_plane0_tileset`/
  `build_level_tmx` in `extract.py`) — done. Emits `build/extracted/tiled/`:
  a `plane0_tileset.tsx` (+ backing PNG) and one `.tmx` per real shareware
  level. This settles the schema empirically:
  - **GID == plane0 tile value directly** (tileset `firstgid=1`) — no
    separate value↔GID lookup table anywhere in the pipeline. Tile values
    1-63 render their real wall texture (via `wall_tile_to_chunks`); 90-101
    (doors) and 107-143 (floor/area codes) get flat placeholder colors for
    now, since doors pick their real texture by lock type at runtime rather
    than having one fixed per-tile texture, and area codes only affect
    sound/area connectivity, not appearance.
  - **Plane 1 → two representations**, split by how sparse/dense each part
    is:
    - The **player-start marker** (tiles 19-22) is sparse, so it becomes a
      Tiled **object layer** (`markers`) point object
      (`type="PlayerStart"`, `x`/`y` in pixels, a `facing` property of
      `N`/`E`/`S`/`W` per `WL_DEF.H`'s `NORTH=0/EAST=1/SOUTH=2/WEST=3` and
      `WL_GAME.C`'s `SpawnPlayer(x, y, NORTH + tile - 19)`).
    - Everything else in plane1 (enemies at all three difficulty tiers,
      bosses, static items/decorations, the secret-pushwall marker) is
      dense enough to be a second Tiled **tile layer** (`plane1`), grounded
      directly against `WL_GAME.C`'s `ScanInfoPlane()` switch (non-`SPEAR`
      branch only — this project targets the original WL1/WL6 episodes,
      not Spear of Destiny). `PLANE1_MAX_VALUE=259` (highest code: hard
      mutant patrol, 256-259). Since a Tiled map has one shared GID
      namespace across all its tilesets, this layer can't reuse `firstgid=1`
      like plane0 does — its tileset (`plane1_tileset.tsx`) instead starts
      at `firstgid = PLANE0_MAX_VALUE + 1 = 144`, so
      **GID = plane1 value + (firstgid - 1)**, a single fixed additive
      offset rather than a per-value lookup table. Cells holding a
      player-start code are always written as GID 0 here (that data lives
      solely in the `PlayerStart` object) to avoid two disagreeing sources
      of truth for the same cell.
    - Since decoding VSWAP's sprite-chunk format (column-sparse, masked,
      distinct from the flat 64×64 wall-texture format) is a substantially
      bigger task, plane1 tiles are rendered as **category-colored,
      number-and-mnemonic-stamped placeholders** (green=static item,
      orange=pushwall, dark red=enemy any tier, purple=unique boss,
      pink=ghost, gray=unused code) rather than real sprite art — full-
      fidelity data, placeholder visuals. The mnemonic (e.g. `GRD`, `HANS`,
      `1up`, `PUSH`) is a legend on top of the raw dispatch code, grounded
      directly in `WL_GAME.C`'s `ScanInfoPlane()` switch and (for the 49
      static item types) `WL_ACT1.C`'s `statinfo[]` table comments — it's
      not stored/round-tripped anywhere, purely a `extract.py`-side visual
      aid. **Future QoL TODO, not on the critical path**: replace these
      placeholders with real decoded VSWAP sprite art once that decoder
      exists.
  - **Validated two ways**: `flatpak run org.mapeditor.Tiled --export-map
    level_00.tmx level_00_check.json` round-trips through Tiled's own parser
    with no errors and preserves both tile layers, both tilesets' GID
    ranges, and the `PlayerStart` object/property exactly; and the file
    opens and renders correctly in the Tiled GUI itself (confirmed visually
    — recognizable, structurally sound level layout).
  - `propertyTypes` in `wolf3dmaps.tiled-project` is still deliberately
    empty — `PlayerStart`'s `facing` property works fine as a plain string
    for now; a proper Tiled custom "class" type is only worth adding once
    `build.py` needs to validate/constrain it, or once door lock-type needs
    representing too.
- `src/toolchain/cli/build.py` (Tiled → WL1 direction) — done. Parses each
  `level_NN.tmx` (stdlib `xml.etree`, no new dependency), reading each
  tileset's `firstgid` from the file itself rather than hard-coding it (so
  the plane1 tileset can grow/shrink without breaking the parser).
  Validates the schema above (64×64, plane0 `firstgid=1`, no empty/GID-0
  plane0 cells, no raw player-start codes leaking into the generic plane1
  tile layer, no cell claimed by both a `PlayerStart` object and a plane1
  tile), rebuilds plane0 and plane1 (actors/items/pushwall codes *and* the
  player-start marker) fully, and recovers the level name from a
  `levelName` map property extract.py writes. Calls `mapfile.build_gamemaps`
  and writes `MAPHEAD.WL1`/`GAMEMAPS.WL1` to `build/wl1/`. Round-trip tested
  (`tests/test_build.py`): extract → build reproduces the original plane0
  grid *and full plane1 grid* (not just player-start) exactly, for all 10
  shareware levels. `build.py` only compiles map data; `VSWAP.WL1`/
  `VGA*.WL1`/etc. must still be copied from `orig/data/` alongside its
  output for a complete, runnable game directory.
- `tests/test_formats.py` — done. Round-trip tests for RLEW/Carmack/plane
  codecs, plus ground-truth checks against the real shareware
  `MAPHEAD.WL1`/`GAMEMAPS.WL1`/`VSWAP.WL1` (10 levels, all 64×64, each with
  exactly one player-start marker; wall chunk 0 round-trips through a PNG).
- **Python environment**: no system Pillow was installed. Set up a
  project-local virtualenv (`.venv/`, gitignored) + `requirements.txt`
  (`Pillow>=10`) rather than touching system Python packages. Run tools via
  `.venv/bin/python -m toolchain.cli.extract` (with `PYTHONPATH=src`, or from
  an installed/editable package once one exists) or `.venv/bin/pytest`.
- **MapEdit 7.2**: setup tracked separately below.
- **Tiled**: installed via Flatpak (`flatpak install flathub
  org.mapeditor.Tiled`), **not** vendored in the repo and **not** the older
  `apt` package (1.8.2 vs. Flathub's 1.12.2 — the newer version has custom
  property *types*/classes, useful for things like door lock-type or
  player-start facing). Confirmed working: `flatpak run org.mapeditor.Tiled
  --version` → `Tiled 1.12.2`.
  A project-scoped `src/content/maps/wolf3dmaps.tiled-project` file has been
  added (tracked in git) to scope future custom property types to this
  project, mirroring the pattern seen in another local Agon project
  (`~/Agon/mystuff/nurples/tiles/dg/`) — but *not* copying that project's
  choice to also track the `.tiled-session` file, since that's per-user
  transient UI state (open files, scroll/zoom); `*.tiled-session` is
  gitignored here instead.
  Launch with `flatpak run org.mapeditor.Tiled
  src/content/maps/wolf3dmaps.tiled-project`.
  `propertyTypes` in the project file is intentionally left empty for now —
  it should be filled in once `build.py`'s Tiled GID/property schema
  (the next open design task, see above) is actually decided, rather than
  guessed at ahead of time.
