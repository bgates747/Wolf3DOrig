"""Compile a Tiled tileset/map set (as produced by extract.py) back into
MAPHEAD.WL1 / GAMEMAPS.WL1.

This is the reverse of extract.py's Tiled export and relies on the exact
same schema: GID == plane0 tile value directly (tileset firstgid=1, so no
lookup table is needed), and player-start markers are `PlayerStart` point
objects carrying a `facing` (N/E/S/W) property on a `markers` object layer.

Note: this only compiles the map data. VSWAP.WL1/VGA*.WL1 etc. still need
to be copied alongside the output from orig/data/ for the result to be a
complete, runnable game directory -- this tool doesn't touch textures.

Usage: .venv/bin/python -m toolchain.cli.build [--tiled-dir DIR] [--out DIR]
"""
from __future__ import annotations

import argparse
import glob
import os
import re
import xml.etree.ElementTree as ET

from toolchain.formats import mapfile

# Inverse of extract.py's PLAYER_START_FACING.
FACING_TO_PLAYER_START = {"N": 19, "E": 20, "S": 21, "W": 22}

LEVEL_FILENAME_RE = re.compile(r"level_(\d+)\.tmx$")


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

    tileset = root.find("tileset")
    if tileset is not None and tileset.get("firstgid") != "1":
        raise ValueError(f"{path}: expected tileset firstgid=1 (GID == plane0 "
                          f"tile value directly), got {tileset.get('firstgid')}")

    name = f"Level {index}"
    for prop in root.findall("./properties/property"):
        if prop.get("name") == "levelName":
            name = prop.get("value")

    layer = root.find("./layer[@name='plane0']")
    if layer is None:
        raise ValueError(f"{path}: missing 'plane0' tile layer")
    data_el = layer.find("data")
    if data_el is None or data_el.get("encoding") != "csv":
        raise ValueError(f"{path}: 'plane0' layer must use CSV encoding")
    rows = [row.strip() for row in data_el.text.strip().splitlines()]
    if len(rows) != height:
        raise ValueError(f"{path}: expected {height} plane0 rows, got {len(rows)}")
    plane0 = []
    for y, row in enumerate(rows):
        values = [int(v) for v in row.split(",") if v]
        if len(values) != width:
            raise ValueError(f"{path}: row {y} has {len(values)} tiles, expected {width}")
        if any(v == 0 for v in values):
            raise ValueError(f"{path}: row {y} has an empty (GID 0) plane0 tile -- "
                              f"every cell needs a real wall/door/floor value")
        plane0.append(values)

    plane1 = [[0] * width for _ in range(height)]
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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tiled-dir",
                         default=os.path.join(os.path.dirname(__file__), "..", "..", "..",
                                               "build", "extracted", "tiled"))
    parser.add_argument("--out",
                         default=os.path.join(os.path.dirname(__file__), "..", "..", "..",
                                               "build", "wl1"))
    args = parser.parse_args()

    maphead_path, gamemaps_path = build_wl1(args.tiled_dir, args.out)
    print(f"wrote {maphead_path}")
    print(f"wrote {gamemaps_path}")


if __name__ == "__main__":
    main()
