"""Reader for AgonWolf3D's MapMaker `.map` room files and `tiles.txt` object
catalog (a completely different, sibling project living at
~/Agon/mystuff/AgonWolf3D -- a from-scratch eZ80/ESP32 engine with discrete,
graph-linked 15x15 rooms, not the classic 64x64 Wolf3D grid).

Format grounded directly in that project's own docs
(docs/map-design-manual/appendix-b-map-build-format.md) and verified against
a real sample file's raw bytes:

- Header: 4 records (max X index, max Y index, standard bank count, custom
  bank count -- normally 14, 14, 5, 0).
- Grid: 225 records, one per cell of a 15x15 grid (indices 0-14), stored
  Y-major/X-minor (BBC BASIC's save loop walks the array's first dimension
  outside the second, and that first dimension is semantically Y per the
  `the_map%(YCORD%,XCORD%)` convention used throughout mapmaker.bas).
- Every record (header or grid) is a small nonnegative integer written by
  BBC BASIC's PRINT#: little-endian, padded to 5 bytes.

Custom-bank records (if custom bank count > 0) may follow; Wolf3D itself
never uses them, and this reader doesn't parse them.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass

RECORD_SIZE = 5
GRID_SIZE = 15  # authored indices 0-14; the compiled room adds a 15th
                # row/col of "outer" boundary wall (not stored in the file).


@dataclass
class AgonMap:
    max_x: int
    max_y: int
    standard_banks: int
    custom_banks: int
    grid: list[list[int]]  # grid[y][x], authored 15x15 (indices 0-14)


def _read_record(data: bytes, offset: int) -> int:
    value = struct.unpack_from("<I", data, offset)[0]
    if data[offset + 4] != 0:
        raise ValueError(f"unexpected non-zero 5th byte at offset {offset}")
    return value


def read_agon_map(path: str) -> AgonMap:
    with open(path, "rb") as f:
        data = f.read()
    max_x = _read_record(data, 0)
    max_y = _read_record(data, 5)
    standard_banks = _read_record(data, 10)
    custom_banks = _read_record(data, 15)
    if max_x != GRID_SIZE - 1 or max_y != GRID_SIZE - 1:
        raise ValueError(f"{path}: expected a {GRID_SIZE}x{GRID_SIZE} room "
                          f"(max index {GRID_SIZE - 1}), got max_x={max_x} max_y={max_y}")
    grid = [[0] * GRID_SIZE for _ in range(GRID_SIZE)]
    offset = 20
    for y in range(GRID_SIZE):
        for x in range(GRID_SIZE):
            grid[y][x] = _read_record(data, offset)
            offset += RECORD_SIZE
    return AgonMap(max_x=max_x, max_y=max_y, standard_banks=standard_banks,
                   custom_banks=custom_banks, grid=grid)


@dataclass
class TileInfo:
    obj_id: int
    name: str
    is_active: bool
    is_door: bool
    is_wall: bool
    is_trigger: bool
    is_blocking: bool
    render_type: str
    special: str


def _unquote(field: str) -> str:
    field = field.strip()
    if len(field) >= 2 and field[0] == '"' and field[-1] == '"':
        return field[1:-1]
    return field


def read_tile_catalog(path: str) -> dict[int, TileInfo]:
    with open(path) as f:
        lines = [line.rstrip("\n") for line in f]
    header = lines[0].split("\t")
    col = {name: i for i, name in enumerate(header)}
    catalog: dict[int, TileInfo] = {}
    for line in lines[1:]:
        if not line.strip():
            continue
        fields = line.split("\t")
        obj_id = int(fields[col["obj_id"]])
        catalog[obj_id] = TileInfo(
            obj_id=obj_id,
            name=_unquote(fields[col["tile_name"]]),
            is_active=fields[col["is_active"]] == "1",
            is_door=fields[col["is_door"]] == "1",
            is_wall=fields[col["is_wall"]] == "1",
            is_trigger=fields[col["is_trigger"]] == "1",
            is_blocking=fields[col["is_blocking"]] == "1",
            render_type=_unquote(fields[col["render_type"]]),
            special=_unquote(fields[col["special"]]) if col["special"] < len(fields) else "",
        )
    return catalog
