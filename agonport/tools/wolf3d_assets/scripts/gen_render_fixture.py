#!/usr/bin/env python3
"""Generates a real-level "first position" render fixture for the eZ80
wolf3d client -- Author decision 2026-07-31: "let's build a test fixture...
load the assets, set the camera at the player's first position, and just
render what he should see."

Parses one real shareware level's GAMEMAPS data and emits an eZ80 .inc file
containing the exact precomputed VDU byte stream needed to drive it end to
end: the raw 64x64 tilemap buffer, mutable door/static seeds, an eZ80-only
blocking-static bitset, and the wire-format `init_level` / `set_door` /
`set_static` / `set_player_pose` / `render_frame` command sequence, per the
settled contract in agonport/doc/handoff_ez80_ai_raycaster.md. All doors are
emitted closed (action=0, position=0x0000) and all real plane-1 static objects
are emitted in row-major order -- the level's actual state at first spawn,
before the player has touched anything.

Door `vertical`/`lock` derivation is grounded directly in
orig/src/WOLFSRC/WL_GAME.C's SetupGameLevel door-spawn loop: even tile
values (90,92,...,100) -> vertical=1, odd (91,93,...,101) -> vertical=0,
lock = (tile-90)//2 for both (integer division collapses each even/odd pair
to the same lock index). Player start facing is WL_GAME.C's
SpawnPlayer(x, y, NORTH + tile - 19) via WL_DEF.H's NORTH=0/EAST=1/SOUTH=2/
WEST=3, converted here to the wire's 0..359 degree/counterclockwise/east=0
convention (confirmed in the handoff doc's VDP_AGENT_RESPONSE item 5).
Wall/door texture ids reuse exactly the same classification as
scripts/build_level_manifest.py (must stay in sync).

Run this script, then copy the referenced level's ``tiles.agnb`` and
``sprites.agnb`` next to the assembled binary on the SD card (see
``src/asm/wolf3d/README.md``).
"""

import argparse
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from formats import mapfile, staticinfo  # noqa: E402

GENERATED_DIR = Path(__file__).resolve().parents[3] / "assets" / "generated" / "wolf3d"
DEFAULT_MAPHEAD = Path(__file__).resolve().parents[4] / "orig" / "data" / "MAPHEAD.WL1"
DEFAULT_GAMEMAPS = Path(__file__).resolve().parents[4] / "orig" / "data" / "GAMEMAPS.WL1"

WALL_MIN, WALL_MAX = 1, 63
DOOR_MIN, DOOR_MAX = 90, 101
PLAYER_START_FACING_ANGLE = {19: 90, 20: 0, 21: 270, 22: 180}  # N, E, S, W -> wire degrees
DOOR_LOCK_KIND = {0: "normal", 1: "locked", 2: "locked", 3: "locked", 4: "locked", 5: "elevator"}
DOOR_KIND_TEXTURE_ID = {"normal": 121, "elevator": 123, "locked": 124}

BUFFERED_WOLF3D = 0x4A
SUB_INIT_LEVEL = 1
SUB_SET_PLAYER_POSE = 2
SUB_SET_DOOR = 3
SUB_SET_STATIC = 6
SUB_RENDER_FRAME = 7

W3D_TILE_DOOR_FLAG = 0x80
TILE_GLOBAL = 1 << 16


def build_tilemap_and_doors(plane0: list[list[int]]):
    tilemap = bytearray(64 * 64)
    doors = []  # each: (tilex, tiley, vertical, lock, textureId)
    for y, row in enumerate(plane0):
        for x, value in enumerate(row):
            if WALL_MIN <= value <= WALL_MAX:
                tilemap[y * 64 + x] = value
            elif DOOR_MIN <= value <= DOOR_MAX:
                vertical = (value - DOOR_MIN) % 2 == 0
                lock = (value - DOOR_MIN) // 2
                texture_id = DOOR_KIND_TEXTURE_ID[DOOR_LOCK_KIND[lock]]
                doornum = len(doors)
                doors.append((x, y, vertical, lock, texture_id))
                tilemap[y * 64 + x] = W3D_TILE_DOOR_FLAG | doornum
            # else: open floor / area marker -- byte stays 0x00
    return bytes(tilemap), doors


def find_player_start(plane1: list[list[int]]):
    for y, row in enumerate(plane1):
        for x, value in enumerate(row):
            if value in PLAYER_START_FACING_ANGLE:
                return x, y, PLAYER_START_FACING_ANGLE[value]
    raise ValueError("no player-start marker (plane1 value 19-22) found in this level")


def build_statics(plane1: list[list[int]]):
    """Build mutable static seeds and their eZ80 collision bitset.

    Seeds are ordered exactly like the original ``ScanInfoPlane()`` traversal:
    rows first, then columns.  A bit index is ``y * 64 + x`` and the bit is
    LSB-first within its byte.  The bitset never enters the VDP command stream.
    """

    if len(plane1) != mapfile.MAP_HEIGHT or any(
        len(row) != mapfile.MAP_WIDTH for row in plane1
    ):
        raise ValueError(
            f"expected {mapfile.MAP_WIDTH}x{mapfile.MAP_HEIGHT} plane 1"
        )

    statics = []  # each: tilex, tiley, shapenum, flags, itemnumber
    blocking_bits = bytearray(mapfile.MAP_WIDTH * mapfile.MAP_HEIGHT // 8)
    for y, row in enumerate(plane1):
        for x, value in enumerate(row):
            info = staticinfo.from_plane1(value)
            if info is None:
                continue
            flags = staticinfo.FL_BONUS if info.bonus else 0
            # statobj_t's itemnumber is initialized only for FL_BONUS entries;
            # the global static array otherwise begins zero-filled.
            itemnumber = int(info.kind) if info.bonus else 0
            statics.append((x, y, info.shapenum, flags, itemnumber))
            if info.blocking:
                bit_index = y * mapfile.MAP_WIDTH + x
                blocking_bits[bit_index >> 3] |= 1 << (bit_index & 7)
    return statics, bytes(blocking_bits)


def le32(value: int) -> bytes:
    return struct.pack("<i", value)


def le16(value: int) -> bytes:
    return struct.pack("<H", value)


def lei16(value: int) -> bytes:
    return struct.pack("<h", value)


def build_command_stream(
    control_buffer_id,
    tilemap_buffer_id,
    doors,
    statics,
    player_x,
    player_y,
    player_angle,
):
    out = bytearray()

    def header(subcommand: int) -> bytes:
        return bytes((23, 0, 0xA0)) + le16(control_buffer_id) + bytes((BUFFERED_WOLF3D, subcommand))

    out += header(SUB_INIT_LEVEL) + le16(tilemap_buffer_id)

    for doornum, (tilex, tiley, vertical, lock, texture_id) in enumerate(doors):
        out += header(SUB_SET_DOOR)
        out += bytes((doornum, tilex, tiley, 1 if vertical else 0, lock, 0))  # action=0 closed
        out += le16(0x0000)  # position=fully closed
        out += bytes((texture_id,))

    for index, (tilex, tiley, shapenum, flags, _itemnumber) in enumerate(statics):
        out += header(SUB_SET_STATIC)
        out += le16(index) + bytes((tilex, tiley)) + lei16(shapenum) + bytes((flags,))

    out += header(SUB_SET_PLAYER_POSE) + le32(player_x) + le32(player_y) + le16(player_angle)
    out += header(SUB_RENDER_FRAME)
    return bytes(out)


def emit_inc(
    out_path: Path,
    level_index: int,
    level_name: str,
    tilemap: bytes,
    doors,
    statics,
    static_blocking_bits: bytes,
    player,
    player_tile,
    control_buffer_id: int,
    tilemap_buffer_id: int,
    cmds: bytes,
) -> None:
    tilex, tiley = player_tile
    px, py, angle = player
    lines = [
        f"; Auto-generated by {Path(__file__).name} -- level_{level_index:02d} ({level_name}) "
        "\"player's first position\" render fixture. Do not hand-edit; re-run the script.",
        ";",
        f"; Player start: tile ({tilex},{tiley}), angle {angle} degrees "
        f"(0=east, 90=north, ccw). {len(doors)} real door(s), all emitted closed; "
        f"{len(statics)} static object(s).",
        "",
        f"W3D_FIXTURE_CONTROL_BUFFER_ID: equ {control_buffer_id}",
        f"W3D_FIXTURE_TILEMAP_BUFFER_ID: equ {tilemap_buffer_id}",
        f"W3D_FIXTURE_DOOR_COUNT: equ {len(doors)}",
        f"W3D_FIXTURE_STATIC_COUNT: equ {len(statics)}",
        "",
        "; Authoritative mutable-player seed used by the interactive fixture.",
        "w3d_fixture_initial_player_pose:",
        "    db " + ",".join(str(b) for b in (le32(px) + le32(py) + le16(angle))),
        "w3d_fixture_initial_player_pose_end:",
        "",
        "; Authoritative door seeds in W3D_DOOR_* / W3D_DOOR_SIZE order.",
        "; Runtime state copies these records; the VDP receives only dirty snapshots.",
        "w3d_fixture_initial_doors:",
    ]
    for tilex, tiley, vertical, lock, texture_id in doors:
        lines.append(
            "    db "
            + ",".join(
                str(value)
                for value in (
                    tilex,
                    tiley,
                    1 if vertical else 0,
                    lock,
                    0,  # W3D_DOOR_ACTION_CLOSED
                    0,
                    0,  # uint16 position, fully closed
                    texture_id,
                )
            )
        )
    lines.extend([
        "w3d_fixture_initial_doors_end:",
        "",
        "; Authoritative static seeds: tilex, tiley, shapenum i16, flags, itemnumber.",
        "; Records remain allocated after pickup; shapenum=-1 marks a removed object.",
        "w3d_fixture_initial_statics:",
    ])
    for tilex, tiley, shapenum, flags, itemnumber in statics:
        lines.append(
            "    db "
            + ",".join(
                str(value)
                for value in (
                    bytes((tilex, tiley))
                    + lei16(shapenum)
                    + bytes((flags, itemnumber))
                )
            )
        )
    lines.extend([
        "w3d_fixture_initial_statics_end:",
        "",
        "; eZ80-only collision mask for blocking statics: bit y*64+x, LSB-first.",
        "; This is not uploaded to the VDP.",
        "w3d_fixture_static_blocking_bits:",
    ])
    for i in range(0, len(static_blocking_bits), 32):
        chunk = static_blocking_bits[i:i + 32]
        lines.append("    db " + ",".join(str(b) for b in chunk))
    lines.extend([
        "w3d_fixture_static_blocking_bits_end:",
        "",
        "w3d_fixture_tilemap:",
    ])
    for row in range(64):
        chunk = tilemap[row * 64:(row + 1) * 64]
        lines.append("    db " + ",".join(str(b) for b in chunk))
    lines.append("w3d_fixture_tilemap_end:")
    lines.append("")
    lines.append(f"w3d_fixture_cmds_len: equ {len(cmds)}")
    lines.append("w3d_fixture_cmds:")
    for i in range(0, len(cmds), 24):
        chunk = cmds[i:i + 24]
        lines.append("    db " + ",".join(str(b) for b in chunk))
    lines.append("w3d_fixture_cmds_end:")
    out_path.write_text("\n".join(lines) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--level", type=int, default=0, help="GAMEMAPS level slot index")
    parser.add_argument("--maphead", type=Path, default=DEFAULT_MAPHEAD)
    parser.add_argument("--gamemaps", type=Path, default=DEFAULT_GAMEMAPS)
    parser.add_argument("--control-buffer-id", type=int, default=1)
    parser.add_argument("--tilemap-buffer-id", type=int, default=2)
    parser.add_argument(
        "--out", type=Path,
        default=Path(__file__).resolve().parents[4] / "src" / "asm" / "wolf3d" / "src" / "wolf3d_fixture.inc",
    )
    args = parser.parse_args()

    maphead = mapfile.read_maphead(args.maphead.read_bytes())
    gamemaps = args.gamemaps.read_bytes()
    level = mapfile.read_level(gamemaps, maphead, args.level, maphead.magic)

    tilemap, doors = build_tilemap_and_doors(level.plane0)
    statics, static_blocking_bits = build_statics(level.plane1)
    tilex, tiley, angle = find_player_start(level.plane1)
    player_x = (tilex * TILE_GLOBAL) + TILE_GLOBAL // 2
    player_y = (tiley * TILE_GLOBAL) + TILE_GLOBAL // 2

    cmds = build_command_stream(
        args.control_buffer_id,
        args.tilemap_buffer_id,
        doors,
        statics,
        player_x,
        player_y,
        angle,
    )

    emit_inc(
        args.out,
        args.level,
        level.header.name,
        tilemap,
        doors,
        statics,
        static_blocking_bits,
        (player_x, player_y, angle),
        (tilex, tiley),
        args.control_buffer_id,
        args.tilemap_buffer_id,
        cmds,
    )
    print(
        f"level_{args.level:02d} ({level.header.name}): player start tile ({tilex},{tiley}) "
        f"facing {angle} deg, {len(doors)} door(s), {len(statics)} static(s) "
        f"({sum(byte.bit_count() for byte in static_blocking_bits)} blocking). Wrote {args.out} "
        f"({len(cmds)}-byte command stream)."
    )


if __name__ == "__main__":
    main()
