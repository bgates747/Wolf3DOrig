#!/usr/bin/env python3
"""Generate runtime W3L1 state packages for every WL1 level/difficulty."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from formats import actorinfo, mapfile  # noqa: E402
from formats.level_package import LevelPackage, build_package  # noqa: E402
from scripts import gen_render_fixture as fixture  # noqa: E402

TILE_GLOBAL = fixture.TILE_GLOBAL
W3D_SLOT_NONE = fixture.W3D_SLOT_NONE

PROJECT_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_DATA_DIR = PROJECT_ROOT / "orig/data"
DEFAULT_OUT_DIR = PROJECT_ROOT / "agonport/assets/generated/wolf3d/levels"


def _le16(value: int) -> bytes:
    return int(value).to_bytes(2, "little", signed=False)


def _le32(value: int) -> bytes:
    return int(value).to_bytes(4, "little", signed=False)


def build_one(level: mapfile.Level, level_index: int, difficulty: actorinfo.Difficulty) -> bytes:
    tilemap, doors = fixture.build_tilemap_and_doors(level.plane0)
    statics, blocking = fixture.build_statics(level.plane1)
    actors = fixture.build_actors(level.plane0, level.plane1, difficulty)
    areas = fixture.build_area_map(level.plane0)
    paths = fixture.build_path_directions(level.plane1)
    tilex, tiley, angle = fixture.find_player_start(level.plane1)
    player_pose = _le32(tilex * TILE_GLOBAL + TILE_GLOBAL // 2)
    player_pose += _le32(tiley * TILE_GLOBAL + TILE_GLOBAL // 2) + _le16(angle)

    door_bytes = bytearray()
    for x, y, vertical, lock, texture_id, area1, area2 in doors:
        door_bytes.extend((x, y, int(vertical), lock, 0, 0, 0, texture_id, area1, area2))
    static_bytes = bytearray()
    for x, y, shape, flags, item in statics:
        static_bytes.extend((x, y))
        static_bytes.extend(int(shape).to_bytes(2, "little", signed=True))
        static_bytes.extend((flags, item))
    actor_bytes = bytearray()
    ticcounts = actorinfo.initial_ticcounts(actors)
    for index, (actor, ticcount) in enumerate(zip(actors, ticcounts), start=1):
        actor_bytes.extend(
            fixture.pack_actor_runtime(
                actor,
                index + 1 if index < len(actors) else W3D_SLOT_NONE,
                index - 1 if index > 1 else W3D_SLOT_NONE,
                ticcount,
            )
        )
    package = LevelPackage(
        level=level_index,
        difficulty=int(difficulty),
        door_count=len(doors),
        static_count=len(statics),
        actor_count=len(actors),
        random_index=actorinfo.random_index_after_initial_ticcounts(actors),
        player_pose=player_pose,
        sections={
            "doors": bytes(door_bytes),
            "statics": bytes(static_bytes),
            "actors": bytes(actor_bytes),
            "blocking": blocking,
            "areas": areas,
            "paths": paths,
            "tilemap": tilemap,
        },
    )
    return build_package(package)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    args = parser.parse_args()
    maphead = mapfile.read_maphead((args.data_dir / "MAPHEAD.WL1").read_bytes())
    gamemaps = (args.data_dir / "GAMEMAPS.WL1").read_bytes()
    for level_index, offset in enumerate(maphead.level_offsets):
        if offset <= 0:
            continue
        level = mapfile.read_level(gamemaps, maphead, level_index, maphead.magic)
        level_dir = args.out_dir / f"level_{level_index:02d}"
        level_dir.mkdir(parents=True, exist_ok=True)
        for difficulty in actorinfo.Difficulty:
            payload = build_one(level, level_index, difficulty)
            name = difficulty.name.lower()
            output = level_dir / f"state_{name}.w3l"
            output.write_bytes(payload)
            print(f"{output}: {len(payload)} bytes")


if __name__ == "__main__":
    main()
