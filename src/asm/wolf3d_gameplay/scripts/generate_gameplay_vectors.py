#!/usr/bin/env python3
"""Generate durable JSON gameplay vectors from the independent oracle.

The JSON is intentionally straightforward to inspect and can be converted to
a packed eZ80 fixture once the assembly test ABI is frozen.  Directed records
come first, followed by deterministic randomized collision/ClipMove records.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import random

import gameplay_oracle as go


SEED = 0x574F4C46


def build_vectors(random_cases: int) -> dict[str, object]:
    vectors: list[dict[str, object]] = []

    def add_collision(
        name: str,
        tilemap: bytearray,
        doors: list[go.Door],
        pose: go.Pose,
        dx: int,
        dy: int,
    ) -> None:
        result, path = go.clip_move(tilemap, doors, pose, dx, dy)
        nonzero_tiles = [
            [index % 64, index // 64, value]
            for index, value in enumerate(tilemap)
            if value and index // 64 not in (0, 63) and index % 64 not in (0, 63)
        ]
        vectors.append(
            {
                "name": name,
                "pose": [pose.x, pose.y, pose.angle],
                "delta": [dx, dy],
                "map_patches": nonzero_tiles,
                "doors": [
                    [
                        door.tile_x,
                        door.tile_y,
                        int(door.vertical),
                        door.lock,
                        door.action,
                        door.position,
                        door.texture_id,
                    ]
                    for door in doors
                ],
                "expected_clear": go.player_position_clear(tilemap, doors, pose),
                "expected_pose": [result.x, result.y, result.angle],
                "expected_path": path,
            }
        )

    tilemap = go.empty_bordered_map()
    tilemap[10 * 64 + 11] = 1
    add_collision(
        "directed_wall_threshold_clear",
        tilemap,
        [],
        go.Pose(go.fixed(10, 0xA7FF), go.fixed(10)),
        1,
        0,
    )
    add_collision(
        "directed_wall_threshold_touch",
        tilemap,
        [],
        go.Pose(go.fixed(10, 0xA800), go.fixed(10)),
        0,
        0,
    )

    rng = random.Random(SEED)
    for sequence in range(random_cases):
        tilemap = go.empty_bordered_map()
        for _ in range(rng.randrange(1, 10)):
            x, y = rng.randrange(2, 62), rng.randrange(2, 62)
            tilemap[y * 64 + x] = rng.randrange(1, 0x80)
        pose = go.Pose(
            go.fixed(rng.randrange(2, 62), rng.randrange(0x10000)),
            go.fixed(rng.randrange(2, 62), rng.randrange(0x10000)),
            rng.randrange(360),
        )
        add_collision(
            f"random_{sequence:05d}",
            tilemap,
            [],
            pose,
            rng.randrange(-0x6000, 0x6001),
            rng.randrange(-0x6000, 0x6001),
        )

    return {
        "format": "wolf3d-ez80-gameplay-v1",
        "seed": SEED,
        "random_cases": random_cases,
        "vectors": vectors,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--random-cases", type=int, default=10_000)
    parser.add_argument("--output", type=Path, default=Path("gameplay_vectors.json"))
    args = parser.parse_args()
    payload = build_vectors(args.random_cases)
    args.output.write_text(json.dumps(payload, separators=(",", ":")) + "\n")
    print(f"wrote {len(payload['vectors'])} vectors to {args.output}")


if __name__ == "__main__":
    main()
