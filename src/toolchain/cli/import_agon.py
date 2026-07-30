"""Best-effort translator: AgonWolf3D MapMaker `.map` room -> a Tiled level
using THIS project's existing real-Wolf3D plane0/plane1 WL1 vocabulary
(reuses plane0_tileset.tsx/plane1_tileset.tsx from extract.py's output, so
translated rooms can be viewed/edited in Tiled right alongside real levels).

AgonWolf3D (a completely separate sibling project) is a different genre of
game than classic Wolf3D even though it borrows the name and aesthetic: its
levels are independent 15x15 "rooms" linked by a room-transition graph (not
one continuous 64x64 grid), it has no difficulty tiers, no door lock types,
and only 3 enemy types. This translation is explicitly LOSSY and best-effort
(per Author decision, 2026-07-30) -- every simplification/approximation is
called out below. It is NOT intended to reproduce Agon's room-link gameplay;
"go to another room" cells become ordinary in-place doors that lead nowhere.

Each room is embedded, alone, in a real 64x64 WL1 canvas: Agon's compiled
16x16 shape (15x15 authored cells + a synthesized "outer" boundary row/col,
matching AgonWolf3D's own MapMaker import step) sits in the top-left corner;
everything else is filled with solid wall so the level stays enclosed. That
means the output CAN be round-tripped through build.py into a real,
bootable (if mostly empty) WL1 level -- useful for a quick look, not a
faithful port.

Usage: .venv/bin/python -m toolchain.cli.import_agon --map PATH/TO/00_0.map
       [--tiles-catalog PATH/TO/tiles.txt] [--out-dir build/extracted/tiled]
"""
from __future__ import annotations

import argparse
import os
from xml.sax.saxutils import escape

from toolchain.cli.extract import PLANE1_GID_OFFSET
from toolchain.formats import agonmap, mapfile

DEFAULT_TILES_CATALOG = os.path.expanduser(
    "~/Agon/mystuff/AgonWolf3D/src/mapmaker/tiles.txt")

AGON_ROOM_SIZE = agonmap.GRID_SIZE  # 15 (authored); compiled shape is 16x16
OUTER_BOUNDARY_AGON_ID = 10  # "LIGHT GREY WALL", tiles.txt special="outer"

# Active AgonWolf3D wall IDs -> arbitrary distinct real WL1 wall texture
# values 1-9. No true texture correspondence exists (different games'
# textures); this only keeps each Agon wall type visually distinguishable.
WALL_MAP = {10: 1, 11: 2, 12: 3, 13: 4, 14: 5, 15: 6, 16: 7, 17: 8, 19: 9}

FLOOR_TILE = 107  # AREATILE -- one generic open-floor/area code for the room

# Decorations/items/pickups -> nearest-analog real Wolf3D plane1 static-item
# code (see extract.py's STATIC_NAMES, grounded in WL_ACT1.C's statinfo[]).
STATIC_ITEM_MAP = {
    20: 26,  # LAMP -> floor lamp
    21: 24,  # BARREL -> green barrel
    22: 25,  # TABLE -> table/chairs
    23: 37,  # OVERHEAD LIGHT -> ceiling light
    24: 58,  # RADIOACTIVE BARREL -> barrel2 (2nd generic barrel)
    40: 48,  # HEALTH PACK -> first aid
    41: 53,  # GOLD CHALISE -> chalice
    42: 52,  # GOLD CROSS -> cross
    43: 47,  # PLATE OF FOOD -> good food
    44: 49,  # KEYCARD -> clip (functional match: ammo, not a real key)
    45: 55,  # GOLD CHEST -> crown (treasure flavor)
    46: 50,  # MACHINE GUN -> machine gun
    47: 51,  # GATLING GUN -> chaingun
    48: 29,  # DOG FOOD -> bad food (thematically "food", not literally poison)
    49: 43,  # GOLD KEY -> key1
}

# Enemies -> plane1 "stand, facing north, easy tier" (Agon enemies have no
# patrol paths or difficulty tiers, so there's no real analog for those axes).
ENEMY_MAP = {
    50: 134,  # DOG -> dog stand N
    51: 108,  # GERMAN TROOPER -> guard stand N
    52: 126,  # SS GUARD -> SS stand N
}
DEAD_GUARD_AGON_ID = 56
DEAD_GUARD_PLANE1 = 124

REGULAR_DOOR_AGON_ID = 57
ELEVATOR_SWITCH_AGON_ID = 58
ELEVATOR_SWITCH_PLANE0 = 21  # ELEVATORTILE -- closest real analog (a solid,
                             # interactive wall tile), even though Agon's
                             # switch doesn't actually change levels.
ELEVATOR_DOOR_AGON_ID = 59
ROOM_LINK_AGON_IDS = set(range(30, 40))  # "to room N" -- destination is lost

# (even/vertical value, odd/horizontal value) per door kind.
DOOR_VALUE_PAIRS = {
    REGULAR_DOOR_AGON_ID: (90, 91),
    ELEVATOR_DOOR_AGON_ID: (100, 101),
}
# Room-link doors have no real lock-type analog; treated as plain doors.
for _room_link_id in ROOM_LINK_AGON_IDS:
    DOOR_VALUE_PAIRS[_room_link_id] = (90, 91)

START_AGON_ID = 28
FLOOR_LIKE_AGON_IDS = {25, 26, 27, 29}  # BJ 25/50/75% (UI, "avoid" per docs) + grey floor


def _is_wall_neighbor(grid: list[list[int]], x: int, y: int) -> bool:
    if not (0 <= x < AGON_ROOM_SIZE and 0 <= y < AGON_ROOM_SIZE):
        return True  # room edge: treated as enclosed
    obj_id = grid[y][x]
    return obj_id in WALL_MAP


def _door_orientation(grid: list[list[int]], x: int, y: int) -> str:
    """Heuristic only -- AgonWolf3D doesn't record door orientation.
    Vertical (even) if the door's north/south neighbors are walls (i.e. the
    door itself opens east-west); horizontal (odd) otherwise."""
    north_wall = _is_wall_neighbor(grid, x, y - 1)
    south_wall = _is_wall_neighbor(grid, x, y + 1)
    return "V" if (north_wall and south_wall) else "H"


def _classify_cell(obj_id: int, x: int, y: int, grid: list[list[int]]
                    ) -> tuple[int, int, str | None]:
    """Returns (plane0_value, plane1_value, player_start_facing_or_None)."""
    if obj_id in WALL_MAP:
        return WALL_MAP[obj_id], 0, None
    if obj_id in DOOR_VALUE_PAIRS:
        even, odd = DOOR_VALUE_PAIRS[obj_id]
        value = even if _door_orientation(grid, x, y) == "V" else odd
        return value, 0, None
    if obj_id == ELEVATOR_SWITCH_AGON_ID:
        return ELEVATOR_SWITCH_PLANE0, 0, None
    if obj_id == START_AGON_ID:
        return FLOOR_TILE, 0, "N"  # Agon can't encode starting orientation
    if obj_id in FLOOR_LIKE_AGON_IDS:
        return FLOOR_TILE, 0, None
    if obj_id in STATIC_ITEM_MAP:
        return FLOOR_TILE, STATIC_ITEM_MAP[obj_id], None
    if obj_id in ENEMY_MAP:
        return FLOOR_TILE, ENEMY_MAP[obj_id], None
    if obj_id == DEAD_GUARD_AGON_ID:
        return FLOOR_TILE, DEAD_GUARD_PLANE1, None
    print(f"warning: unrecognized/placeholder Agon object id {obj_id} at "
          f"({x},{y}) -- treating as generic wall")
    return WALL_MAP[OUTER_BOUNDARY_AGON_ID], 0, None


def build_room_tmx(map_path: str, out_dir: str, level_name: str | None = None) -> str:
    agon_map = agonmap.read_agon_map(map_path)
    width, height = mapfile.MAP_WIDTH, mapfile.MAP_HEIGHT
    outer_wall = WALL_MAP[OUTER_BOUNDARY_AGON_ID]

    plane0 = [[outer_wall] * width for _ in range(height)]
    plane1 = [[0] * width for _ in range(height)]
    player_start_facing = None
    player_start_xy = None

    for y in range(AGON_ROOM_SIZE):
        for x in range(AGON_ROOM_SIZE):
            obj_id = agon_map.grid[y][x]
            p0, p1, facing = _classify_cell(obj_id, x, y, agon_map.grid)
            plane0[y][x] = p0
            plane1[y][x] = p1
            if facing is not None:
                if player_start_facing is not None:
                    raise ValueError(f"{map_path}: more than one start object (28) found")
                player_start_facing, player_start_xy = facing, (x, y)
    # Compiled room's synthesized "outer" boundary row/col (index 15).
    for i in range(AGON_ROOM_SIZE + 1):
        plane0[AGON_ROOM_SIZE][i] = outer_wall
        plane0[i][AGON_ROOM_SIZE] = outer_wall

    # Per AgonWolf3D's own docs, only room 0 of a floor is required to hold
    # a start object (28) -- other rooms are reached via room-link doors, so
    # this translator leaves the markers layer empty for those (no error).
    objects = ""
    if player_start_facing is not None:
        px, py = player_start_xy
        objects = (
            f'  <object id="1" name="PlayerStart" type="PlayerStart" '
            f'x="{px * 64}" y="{py * 64}" width="64" height="64">\n'
            f'   <properties>\n'
            f'    <property name="facing" value="{player_start_facing}"/>\n'
            f'   </properties>\n'
            f'  </object>\n')

    plane0_csv = ",\n".join(",".join(str(v) for v in row) for row in plane0)
    plane1_csv = ",\n".join(
        ",".join(str(0 if v == 0 else v + PLANE1_GID_OFFSET) for v in row) for row in plane1)

    stem = os.path.splitext(os.path.basename(map_path))[0]
    level_name = level_name or f"AgonWolf3D {stem}"
    level_name_xml = escape(level_name, {'"': "&quot;"})
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<map version="1.10" tiledversion="1.12.2" orientation="orthogonal" '
        f'renderorder="right-down" width="{width}" height="{height}" tilewidth="64" '
        f'tileheight="64" infinite="0" nextlayerid="4" nextobjectid="2">\n'
        f' <properties>\n'
        f'  <property name="levelName" value="{level_name_xml}"/>\n'
        f' </properties>\n'
        f' <tileset firstgid="1" source="plane0_tileset.tsx"/>\n'
        f' <tileset firstgid="{PLANE1_GID_OFFSET + 1}" source="plane1_tileset.tsx"/>\n'
        f' <layer id="1" name="plane0" width="{width}" height="{height}">\n'
        f'  <data encoding="csv">\n{plane0_csv}\n</data>\n'
        f' </layer>\n'
        f' <layer id="2" name="plane1" width="{width}" height="{height}">\n'
        f'  <data encoding="csv">\n{plane1_csv}\n</data>\n'
        f' </layer>\n'
        f' <objectgroup id="3" name="markers">\n{objects} </objectgroup>\n'
        '</map>\n')

    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"agon_{stem}.tmx")
    with open(out_path, "w") as f:
        f.write(xml)
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--map", required=True, help="path to an AgonWolf3D .map room file")
    parser.add_argument("--tiles-catalog", default=DEFAULT_TILES_CATALOG,
                         help="path to AgonWolf3D's src/mapmaker/tiles.txt")
    parser.add_argument("--out-dir",
                         default=os.path.join(os.path.dirname(__file__), "..", "..", "..",
                                               "build", "extracted", "tiled"))
    args = parser.parse_args()

    # Catalog is read for validation/reference even though the current
    # hard-coded mapping tables above don't consult it dynamically yet.
    agonmap.read_tile_catalog(args.tiles_catalog)
    out_path = build_room_tmx(args.map, args.out_dir)
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
