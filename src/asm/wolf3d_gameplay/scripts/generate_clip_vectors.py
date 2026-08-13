#!/usr/bin/env python3
"""Generate packed vectors for the eZ80 ClipMove emulator regression."""

from __future__ import annotations

import argparse
from pathlib import Path
import random
import struct

import gameplay_oracle as go


SEED = 0x434C4950
NO_PATCH = 0xFF
PATCH_MAP = 0
PATCH_STATIC = 1
# Keep the established 40-byte ABI. Byte 36, formerly padding, now carries
# the patched door orientation (1 vertical, 0 horizontal); bytes 37..39 remain
# padding. All earlier field offsets are unchanged.
RECORD = struct.Struct("<BBBBBHBii3s3siiBBIB3s")


def signed24(value: int) -> bytes:
    if not -(1 << 23) <= value < (1 << 23):
        raise ValueError(value)
    return (value & 0xFFFFFF).to_bytes(3, "little")


def build_vectors(random_cases: int, *, include_zero_delta: bool) -> list[bytes]:
    records: list[bytes] = []

    def add(
        pose: go.Pose,
        dx: int,
        dy: int,
        patch: tuple[int, int, int] | None = None,
        patch_kind: int = PATCH_MAP,
        door_action: int = go.DOOR_CLOSED,
        door_position: int = 0,
        door_vertical: bool = True,
    ) -> None:
        tilemap = go.empty_bordered_map()
        static_bits = go.empty_static_blocking_bits()
        doors: list[go.Door] = []
        patch_x, patch_y, patch_value = NO_PATCH, 0, 0
        if patch is not None:
            patch_x, patch_y, patch_value = patch
            if patch_kind == PATCH_STATIC:
                go.set_static_blocked(static_bits, patch_x, patch_y)
            else:
                tilemap[patch_y * 64 + patch_x] = patch_value
            if patch_kind == PATCH_MAP and 0x80 <= patch_value <= 0xBF:
                count = (patch_value & 0x7F) + 1
                doors = [go.Door(0, 0, True, 0) for _ in range(count)]
                doors[-1] = go.Door(
                    patch_x,
                    patch_y,
                    door_vertical,
                    0,
                    action=door_action,
                    position=door_position,
                )
        result, _ = go.clip_move(tilemap, doors, pose, dx, dy, static_bits)
        expected_a = int((result.x, result.y) != (pose.x, pose.y))
        expected_dirty = expected_a
        records.append(
            RECORD.pack(
                patch_kind,
                patch_x,
                patch_y,
                patch_value,
                door_action,
                door_position,
                expected_a,
                pose.x,
                pose.y,
                signed24(dx),
                signed24(dy),
                result.x,
                result.y,
                expected_dirty,
                int(go.player_position_clear(tilemap, doors, pose,
                                             static_blocking_bits=static_bits)),
                len(records),
                int(door_vertical),
                b"\0" * 3,
            )
        )

    # Exact wall-contact boundary and each ClipMove outcome.
    wall = (11, 10, 1)
    add(go.Pose(go.fixed(10, 0xB7FF), go.fixed(10)), 1, 0, wall)
    add(go.Pose(go.fixed(10, 0xB800), go.fixed(10)), -1, 0, wall)
    # The bit plane remains the broad phase, but a dense slot lookup resolves
    # centered blocking statics for the exact 0x4800 narrow-phase boundary.
    add(go.Pose(go.fixed(11, 0x37FF), go.fixed(10)), 1, 0, wall, PATCH_STATIC)
    add(go.Pose(go.fixed(11, 0x3800), go.fixed(10)), -1, 0, wall, PATCH_STATIC)
    add(go.Pose(go.fixed(10), go.fixed(10)), 0x2000, 0xB800,
        (10, 11, 1), PATCH_STATIC)
    add(go.Pose(go.fixed(10), go.fixed(10)), 0xB800, 0x2000,
        (11, 10, 1), PATCH_STATIC)
    add(go.Pose(go.fixed(10), go.fixed(10)), 0x4000, 0x4000, (11, 11, 1))
    add(go.Pose(go.fixed(10), go.fixed(10)), 0x2000, 0x4000, (10, 11, 1))
    add(go.Pose(go.fixed(10), go.fixed(10)), 0x4000, 0x2000, (11, 10, 1))
    add(go.Pose(go.fixed(10), go.fixed(10)), 0x4000, 0x4000, (11, 10, 1))
    # Exercise the harness's physical bottom border explicitly. ez80asm
    # evaluates mixed +/* expressions left-to-right, so this guards the
    # literal row-63 setup in gameplay_regression.asm as well as ClipMove.
    add(go.Pose(go.fixed(10), go.fixed(62)), 0, 0xA800)
    # Door cells are traversable wells containing a center-plane slab. The
    # following vectors pin inclusive plane contact from either side, escape
    # from contact, well entry, and the renderer's exact gap/panel boundary.
    door_patch = (11, 10, 0x80)
    vertical_plane = go.fixed(11)
    panel_y = go.fixed(10)
    add(
        go.Pose(vertical_plane - go.PLAYER_RADIUS - 1, panel_y),
        1, 0, door_patch,
    )
    add(
        go.Pose(vertical_plane - go.PLAYER_RADIUS, panel_y),
        -1, 0, door_patch,
    )
    add(
        go.Pose(vertical_plane + go.PLAYER_RADIUS + 1, panel_y),
        -1, 0, door_patch,
    )
    add(
        go.Pose(vertical_plane + go.PLAYER_RADIUS, panel_y),
        1, 0, door_patch,
    )
    # Cross each tile boundary into the closed door well without reaching its
    # center plane. A tile-wide door implementation rejects both vectors.
    add(go.Pose(go.fixed(10, 0xB7FF), panel_y), 1, 0, door_patch)
    add(go.Pose(go.fixed(12, 0x4800), panel_y), -1, 0, door_patch)
    # A player centered on the closed plane is blocked even for nonzero motion.
    add(go.Pose(vertical_plane, panel_y), 1, 0, door_patch)
    # At p=C000, q=C000 is still gap and q=C001 is first panel.
    add(
        go.Pose(vertical_plane - go.PLAYER_RADIUS - 1,
                go.fixed(10, 0x7800)),
        1, 0, door_patch, door_position=0xC000,
    )
    add(
        go.Pose(vertical_plane - go.PLAYER_RADIUS - 1,
                go.fixed(10, 0x7801)),
        1, 0, door_patch, door_position=0xC000,
    )
    # The final q=FFFF endpoint blocks at p=FFFE; p=FFFF has no panel,
    # independently of the action label.
    add(
        go.Pose(vertical_plane - go.PLAYER_RADIUS - 1,
                go.fixed(10, 0xB7FF)),
        1, 0, door_patch,
        door_action=go.DOOR_OPENING, door_position=0xFFFE,
    )
    add(
        go.Pose(vertical_plane - go.PLAYER_RADIUS - 1,
                go.fixed(10, 0xB7FF)),
        1, 0, door_patch,
        door_action=go.DOOR_CLOSING, door_position=0xFFFF,
    )

    # Horizontal doors swap axes but retain the same unmirrored fraction rule.
    horizontal_plane = go.fixed(10)
    panel_x = go.fixed(11)
    add(
        go.Pose(panel_x, horizontal_plane - go.PLAYER_RADIUS - 1),
        0, 1, door_patch, door_vertical=False,
    )
    add(
        go.Pose(panel_x, horizontal_plane + go.PLAYER_RADIUS + 1),
        0, -1, door_patch, door_vertical=False,
    )
    add(
        go.Pose(go.fixed(11, 0x7800),
                horizontal_plane - go.PLAYER_RADIUS - 1),
        0, 1, door_patch, door_position=0xC000, door_vertical=False,
    )
    add(
        go.Pose(go.fixed(11, 0x7801),
                horizontal_plane - go.PLAYER_RADIUS - 1),
        0, 1, door_patch, door_position=0xC000, door_vertical=False,
    )
    add(
        go.Pose(panel_x, go.fixed(9, 0xB7FF)),
        0, 1, door_patch, door_vertical=False,
    )
    if include_zero_delta:
        # The routine's stated A/dirty contract says unchanged coordinates
        # return zero. This catches a successful-zero-vector implementation.
        add(go.Pose(go.fixed(10), go.fixed(10)), 0, 0)

    rng = random.Random(SEED)
    for _ in range(random_cases):
        pose = go.Pose(
            # The public gameplay contract assumes the current player pose is
            # valid. Keeping the center in tiles 2..61 guarantees its 0x5800
            # AABB does not already overlap the solid perimeter.
            go.fixed(rng.randrange(2, 62), rng.randrange(0x10000)),
            go.fixed(rng.randrange(2, 62), rng.randrange(0x10000)),
            rng.randrange(360),
        )
        dx = rng.randrange(-0x6000, 0x6001)
        dy = rng.randrange(-0x6000, 0x6001)
        if dx == 0 and dy == 0:
            dx = 1
        destination = go.Pose(pose.x + dx, pose.y + dy)
        x_low, x_high, y_low, y_high = go.player_bounds(destination)
        candidates = [
            (x, y)
            for y in range(max(1, y_low - 1), min(62, y_high + 1) + 1)
            for x in range(max(1, x_low - 1), min(62, x_high + 1) + 1)
        ]
        patch = None
        patch_kind = PATCH_MAP
        door_action = go.DOOR_CLOSED
        door_position = 0
        door_vertical = True
        if candidates and rng.randrange(4) != 0:
            patch_x, patch_y = rng.choice(candidates)
            if rng.randrange(5) == 0:
                patch_value = 0x80
                door_action = rng.randrange(4)
                door_position = rng.randrange(0x10000)
                door_vertical = bool(rng.getrandbits(1))
                if rng.randrange(8) == 0:
                    door_action, door_position = go.DOOR_OPEN, 0xFFFF
            else:
                patch_value = rng.randrange(1, 0x80)
            patch_kind = (
                PATCH_STATIC
                if patch_value < 0x80 and rng.randrange(3) == 0
                else PATCH_MAP
            )
            patch = (patch_x, patch_y, patch_value)
            if patch_kind == PATCH_MAP and patch_value == 0x80:
                patch_blocks = go.door_slab_overlaps_player(
                    go.Door(
                        patch_x,
                        patch_y,
                        door_vertical,
                        0,
                        action=door_action,
                        position=door_position,
                    ),
                    pose,
                )
            else:
                base_x_low, base_x_high, base_y_low, base_y_high = go.player_bounds(pose)
                patch_blocks = (
                    base_x_low <= patch_x <= base_x_high
                    and base_y_low <= patch_y <= base_y_high
                )
            if patch_blocks:
                patch = None
                patch_kind = PATCH_MAP
                door_vertical = True
        add(
            pose,
            dx,
            dy,
            patch,
            patch_kind,
            door_action,
            door_position,
            door_vertical,
        )
    return records


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--random-cases", type=int, default=10_000)
    parser.add_argument("--include-zero-delta", action="store_true")
    parser.add_argument("--output", type=Path, default=Path("clip_vectors.bin"))
    args = parser.parse_args()
    records = build_vectors(args.random_cases, include_zero_delta=args.include_zero_delta)
    args.output.write_bytes(struct.pack("<I", len(records)) + b"".join(records))
    print(f"wrote {len(records)} {RECORD.size}-byte vectors to {args.output}")


if __name__ == "__main__":
    main()
