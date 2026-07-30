"""Compile a Tiled tileset/map set (as produced by extract.py) back into
MAPHEAD.WL1 / GAMEMAPS.WL1.

This is the reverse of extract.py's Tiled export and relies on the exact
same schema:
- plane0: GID == tile value directly (plane0_tileset.tsx, firstgid=1).
- plane1 actors/items/pushwall: GID == tile value + that tileset's
  (firstgid - 1) (plane1_tileset.tsx; firstgid read from the .tmx itself,
  not hard-coded, so it tolerates the tileset growing/shrinking).
- plane1 player-start markers (values 19-22): NOT in the plane1 tile layer
  (extract.py always zeroes those cells there) -- instead a `PlayerStart`
  point object with a `facing` (N/E/S/W) property on a `markers` object
  layer.

Also rebuilds VSWAP.WL1's wall/door textures from an edited copy of
extract.py's wall_textures.png sheet (pass --skip-textures to compile map
geometry only). VGA*.WL1/WOLF3D.EXE etc. still need to be copied alongside
the output from orig/data/ for the result to be a complete, runnable game
directory -- this tool doesn't touch those.

Usage: .venv/bin/python -m toolchain.cli.build [--tiled-dir DIR] [--out DIR]
       [--textures PNG] [--orig-vswap PATH] [--skip-textures]
"""
from __future__ import annotations

import argparse
import glob
import os
import re
import xml.etree.ElementTree as ET

from PIL import Image

from toolchain.cli.extract import TILESET_COLUMNS
from toolchain.formats import mapfile, vswap

# Inverse of extract.py's PLAYER_START_FACING.
FACING_TO_PLAYER_START = {"N": 19, "E": 20, "S": 21, "W": 22}

LEVEL_FILENAME_RE = re.compile(r"level_(\d+)\.tmx$")


def _parse_tile_layer(root: ET.Element, path: str, name: str, width: int, height: int
                       ) -> list[list[int]]:
    layer = root.find(f"./layer[@name='{name}']")
    if layer is None:
        raise ValueError(f"{path}: missing '{name}' tile layer")
    data_el = layer.find("data")
    if data_el is None or data_el.get("encoding") != "csv":
        raise ValueError(f"{path}: '{name}' layer must use CSV encoding")
    rows = [row.strip() for row in data_el.text.strip().splitlines()]
    if len(rows) != height:
        raise ValueError(f"{path}: expected {height} '{name}' rows, got {len(rows)}")
    grid = []
    for y, row in enumerate(rows):
        values = [int(v) for v in row.split(",") if v]
        if len(values) != width:
            raise ValueError(f"{path}: '{name}' row {y} has {len(values)} tiles, "
                              f"expected {width}")
        grid.append(values)
    return grid


def _tileset_firstgid(root: ET.Element, path: str, source_contains: str) -> int:
    for tileset in root.findall("tileset"):
        if source_contains in (tileset.get("source") or ""):
            return int(tileset.get("firstgid"))
    raise ValueError(f"{path}: no <tileset> referencing '{source_contains}'")


def _parse_level_tmx(path: str) -> tuple[int, mapfile.Level]:
    match = LEVEL_FILENAME_RE.search(os.path.basename(path))
    if not match:
        raise ValueError(f"{path}: filename doesn't match level_NN.tmx")
    index = int(match.group(1))

    root = ET.parse(path).getroot()
    width = int(root.get("width"))
    height = int(root.get("height"))
    if width != mapfile.MAP_WIDTH or height != mapfile.MAP_HEIGHT:
        raise ValueError(f"{path}: expected {mapfile.MAP_WIDTH}x{mapfile.MAP_HEIGHT} "
                          f"tiles, got {width}x{height}")

    plane0_firstgid = _tileset_firstgid(root, path, "plane0_tileset")
    if plane0_firstgid != 1:
        raise ValueError(f"{path}: expected plane0_tileset firstgid=1 (GID == "
                          f"plane0 tile value directly), got {plane0_firstgid}")
    plane1_firstgid = _tileset_firstgid(root, path, "plane1_tileset")

    name = f"Level {index}"
    for prop in root.findall("./properties/property"):
        if prop.get("name") == "levelName":
            name = prop.get("value")

    plane0 = _parse_tile_layer(root, path, "plane0", width, height)
    for y, row in enumerate(plane0):
        if any(v == 0 for v in row):
            raise ValueError(f"{path}: plane0 row {y} has an empty (GID 0) tile -- "
                              f"every cell needs a real wall/door/floor value")

    plane1_gids = _parse_tile_layer(root, path, "plane1", width, height)
    plane1 = [[0] * width for _ in range(height)]
    for y, row in enumerate(plane1_gids):
        for x, gid in enumerate(row):
            if gid == 0:
                continue
            value = gid - plane1_firstgid + 1
            if 19 <= value <= 22:
                raise ValueError(f"{path}: plane1 tile at ({x},{y}) is a raw "
                                  f"player-start code ({value}) -- use a PlayerStart "
                                  f"object on the 'markers' layer instead")
            plane1[y][x] = value

    markers = root.find("./objectgroup[@name='markers']")
    if markers is not None:
        for obj in markers.findall("object"):
            if obj.get("type") != "PlayerStart":
                continue
            facing = None
            for prop in obj.findall("./properties/property"):
                if prop.get("name") == "facing":
                    facing = prop.get("value")
            if facing not in FACING_TO_PLAYER_START:
                raise ValueError(f"{path}: PlayerStart object has invalid/missing "
                                  f"facing property: {facing!r}")
            tile_x = int(float(obj.get("x"))) // 64
            tile_y = int(float(obj.get("y"))) // 64
            if plane1[tile_y][tile_x] != 0:
                raise ValueError(f"{path}: cell ({tile_x},{tile_y}) has both a "
                                  f"PlayerStart object and a plane1 actor/item "
                                  f"tile -- a cell can only hold one plane1 value")
            plane1[tile_y][tile_x] = FACING_TO_PLAYER_START[facing]

    header = mapfile.LevelHeader(
        off_plane0=0, off_plane1=0, off_plane2=0,
        len_plane0=0, len_plane1=0, len_plane2=0,
        width=width, height=height, name=name)
    return index, mapfile.Level(header=header, plane0=plane0, plane1=plane1)


def build_wl1(tiled_dir: str, out_dir: str) -> tuple[str, str]:
    levels: dict[int, mapfile.Level] = {}
    for path in sorted(glob.glob(os.path.join(tiled_dir, "level_*.tmx"))):
        index, level = _parse_level_tmx(path)
        levels[index] = level
    if not levels:
        raise ValueError(f"no level_*.tmx files found in {tiled_dir}")

    gamemaps_body, maphead = mapfile.build_gamemaps(levels)

    os.makedirs(out_dir, exist_ok=True)
    maphead_path = os.path.join(out_dir, "MAPHEAD.WL1")
    gamemaps_path = os.path.join(out_dir, "GAMEMAPS.WL1")
    with open(maphead_path, "wb") as f:
        f.write(mapfile.write_maphead(maphead))
    with open(gamemaps_path, "wb") as f:
        f.write(gamemaps_body)
    return maphead_path, gamemaps_path


def build_vswap(textures_png_path: str, orig_vswap_path: str, out_path: str) -> str:
    """Re-encode an edited wall/door texture sheet (extract.py's
    wall_textures.png layout: TILESET_COLUMNS-wide grid, one tile per VSWAP
    chunk index 0..spritestart) back into VSWAP.WL1. Every other chunk --
    sprites, sounds, and any wall slot that was originally empty/unused --
    is copied byte-for-byte from orig_vswap_path, so this only ever touches
    real wall/door textures.
    """
    with open(orig_vswap_path, "rb") as f:
        orig = vswap.read_vswap(f.read())
    sheet = Image.open(textures_png_path).convert("RGB")
    size = vswap.TEXTURE_SIZE

    chunks = list(orig.chunks)
    for i in range(orig.spritestart):
        if not orig.chunks[i]:
            continue  # originally empty/unused wall-texture slot -- leave as-is
        x, y = (i % TILESET_COLUMNS) * size, (i // TILESET_COLUMNS) * size
        tile = sheet.crop((x, y, x + size, y + size))
        chunks[i] = vswap.image_to_chunk(tile)

    new_vswap = vswap.VSwapFile(numchunks=orig.numchunks, spritestart=orig.spritestart,
                                 soundstart=orig.soundstart, chunks=chunks)
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "wb") as f:
        f.write(vswap.write_vswap(new_vswap))
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tiled-dir",
                         default=os.path.join(os.path.dirname(__file__), "..", "..", "..",
                                               "build", "extracted", "tiled"))
    parser.add_argument("--out",
                         default=os.path.join(os.path.dirname(__file__), "..", "..", "..",
                                               "build", "wl1"))
    parser.add_argument("--textures",
                         default=os.path.join(os.path.dirname(__file__), "..", "..", "..",
                                               "build", "extracted", "wall_textures.png"),
                         help="edited copy of extract.py's wall_textures.png")
    parser.add_argument("--orig-vswap",
                         default=os.path.join(os.path.dirname(__file__), "..", "..", "..",
                                               "orig", "data", "VSWAP.WL1"),
                         help="original VSWAP.WL1 to copy sprite/sound chunks from")
    parser.add_argument("--skip-textures", action="store_true",
                         help="compile map geometry only, don't rebuild VSWAP.WL1")
    args = parser.parse_args()

    maphead_path, gamemaps_path = build_wl1(args.tiled_dir, args.out)
    print(f"wrote {maphead_path}")
    print(f"wrote {gamemaps_path}")

    if args.skip_textures:
        return
    if not (os.path.exists(args.textures) and os.path.exists(args.orig_vswap)):
        print(f"skipping VSWAP.WL1 rebuild ({args.textures} or {args.orig_vswap} not found)")
        return
    vswap_path = build_vswap(args.textures, args.orig_vswap, os.path.join(args.out, "VSWAP.WL1"))
    print(f"wrote {vswap_path}")


if __name__ == "__main__":
    main()
