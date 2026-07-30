"""Extract the real shareware WL1 data into inspectable, editable artifacts:

- A wall/door texture tileset PNG (one tile per VSWAP wall/door chunk).
- Per-level plane0/plane1 tile grids dumped as JSON (ground truth for
  round-trip tests).
- A Tiled tileset (.tsx) + per-level map (.tmx) so a real decoded level can
  be opened and visually validated in Tiled itself.

Usage: .venv/bin/python -m toolchain.cli.extract [--orig-data DIR] [--out DIR]
"""
from __future__ import annotations

import argparse
import json
import os
from xml.sax.saxutils import escape

from PIL import Image, ImageDraw, ImageFont

from toolchain.formats import mapfile, vswap

TILESET_COLUMNS = 8

# Tiled plane0 tileset: GID == plane0 tile value directly (tileset firstgid=1),
# so no separate value<->GID lookup table is needed anywhere in this pipeline.
PLANE0_TILESET_COLUMNS = 16
DOOR_MIN, DOOR_MAX = 90, 101
AREA_TILE, NUM_AREAS = 107, 37
PLANE0_MAX_VALUE = AREA_TILE + NUM_AREAS - 1  # 143

# Plane1 player-start tiles -> facing, per WL_GAME.C's
# SpawnPlayer(x, y, NORTH + tile - 19) and WL_DEF.H's NORTH=0/EAST=1/SOUTH=2/WEST=3.
PLAYER_START_FACING = {19: "N", 20: "E", 21: "S", 22: "W"}

# All other plane1 codes (actors/items/pushwall marker), grounded against
# WL_GAME.C's ScanInfoPlane() (non-SPEAR branch: this project targets the
# original WL1/WL6 episodes, not Spear of Destiny). These are rendered as
# generic, category-colored placeholders (not real sprite art -- decoding
# VSWAP's sprite chunk format, distinct from the flat wall-texture format,
# is a bigger task deferred for later) stamped with the raw tile number, so
# a level is still fully editable/inspectable without inventing per-monster
# assets. GID == plane1 value + PLANE1_GID_OFFSET (tileset firstgid ==
# PLANE0_MAX_VALUE + 1, so the two tilesets' GID ranges don't collide).
PLANE1_MAX_VALUE = 259  # highest code used: hard mutant patrol (256-259)
PLANE1_TILESET_COLUMNS = 16
PLANE1_GID_OFFSET = PLANE0_MAX_VALUE
PUSHWALL_TILE = 98
STATIC_MIN, STATIC_MAX = 23, 74
DEAD_GUARD_TILE = 124
GHOST_MIN, GHOST_MAX = 224, 227
# guard/officer/ss/dog stand+patrol blocks, repeated at +36 per difficulty tier
# (easy/medium/hard); mutant blocks repeated at +18 per tier instead.
ENEMY_RANGES = [(108, 141), (144, 177), (180, 213), (216, 223), (234, 241), (252, 259)]
BOSS_TILES = {214, 197, 215, 179, 196, 160, 178}  # Hans/Gretel/Otto/Fat/Schabbs/fake+real Hitler


def _plane1_category_color(value: int) -> tuple[int, int, int]:
    if PLAYER_START_FACING.get(value):
        return (255, 215, 0)  # player start (also its own object; rare to render as a tile)
    if value == PUSHWALL_TILE:
        return (230, 140, 20)  # secret pushwall marker
    if STATIC_MIN <= value <= STATIC_MAX:
        return (60, 160, 60)  # static item/decoration
    if value == DEAD_GUARD_TILE:
        return (110, 90, 80)  # dead guard (decorative)
    if value in BOSS_TILES:
        return (140, 0, 170)  # unique boss
    if GHOST_MIN <= value <= GHOST_MAX:
        return (255, 105, 180)  # spectre ghosts
    if any(lo <= value <= hi for lo, hi in ENEMY_RANGES):
        return (150, 30, 30)  # guard/officer/ss/dog/mutant, any difficulty tier
    return (80, 80, 80)  # unused/unknown code


def extract_tileset(vswap_path: str, out_dir: str) -> int:
    with open(vswap_path, "rb") as f:
        vs = vswap.read_vswap(f.read())
    wall_chunk_count = vs.spritestart  # chunks [0, spritestart) are wall/door textures
    rows = (wall_chunk_count + TILESET_COLUMNS - 1) // TILESET_COLUMNS
    size = vswap.TEXTURE_SIZE
    sheet = Image.new("RGB", (TILESET_COLUMNS * size, rows * size), (255, 0, 255))
    for i in range(wall_chunk_count):
        chunk = vs.chunks[i]
        if not chunk:
            continue
        tile = vswap.chunk_to_image(chunk)
        x, y = (i % TILESET_COLUMNS) * size, (i // TILESET_COLUMNS) * size
        sheet.paste(tile, (x, y))
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "wall_textures.png")
    sheet.save(out_path)
    return wall_chunk_count


def extract_levels(maphead_path: str, gamemaps_path: str, out_dir: str) -> list[str]:
    with open(maphead_path, "rb") as f:
        maphead = mapfile.read_maphead(f.read())
    with open(gamemaps_path, "rb") as f:
        gamemaps = f.read()
    os.makedirs(out_dir, exist_ok=True)
    written = []
    for index, offset in enumerate(maphead.level_offsets):
        if offset <= 0:
            continue
        level = mapfile.read_level(gamemaps, maphead, index)
        out_path = os.path.join(out_dir, f"level_{index:02d}.json")
        with open(out_path, "w") as f:
            json.dump({
                "index": index,
                "name": level.header.name,
                "width": mapfile.MAP_WIDTH,
                "height": mapfile.MAP_HEIGHT,
                "plane0": level.plane0,
                "plane1": level.plane1,
            }, f)
        written.append(out_path)
    return written


def _plane0_tile_image(vs: vswap.VSwapFile, value: int) -> Image.Image:
    size = vswap.TEXTURE_SIZE
    if 1 <= value <= 63:  # wall types, incl. ELEVATORTILE=21 (just another wall type)
        horiz, _vert = vswap.wall_tile_to_chunks(value)
        chunk = vs.chunks[horiz] if horiz < len(vs.chunks) else b""
        # Unused wall-type slots may have no chunk, or -- since DOORWALL's door
        # textures are packed at the end of the same chunk range -- a chunk of
        # the wrong size (only real, level-referenced wall types are guaranteed
        # a genuine 64x64 texture). Either way, fall back to a placeholder.
        if len(chunk) == size * size:
            return vswap.chunk_to_image(chunk)
        return Image.new("RGB", (size, size), (255, 0, 255))  # wall type unused by shareware
    if DOOR_MIN <= value <= DOOR_MAX:
        # Real doors pick a VSWAP door-face texture at runtime by lock type;
        # a flat placeholder is enough to spot/edit door placement in Tiled.
        return Image.new("RGB", (size, size), (150, 100, 40))
    if AREA_TILE <= value <= PLANE0_MAX_VALUE:
        return Image.new("RGB", (size, size), (190, 190, 190))  # open floor/area
    return Image.new("RGB", (size, size), (255, 0, 255))  # undefined code


def build_plane0_tileset(vswap_path: str, out_dir: str) -> tuple[str, str]:
    """Build a Tiled tileset (.tsx + backing .png) where GID == plane0 tile
    value directly (firstgid=1) -- no separate value<->GID table needed."""
    with open(vswap_path, "rb") as f:
        vs = vswap.read_vswap(f.read())
    size = vswap.TEXTURE_SIZE
    columns = PLANE0_TILESET_COLUMNS
    rows = (PLANE0_MAX_VALUE + columns - 1) // columns
    sheet = Image.new("RGB", (columns * size, rows * size), (255, 0, 255))
    for value in range(1, PLANE0_MAX_VALUE + 1):
        local_id = value - 1
        x, y = (local_id % columns) * size, (local_id // columns) * size
        sheet.paste(_plane0_tile_image(vs, value), (x, y))

    os.makedirs(out_dir, exist_ok=True)
    png_path = os.path.join(out_dir, "plane0_tileset.png")
    sheet.save(png_path)

    tsx_path = os.path.join(out_dir, "plane0_tileset.tsx")
    with open(tsx_path, "w") as f:
        f.write(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<tileset version="1.10" tiledversion="1.12.2" name="wolf3d_plane0" '
            f'tilewidth="{size}" tileheight="{size}" tilecount="{PLANE0_MAX_VALUE}" '
            f'columns="{columns}">\n'
            f' <image source="plane0_tileset.png" width="{columns * size}" '
            f'height="{rows * size}"/>\n'
            '</tileset>\n')
    return tsx_path, png_path


def _plane1_tile_image(size: int, font: ImageFont.ImageFont, value: int) -> Image.Image:
    tile = Image.new("RGB", (size, size), _plane1_category_color(value))
    draw = ImageDraw.Draw(tile)
    label = str(value)
    bbox = draw.textbbox((0, 0), label, font=font)
    pos = ((size - (bbox[2] - bbox[0])) // 2 - bbox[0], (size - (bbox[3] - bbox[1])) // 2 - bbox[1])
    shadow = (pos[0] + 1, pos[1] + 1)
    draw.text(shadow, label, fill=(0, 0, 0), font=font)
    draw.text(pos, label, fill=(255, 255, 255), font=font)
    return tile


def build_plane1_tileset(out_dir: str) -> tuple[str, str]:
    """Build a Tiled tileset (.tsx + backing .png) of category-colored,
    number-stamped placeholders for plane1 actor/item/pushwall codes (see
    the PLANE1_* constants above for the grounding and the real-sprite-art
    caveat). GID == plane1 value + PLANE1_GID_OFFSET (tileset firstgid ==
    PLANE0_MAX_VALUE + 1), so its GIDs never collide with the plane0 tileset
    sharing the same map."""
    size = vswap.TEXTURE_SIZE
    columns = PLANE1_TILESET_COLUMNS
    rows = (PLANE1_MAX_VALUE + columns - 1) // columns
    font = ImageFont.load_default()
    sheet = Image.new("RGB", (columns * size, rows * size), (255, 0, 255))
    for value in range(1, PLANE1_MAX_VALUE + 1):
        local_id = value - 1
        x, y = (local_id % columns) * size, (local_id // columns) * size
        sheet.paste(_plane1_tile_image(size, font, value), (x, y))

    os.makedirs(out_dir, exist_ok=True)
    png_path = os.path.join(out_dir, "plane1_tileset.png")
    sheet.save(png_path)

    firstgid = PLANE1_GID_OFFSET + 1
    tsx_path = os.path.join(out_dir, "plane1_tileset.tsx")
    with open(tsx_path, "w") as f:
        f.write(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<tileset version="1.10" tiledversion="1.12.2" name="wolf3d_plane1" '
            f'tilewidth="{size}" tileheight="{size}" tilecount="{PLANE1_MAX_VALUE}" '
            f'columns="{columns}">\n'
            f' <image source="plane1_tileset.png" width="{columns * size}" '
            f'height="{rows * size}"/>\n'
            '</tileset>\n')
    return tsx_path, png_path


def build_level_tmx(gamemaps: bytes, maphead: mapfile.MapHead, index: int, out_dir: str) -> str:
    level = mapfile.read_level(gamemaps, maphead, index)
    width, height = mapfile.MAP_WIDTH, mapfile.MAP_HEIGHT

    plane0_csv = ",\n".join(",".join(str(v) for v in row) for row in level.plane0)

    def plane1_gid(value: int) -> int:
        # Player-start codes are represented exclusively by the PlayerStart
        # object below, so they're omitted (0) from this generic tile layer.
        if value == 0 or value in PLAYER_START_FACING:
            return 0
        return value + PLANE1_GID_OFFSET

    plane1_csv = ",\n".join(",".join(str(plane1_gid(v)) for v in row) for row in level.plane1)

    objects = []
    obj_id = 1
    for y in range(height):
        for x in range(width):
            facing = PLAYER_START_FACING.get(level.plane1[y][x])
            if facing is not None:
                objects.append(
                    f'  <object id="{obj_id}" name="PlayerStart" type="PlayerStart" '
                    f'x="{x * 64}" y="{y * 64}" width="64" height="64">\n'
                    f'   <properties>\n'
                    f'    <property name="facing" value="{facing}"/>\n'
                    f'   </properties>\n'
                    f'  </object>\n')
                obj_id += 1

    level_name = escape(level.header.name or f"Level {index}", {'"': "&quot;"})
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<map version="1.10" tiledversion="1.12.2" orientation="orthogonal" '
        f'renderorder="right-down" width="{width}" height="{height}" tilewidth="64" '
        f'tileheight="64" infinite="0" nextlayerid="4" nextobjectid="{obj_id}">\n'
        f' <properties>\n'
        f'  <property name="levelName" value="{level_name}"/>\n'
        f' </properties>\n'
        f' <tileset firstgid="1" source="plane0_tileset.tsx"/>\n'
        f' <tileset firstgid="{PLANE1_GID_OFFSET + 1}" source="plane1_tileset.tsx"/>\n'
        f' <layer id="1" name="plane0" width="{width}" height="{height}">\n'
        f'  <data encoding="csv">\n{plane0_csv}\n</data>\n'
        f' </layer>\n'
        f' <layer id="2" name="plane1" width="{width}" height="{height}">\n'
        f'  <data encoding="csv">\n{plane1_csv}\n</data>\n'
        f' </layer>\n'
        f' <objectgroup id="3" name="markers">\n{"".join(objects)} </objectgroup>\n'
        '</map>\n')
    out_path = os.path.join(out_dir, f"level_{index:02d}.tmx")
    with open(out_path, "w") as f:
        f.write(xml)
    return out_path


def extract_tiled_maps(maphead_path: str, gamemaps_path: str, vswap_path: str,
                        out_dir: str) -> list[str]:
    build_plane0_tileset(vswap_path, out_dir)
    build_plane1_tileset(out_dir)
    with open(maphead_path, "rb") as f:
        maphead = mapfile.read_maphead(f.read())
    with open(gamemaps_path, "rb") as f:
        gamemaps = f.read()
    written = []
    for index, offset in enumerate(maphead.level_offsets):
        if offset <= 0:
            continue
        written.append(build_level_tmx(gamemaps, maphead, index, out_dir))
    return written


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--orig-data",
                         default=os.path.join(os.path.dirname(__file__), "..", "..", "..",
                                               "orig", "data"))
    parser.add_argument("--out",
                         default=os.path.join(os.path.dirname(__file__), "..", "..", "..",
                                               "build", "extracted"))
    args = parser.parse_args()

    vswap_path = os.path.join(args.orig_data, "VSWAP.WL1")
    maphead_path = os.path.join(args.orig_data, "MAPHEAD.WL1")
    gamemaps_path = os.path.join(args.orig_data, "GAMEMAPS.WL1")

    n = extract_tileset(vswap_path, args.out)
    print(f"wrote {n}-tile wall/door texture sheet -> {args.out}/wall_textures.png")

    levels = extract_levels(maphead_path, gamemaps_path, args.out)
    for path in levels:
        print(f"wrote {path}")

    tiled_dir = os.path.join(args.out, "tiled")
    os.makedirs(tiled_dir, exist_ok=True)
    tiled_paths = extract_tiled_maps(maphead_path, gamemaps_path, vswap_path, tiled_dir)
    print(f"wrote {tiled_dir}/plane0_tileset.tsx (+ .png)")
    print(f"wrote {tiled_dir}/plane1_tileset.tsx (+ .png)")
    for path in tiled_paths:
        print(f"wrote {path}")


if __name__ == "__main__":
    main()
