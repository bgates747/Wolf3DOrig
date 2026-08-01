#!/usr/bin/env python3
"""Generate deterministic direct-eZ80 vectors for positional audio."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import random

import spatial_oracle as so


HERE = Path(__file__).resolve().parent
DEFAULT_OUTPUT = HERE.parent / "src/spatial_vectors.inc"
KIND_ACTOR = 0
KIND_TILE = 1
RECORD_SIZE = 28


def fixed(tile: int, fraction: int = 0x8000) -> int:
    return tile * so.TILE_GLOBAL + fraction


@dataclass(frozen=True)
class Vector:
    name: str
    kind: int
    sound_id: int
    heading: int
    player_x: int
    player_y: int
    source_x: int
    source_y: int


def directed_vectors() -> list[Vector]:
    vectors = [
        Vector("actor exact overlap", KIND_ACTOR, 0, 0, fixed(10), fixed(10), fixed(10), fixed(10)),
        Vector("actor positive sub-Q8 borrow", KIND_ACTOR, 1, 0, fixed(9, 0xFFFF), fixed(10), fixed(10, 0), fixed(10)),
        Vector("actor negative one-LSB borrow", KIND_ACTOR, 6, 0, fixed(10, 0), fixed(10), fixed(9, 0xFFFF), fixed(10)),
        Vector("actor exact +1 Q8", KIND_ACTOR, 18, 0, fixed(10, 1), fixed(10), fixed(10, 0x0101), fixed(10)),
        Vector("actor exact -1 Q8", KIND_ACTOR, 19, 0, fixed(10, 0x0101), fixed(10), fixed(10, 1), fixed(10)),
        Vector("tile exact center", KIND_TILE, 23, 0, fixed(10), fixed(11), fixed(10), fixed(11)),
        Vector("tile center minus one LSB", KIND_TILE, 24, 0, fixed(10, 0x8001), fixed(11, 0x8001), fixed(10), fixed(11)),
        Vector("tile center plus one LSB", KIND_TILE, 26, 0, fixed(10, 0x7FFF), fixed(11, 0x7FFF), fixed(10), fixed(11)),
    ]

    # One non-axis-aligned vector at every cardinal and diagonal heading.
    for heading in (0, 45, 90, 135, 180, 225, 270, 315):
        vectors.append(
            Vector(
                f"actor heading {heading}",
                KIND_ACTOR,
                (58 + heading // 45) & 0xFF,
                heading,
                fixed(20),
                fixed(20),
                fixed(24),
                fixed(18),
            )
        )

    vectors.extend(
        (
            Vector("actor one-degree truncation", KIND_ACTOR, 60, 30, fixed(10), fixed(10), fixed(10) - 1, fixed(10) - 200 * 256),
            Vector("actor forward positive clamp", KIND_ACTOR, 31, 0, fixed(0), fixed(10), fixed(63), fixed(10)),
            Vector("actor forward negative clamp", KIND_ACTOR, 31, 0, fixed(63), fixed(10), fixed(0), fixed(10)),
            Vector("actor lateral negative clamp", KIND_ACTOR, 31, 0, fixed(10), fixed(32), fixed(10), fixed(0)),
            Vector("actor lateral positive clamp", KIND_ACTOR, 31, 0, fixed(10), fixed(31), fixed(10), fixed(63)),
            Vector("actor focal row below one", KIND_ACTOR, 41, 0, fixed(10), fixed(10), fixed(10) + 168 * 256 + 255, fixed(10)),
            Vector("actor focal row reaches one", KIND_ACTOR, 42, 0, fixed(10), fixed(10), fixed(10) + 169 * 256, fixed(10)),
            Vector("actor map maximum", KIND_ACTOR, 68, 359, fixed(0, 0), fixed(0, 0), fixed(63, 0xFFFF), fixed(63, 0xFFFF)),
            Vector("actor reverse map maximum", KIND_ACTOR, 67, 181, fixed(63, 0xFFFF), fixed(63, 0xFFFF), fixed(0, 0), fixed(0, 0)),
            Vector("tile cardinal 90", KIND_TILE, 18, 90, fixed(40, 0x1234), fixed(20, 0xFEDC), fixed(42), fixed(17)),
            Vector("tile diagonal 225", KIND_TILE, 19, 225, fixed(40, 0xFF00), fixed(20, 0x0100), fixed(7), fixed(54)),
        )
    )
    return vectors


def randomized_vectors() -> list[Vector]:
    rng = random.Random(0x573D573D)
    vectors: list[Vector] = []
    for index in range(192):
        vectors.append(
            Vector(
                f"random actor {index}",
                KIND_ACTOR,
                rng.randrange(69),
                rng.randrange(360),
                rng.randrange(64 << 16),
                rng.randrange(64 << 16),
                rng.randrange(64 << 16),
                rng.randrange(64 << 16),
            )
        )
    for index in range(96):
        tile_x = rng.randrange(64)
        tile_y = rng.randrange(64)
        vectors.append(
            Vector(
                f"random tile {index}",
                KIND_TILE,
                rng.randrange(69),
                rng.randrange(360),
                rng.randrange(64 << 16),
                rng.randrange(64 << 16),
                fixed(tile_x),
                fixed(tile_y),
            )
        )
    return vectors


def _bytes32(value: int) -> tuple[int, int, int, int]:
    if not 0 <= value <= 0xFFFFFFFF:
        raise ValueError(f"fixture coordinate {value} is outside uint32 storage")
    return tuple(value.to_bytes(4, "little"))  # type: ignore[return-value]


def _word(value: int) -> tuple[int, int]:
    return (value & 0xFF, (value >> 8) & 0xFF)


def build_vectors() -> tuple[Vector, ...]:
    return tuple(directed_vectors() + randomized_vectors())


def render(vectors: tuple[Vector, ...]) -> str:
    gains = so.source_gain_table()
    lines = [
        "; Generated by scripts/generate_spatial_vectors.py -- do not hand-edit.",
        "; Expectations come from spatial_oracle.py and the original SetSoundLoc tables.",
        f"W3D_AUDIO_SPATIAL_VECTOR_COUNT: equ {len(vectors)}",
        f"W3D_AUDIO_SPATIAL_VECTOR_SIZE:  equ {RECORD_SIZE}",
        "W3D_AUDIO_SPATIAL_KIND_ACTOR:   equ 0",
        "W3D_AUDIO_SPATIAL_KIND_TILE:    equ 1",
        "",
        "spatial_vectors:",
    ]
    for vector in vectors:
        if vector.kind == KIND_TILE:
            request = so.spatialize_tile(
                vector.sound_id,
                vector.source_x >> 16,
                vector.source_y >> 16,
                vector.player_x,
                vector.player_y,
                vector.heading,
                gains,
            )
        else:
            request = so.spatialize_actor(
                vector.sound_id,
                vector.source_x,
                vector.source_y,
                vector.player_x,
                vector.player_y,
                vector.heading,
                gains,
            )
        data = (
            vector.kind,
            vector.sound_id,
            *_word(vector.heading),
            *_bytes32(vector.player_x),
            *_bytes32(vector.player_y),
            *_bytes32(vector.source_x),
            *_bytes32(vector.source_y),
            *_word(request.relative_x_q8),
            *_word(request.relative_y_q8),
            request.row,
            request.column,
            request.gain,
            request.flags,
        )
        if len(data) != RECORD_SIZE:
            raise AssertionError(f"vector record is {len(data)} bytes")
        lines.append(f"    ; {vector.name}")
        lines.append("    db " + ",".join(str(value) for value in data))
    lines.extend(("spatial_vectors_end:", ""))
    return "\n".join(lines)


def main() -> int:
    vectors = build_vectors()
    text = render(vectors)
    DEFAULT_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_OUTPUT.write_text(text, encoding="utf-8")
    print(f"wrote {len(vectors)} vectors ({len(vectors) * RECORD_SIZE} bytes) to {DEFAULT_OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
