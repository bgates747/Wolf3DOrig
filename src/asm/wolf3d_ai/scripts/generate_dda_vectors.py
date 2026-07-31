#!/usr/bin/env python3
"""Generate deterministic CheckLine/CheckSight regression vectors.

The oracle independently implements the written eZ80 contract: reduce valid
16.16 endpoints to 8.8 for ordinary-cell traversal, block on walls, and use
the original 16.16 segment for exact oriented door-center intersections.
"""

from __future__ import annotations

import argparse
import importlib.util
import random
import struct
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[1]
REPOSITORY = Path(__file__).resolve().parents[4]
SHARED_GENERATOR = REPOSITORY / "agonport/tools/gen_dda_fixture.py"

# op, expected, door position, 8 byte fields, four coordinates, sequence id.
RECORD = struct.Struct("<BBHBBBBBBBBiiiiI")
SEED = 0x574F4C46

OP_CHECK_LINE = 0
OP_CHECK_SIGHT = 1

DIR_EAST = 0
DIR_NORTHEAST = 1
DIR_NORTH = 2
DIR_NORTHWEST = 3
DIR_WEST = 4
DIR_SOUTHWEST = 5
DIR_SOUTH = 6
DIR_SOUTHEAST = 7
DIR_NODIR = 8

NO_PATCH = 0xFF
TILE_OPEN = 0x00
TILE_WALL = 0x01
TILE_DOOR = 0x80


def load_shared_map() -> bytes:
    spec = importlib.util.spec_from_file_location(
        "gen_dda_fixture", SHARED_GENERATOR
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {SHARED_GENERATOR}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    payload = module.build_map()
    if len(payload) != 4096:
        raise RuntimeError("shared map is not exactly 64x64 bytes")
    return payload


def fixed(tile: int, fraction: int = 0x8000) -> int:
    return (tile << 16) | fraction


def q8(value: int) -> int:
    if not 0 <= value < (64 << 16):
        raise ValueError(f"coordinate outside 64x64 map: {value}")
    return value >> 8


def trunc_div(numerator: int, denominator: int) -> int:
    quotient = abs(numerator) // denominator
    return -quotient if numerator < 0 else quotient


def slope8(minor_delta: int, major_distance: int) -> int:
    value = trunc_div(minor_delta << 8, major_distance)
    return max(-0x7FFF, min(0x7FFF, value))


def tile_at(
    tilemap: bytes,
    x: int,
    y: int,
    patch: tuple[int, int, int] | None,
) -> int:
    if patch is not None and (x, y) == patch[:2]:
        return patch[2]
    return tilemap[y * 64 + x]


def tile_blocks(
    value: int,
    *,
    tile_x: int,
    tile_y: int,
    actor_x: int,
    actor_y: int,
    player_x: int,
    player_y: int,
    configured_door_indices: frozenset[int],
    door_vertical: bool,
    door_position: int,
) -> bool:
    if value == TILE_OPEN:
        return False
    if 0x01 <= value <= 0x7F:
        return True
    if 0x80 <= value <= 0xBF:
        if (value & 0x7F) not in configured_door_indices:
            return True
        if door_vertical:
            major1, minor1 = actor_x, actor_y
            major2, minor2 = player_x, player_y
            plane = (tile_x << 16) + 0x8000
            expected_minor_tile = tile_y
        else:
            major1, minor1 = actor_y, actor_x
            major2, minor2 = player_y, player_x
            plane = (tile_y << 16) + 0x8000
            expected_minor_tile = tile_x
        if major1 > major2:
            major1, major2 = major2, major1
            minor1, minor2 = minor2, minor1
        if not major1 <= plane <= major2 or major1 == major2:
            return False
        intercept = minor1 + (
            (minor2 - minor1) * (plane - major1) // (major2 - major1)
        )
        if intercept >> 16 != expected_minor_tile:
            return False
        return (intercept & 0xFFFF) > door_position
    return True


def check_line(
    tilemap: bytes,
    actor_x: int,
    actor_y: int,
    player_x: int,
    player_y: int,
    *,
    door_vertical: bool,
    door_position: int,
    patch: tuple[int, int, int] | None = None,
) -> bool:
    x1, y1 = q8(actor_x), q8(actor_y)
    x2, y2 = q8(player_x), q8(player_y)
    if (x1, y1) > (x2, y2):
        x1, x2 = x2, x1
        y1, y2 = y2, y1
    xt1, yt1 = x1 >> 8, y1 >> 8
    xt2, yt2 = x2 >> 8, y2 >> 8
    configured_indices = {0}
    if patch is not None and 0x80 <= patch[2] <= 0xBF:
        configured_indices.add(patch[2] & 0x7F)
    configured_door_indices = frozenset(configured_indices)

    if xt1 != xt2:
        if xt2 > xt1:
            major_step = 1
            partial = 0x100 - (x1 & 0xFF)
        else:
            major_step = -1
            partial = x1 & 0xFF
        minor_step = slope8(y2 - y1, abs(x2 - x1))
        y_cross = y1 + ((minor_step * partial) >> 8)
        x = xt1 + major_step
        while True:
            value = tile_at(tilemap, x, y_cross >> 8, patch)
            if tile_blocks(
                value,
                tile_x=x,
                tile_y=y_cross >> 8,
                actor_x=actor_x,
                actor_y=actor_y,
                player_x=player_x,
                player_y=player_y,
                configured_door_indices=configured_door_indices,
                door_vertical=door_vertical,
                door_position=door_position,
            ):
                return False
            if x == xt2:
                break
            x += major_step
            y_cross += minor_step

    if yt1 != yt2:
        if yt2 > yt1:
            major_step = 1
            partial = 0x100 - (y1 & 0xFF)
        else:
            major_step = -1
            partial = y1 & 0xFF
        minor_step = slope8(x2 - x1, abs(y2 - y1))
        x_cross = x1 + ((minor_step * partial) >> 8)
        y = yt1 + major_step
        while True:
            value = tile_at(tilemap, x_cross >> 8, y, patch)
            if tile_blocks(
                value,
                tile_x=x_cross >> 8,
                tile_y=y,
                actor_x=actor_x,
                actor_y=actor_y,
                player_x=player_x,
                player_y=player_y,
                configured_door_indices=configured_door_indices,
                door_vertical=door_vertical,
                door_position=door_position,
            ):
                return False
            if y == yt2:
                break
            y += major_step
            x_cross += minor_step

    return True


def facing_accepts(direction: int, dx: int, dy: int) -> bool:
    if direction == DIR_EAST:
        return dx >= 0
    if direction == DIR_NORTHEAST:
        return dx - dy >= 0
    if direction == DIR_NORTH:
        return dy <= 0
    if direction == DIR_NORTHWEST:
        return dx + dy <= 0
    if direction == DIR_WEST:
        return dx <= 0
    if direction == DIR_SOUTHWEST:
        return dy - dx >= 0
    if direction == DIR_SOUTH:
        return dy >= 0
    if direction == DIR_SOUTHEAST:
        return dx + dy >= 0
    return True


def check_sight(
    tilemap: bytes,
    actor_x: int,
    actor_y: int,
    player_x: int,
    player_y: int,
    *,
    direction: int,
    area_connected: bool,
    made_noise: bool,
    door_vertical: bool,
    door_position: int,
    patch: tuple[int, int, int] | None = None,
) -> bool:
    if not area_connected:
        return False
    full_dx = player_x - actor_x
    full_dy = player_y - actor_y
    if -0x18000 < full_dx < 0x18000:
        if -0x18000 < full_dy < 0x18000:
            return True
    dx = q8(player_x) - q8(actor_x)
    dy = q8(player_y) - q8(actor_y)
    if not made_noise and not facing_accepts(direction, dx, dy):
        return False
    return check_line(
        tilemap,
        actor_x,
        actor_y,
        player_x,
        player_y,
        door_vertical=door_vertical,
        door_position=door_position,
        patch=patch,
    )


def is_open(tilemap: bytes, x: int, y: int) -> bool:
    return tilemap[y * 64 + x] == TILE_OPEN


def build_vectors(random_cases: int) -> list[bytes]:
    tilemap = load_shared_map()
    rng = random.Random(SEED)
    records: list[bytes] = []
    sequence = 0

    def add(
        op: int,
        actor_x: int,
        actor_y: int,
        player_x: int,
        player_y: int,
        *,
        door_position: int = 0,
        door_vertical: bool = True,
        direction: int = DIR_EAST,
        actor_area: int = 1,
        area_connected: bool = True,
        made_noise: bool = False,
        patch: tuple[int, int, int] | None = None,
    ) -> None:
        nonlocal sequence
        kwargs = dict(
            door_vertical=door_vertical,
            door_position=door_position,
            patch=patch,
        )
        if op == OP_CHECK_LINE:
            expected = check_line(
                tilemap, actor_x, actor_y, player_x, player_y, **kwargs
            )
        else:
            expected = check_sight(
                tilemap,
                actor_x,
                actor_y,
                player_x,
                player_y,
                direction=direction,
                area_connected=area_connected,
                made_noise=made_noise,
                **kwargs,
            )
        patch_x, patch_y, patch_value = (
            patch if patch is not None else (NO_PATCH, 0, 0)
        )
        records.append(
            RECORD.pack(
                op,
                int(expected),
                door_position,
                int(door_vertical),
                direction,
                actor_area,
                int(area_connected),
                int(made_noise),
                patch_x,
                patch_y,
                patch_value,
                actor_x,
                actor_y,
                player_x,
                player_y,
                sequence,
            )
        )
        sequence += 1

    # Exact central vertical-door threshold from the shared contract.
    west = (fixed(11), fixed(13))
    east = (fixed(15), fixed(13))
    for position in (0, 0x7FFF, 0x8000, 0x8001, 0xFFFF):
        add(OP_CHECK_LINE, *west, *east, door_position=position)
        add(OP_CHECK_LINE, *east, *west, door_position=position)
    add(
        OP_CHECK_LINE,
        *west,
        *east,
        door_position=0xFFFF,
        patch=(30, 30, TILE_DOOR | 1),
    )

    # Angled rays hit the door at its center plane, not its entry edge.
    angled_vertical = (
        fixed(27, 0x8000),
        fixed(29, 0),
        fixed(33, 0x8000),
        fixed(32, 0),
    )
    angled_horizontal = (
        fixed(29, 0),
        fixed(27, 0x8000),
        fixed(32, 0),
        fixed(33, 0x8000),
    )
    for position in (0x7FFF, 0x8000):
        for endpoints in (
            angled_vertical,
            angled_vertical[2:] + angled_vertical[:2],
        ):
            add(
                OP_CHECK_LINE,
                *endpoints,
                door_position=position,
                patch=(30, 30, TILE_DOOR),
            )
        for endpoints in (
            angled_horizontal,
            angled_horizontal[2:] + angled_horizontal[:2],
        ):
            add(
                OP_CHECK_LINE,
                *endpoints,
                door_position=position,
                door_vertical=False,
                patch=(30, 30, TILE_DOOR),
            )

    exact_door_cases = (
        # Preserve the full 0.16 fraction below the old 8.8 cutoff.
        (
            (fixed(27), fixed(30, 0x40FF), fixed(33), fixed(30, 0x40FF)),
            True,
            (30, 30, TILE_DOOR),
            0x4000,
        ),
        (
            (fixed(30, 0x40FF), fixed(27), fixed(30, 0x40FF), fixed(33)),
            False,
            (30, 30, TILE_DOOR),
            0x4000,
        ),
        # An odd 8.8 slope must classify identically in both directions.
        (
            (fixed(27), fixed(30, 0x1000), fixed(33), fixed(30, 0xF000)),
            True,
            (30, 30, TILE_DOOR),
            0x7FFF,
        ),
        (
            (fixed(30, 0x1000), fixed(27), fixed(30, 0xF000), fixed(33)),
            False,
            (30, 30, TILE_DOOR),
            0x7FFF,
        ),
        # Long shallow traces retain the original 16.16 endpoint delta.
        (
            (fixed(1), fixed(30, 0), fixed(62), fixed(30, 0x3C00)),
            True,
            (60, 30, TILE_DOOR),
            0x1000,
        ),
        (
            (fixed(30, 0), fixed(1), fixed(30, 0x3C00), fixed(62)),
            False,
            (30, 60, TILE_DOOR),
            0x1000,
        ),
        # A center plane that has left the door's row/column is clear.
        (
            (
                fixed(25, 0x2000),
                fixed(25, 0x2000),
                fixed(31, 0x2000),
                fixed(30, 0x2000),
            ),
            True,
            (30, 30, TILE_DOOR),
            0,
        ),
        (
            (
                fixed(25, 0x2000),
                fixed(25, 0x2000),
                fixed(30, 0x2000),
                fixed(31, 0x2000),
            ),
            False,
            (30, 30, TILE_DOOR),
            0,
        ),
    )
    for endpoints, vertical, patch, position in exact_door_cases:
        for ordered in (endpoints, endpoints[2:] + endpoints[:2]):
            add(
                OP_CHECK_LINE,
                *ordered,
                door_position=position,
                door_vertical=vertical,
                patch=patch,
            )

    # Exercise the complete 0..63 door-index offset range.
    for door_index in (1, 17, 63):
        add(
            OP_CHECK_LINE,
            fixed(27),
            fixed(30, 0x4000),
            fixed(33),
            fixed(30, 0x4000),
            door_position=0x4000,
            patch=(30, 30, TILE_DOOR | door_index),
        )

    # One-patch directed wall and both door orientations in open map space.
    for fraction in (0x0000, 0x2000, 0x7F00, 0x8000, 0xC000, 0xFF00):
        y = fixed(30, fraction)
        x = fixed(30, fraction)
        for position in (0, 0x3FFF, 0x4000, 0x7FFF, 0x8000, 0xFFFF):
            add(
                OP_CHECK_LINE,
                fixed(27),
                y,
                fixed(33),
                y,
                door_position=position,
                patch=(30, 30, TILE_DOOR),
            )
            add(
                OP_CHECK_LINE,
                x,
                fixed(27),
                x,
                fixed(33),
                door_position=position,
                door_vertical=False,
                patch=(30, 30, TILE_DOOR),
            )

    # Full-16.16, strict CheckSight proximity boundary.
    near_actor_x = fixed(30)
    near_actor_y = fixed(30)
    add(
        OP_CHECK_SIGHT,
        near_actor_x,
        near_actor_y,
        near_actor_x - 0x18000 + 1,
        near_actor_y,
        direction=DIR_EAST,
    )
    add(
        OP_CHECK_SIGHT,
        near_actor_x,
        near_actor_y,
        near_actor_x - 0x18000,
        near_actor_y,
        direction=DIR_EAST,
    )

    for op in (OP_CHECK_LINE, OP_CHECK_SIGHT):
        for _ in range(random_cases):
            targeted = rng.randrange(3)
            door_vertical = bool(rng.getrandbits(1))
            door_position = rng.randrange(0x10000)
            patch: tuple[int, int, int] | None
            if targeted == 0:
                # Force a wall/door crossing in an otherwise open region.
                px = rng.randrange(22, 52)
                py = rng.randrange(22, 52)
                patch_value = (
                    TILE_DOOR | rng.randrange(64)
                    if rng.getrandbits(1)
                    else TILE_WALL
                )
                patch = (px, py, patch_value)
                frac = rng.randrange(0x10000)
                span1 = rng.randrange(1, 8)
                span2 = rng.randrange(1, 8)
                if door_vertical:
                    actor_x, actor_y = fixed(px - span1), fixed(py, frac)
                    player_x, player_y = fixed(px + span2), fixed(py, frac)
                else:
                    actor_x, actor_y = fixed(px, frac), fixed(py - span1)
                    player_x, player_y = fixed(px, frac), fixed(py + span2)
            else:
                patch = None
                while True:
                    ax, ay = rng.randrange(1, 63), rng.randrange(1, 63)
                    px, py = rng.randrange(1, 63), rng.randrange(1, 63)
                    if is_open(tilemap, ax, ay) and is_open(tilemap, px, py):
                        break
                actor_x = fixed(ax, rng.randrange(0x10000))
                actor_y = fixed(ay, rng.randrange(0x10000))
                player_x = fixed(px, rng.randrange(0x10000))
                player_y = fixed(py, rng.randrange(0x10000))

            add(
                op,
                actor_x,
                actor_y,
                player_x,
                player_y,
                door_position=door_position,
                door_vertical=door_vertical,
                direction=rng.randrange(9),
                actor_area=rng.randrange(8),
                area_connected=bool(rng.getrandbits(1)),
                made_noise=bool(rng.getrandbits(1)),
                patch=patch,
            )

    records.sort(key=lambda record: record[0])
    return records


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output", type=Path, default=PROJECT / "tgt/dda_vectors.bin"
    )
    parser.add_argument("--random-cases", type=int, default=10_000)
    args = parser.parse_args()
    records = build_vectors(args.random_cases)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(struct.pack("<I", len(records)) + b"".join(records))
    print(f"wrote {len(records)} records ({RECORD.size} bytes each)")
    print(f"output: {args.output}")


if __name__ == "__main__":
    main()
