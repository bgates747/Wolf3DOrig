"""Compact runtime level-state package used by the eZ80 Wolf3DOrig client."""

from __future__ import annotations

import struct
from dataclasses import dataclass

MAGIC = b"W3L1"
FOOTER = b"E3L1"
VERSION_MAJOR = 1
VERSION_MINOR = 0
HEADER_SIZE = 64
MAP_BYTES = 64 * 64
BLOCKING_BYTES = MAP_BYTES // 8
DOOR_SIZE = 10
STATIC_SIZE = 6
ACTOR_SIZE = 39
MAX_PACKAGE_SIZE = 24 * 1024
MAX_DOORS = 64
MAX_STATICS = 400
MAX_NONPLAYER_ACTORS = 149

SECTION_NAMES = ("doors", "statics", "actors", "blocking", "areas", "paths", "tilemap")


@dataclass(frozen=True)
class LevelPackage:
    level: int
    difficulty: int
    door_count: int
    static_count: int
    actor_count: int
    random_index: int
    player_pose: bytes
    sections: dict[str, bytes]


def build_package(package: LevelPackage) -> bytes:
    for name, value, maximum in (
        ("level", package.level, 9),
        ("difficulty", package.difficulty, 3),
        ("door count", package.door_count, MAX_DOORS),
        ("static count", package.static_count, MAX_STATICS),
        ("actor count", package.actor_count, MAX_NONPLAYER_ACTORS),
        ("random index", package.random_index, 255),
    ):
        if not 0 <= value <= maximum:
            raise ValueError(f"{name} {value} is outside 0..{maximum}")
    if len(package.player_pose) != 10:
        raise ValueError("player pose must contain x:i32, y:i32, angle:u16")
    expected = {
        "doors": package.door_count * DOOR_SIZE,
        "statics": package.static_count * STATIC_SIZE,
        "actors": package.actor_count * ACTOR_SIZE,
        "blocking": BLOCKING_BYTES,
        "areas": MAP_BYTES,
        "paths": MAP_BYTES,
        "tilemap": MAP_BYTES,
    }
    if set(package.sections) != set(SECTION_NAMES):
        raise ValueError("level package sections are incomplete or unknown")
    for name, size in expected.items():
        if len(package.sections[name]) != size:
            raise ValueError(f"{name} section is {len(package.sections[name])}, expected {size}")

    offsets: dict[str, int] = {}
    body = bytearray()
    for name in SECTION_NAMES:
        offsets[name] = HEADER_SIZE + len(body)
        body.extend(package.sections[name])
    body.extend(FOOTER)
    total_size = HEADER_SIZE + len(body)
    if total_size > MAX_PACKAGE_SIZE:
        raise ValueError(f"level package exceeds eZ80 arena: {total_size}")

    header = bytearray(HEADER_SIZE)
    header[0:4] = MAGIC
    header[4:8] = bytes((VERSION_MAJOR, VERSION_MINOR, package.level, package.difficulty))
    header[8:10] = bytes((package.door_count, package.actor_count))
    struct.pack_into("<H", header, 10, package.static_count)
    header[12] = package.random_index
    struct.pack_into("<H", header, 14, total_size)
    header[16:26] = package.player_pose
    for index, name in enumerate(SECTION_NAMES):
        struct.pack_into("<H", header, 26 + index * 2, offsets[name])
    return bytes(header + body)


def parse_package(data: bytes) -> LevelPackage:
    if len(data) < HEADER_SIZE or data[:4] != MAGIC:
        raise ValueError("not a W3L1 level package")
    if data[4:6] != bytes((VERSION_MAJOR, VERSION_MINOR)):
        raise ValueError(f"unsupported W3L version {data[4]}.{data[5]}")
    total_size = struct.unpack_from("<H", data, 14)[0]
    if total_size != len(data):
        raise ValueError(f"declared size {total_size} disagrees with file size {len(data)}")
    door_count, actor_count = data[8:10]
    static_count = struct.unpack_from("<H", data, 10)[0]
    offsets = [struct.unpack_from("<H", data, 26 + i * 2)[0] for i in range(len(SECTION_NAMES))]
    expected_sizes = (
        door_count * DOOR_SIZE,
        static_count * STATIC_SIZE,
        actor_count * ACTOR_SIZE,
        BLOCKING_BYTES,
        MAP_BYTES,
        MAP_BYTES,
        MAP_BYTES,
    )
    sections: dict[str, bytes] = {}
    cursor = HEADER_SIZE
    for name, offset, size in zip(SECTION_NAMES, offsets, expected_sizes):
        if offset != cursor or cursor + size > len(data):
            raise ValueError(f"invalid {name} section offset/size")
        sections[name] = data[cursor : cursor + size]
        cursor += size
    if data[cursor : cursor + len(FOOTER)] != FOOTER:
        raise ValueError("missing W3L1 end marker")
    cursor += len(FOOTER)
    if cursor != len(data) or any(data[40:HEADER_SIZE]):
        raise ValueError("noncanonical level package layout or reserved bytes")
    return LevelPackage(
        level=data[6],
        difficulty=data[7],
        door_count=door_count,
        static_count=static_count,
        actor_count=actor_count,
        random_index=data[12],
        player_pose=data[16:26],
        sections=sections,
    )
