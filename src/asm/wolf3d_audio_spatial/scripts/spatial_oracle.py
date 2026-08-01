#!/usr/bin/env python3
"""Independent Wolf3D mono positional-audio specification.

The production adapter deliberately uses the already-regressed reduced
TransformActor arithmetic: full 16.16 source/player positions are subtracted,
arithmetically reduced to signed Q8, and rotated by the generated 360-degree
Q12 motion basis.  This module describes that result in ordinary Python.  It
does not emulate eZ80 registers or invoke production assembly.

Wolf3D's original ``SetSoundLoc`` listener is displaced by FOCALLENGTH
(``0x5700`` in 16.16), its forward table coordinate is absolute and clamped to
0..14, and its signed lateral coordinate is clamped to -15..14.  The Agon port
collapses the source 15x30 stereo attenuation tables to one VDP gain byte.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
import re


REPO_ROOT = Path(__file__).resolve().parents[4]
PRODUCTION_SRC = REPO_ROOT / "src/asm/wolf3d/src"
ORIGINAL_WL_GAME = REPO_ROOT / "orig/src/WOLFSRC/WL_GAME.C"

Q12_ONE = 1 << 12
TILE_GLOBAL = 1 << 16
TILE_CENTER = 0x8000
FOCAL_LENGTH_16_16 = 0x5700
FOCAL_Q8 = FOCAL_LENGTH_16_16 >> 8
FORWARD_ROWS = 15
LATERAL_COLUMNS = 30
LATERAL_BIAS = 15
POSITIONED_FLAG = 0x01


class SpatialContractError(ValueError):
    """Raised when a caller violates the reduced positional contract."""


@dataclass(frozen=True)
class SpatialRequest:
    sound_id: int
    gain: int
    flags: int
    relative_x_q8: int
    relative_y_q8: int
    forward_q8: int
    lateral_q8: int
    row: int
    column: int


def _round_away(value: float) -> int:
    """Round a generated trigonometric entry to nearest, ties away from zero."""

    if value >= 0:
        return math.floor(value + 0.5)
    return math.ceil(value - 0.5)


def motion_basis_q12(heading: int) -> tuple[int, int]:
    """Return ``(cos, -sin)`` for map +Y south and heading 0..359."""

    if not isinstance(heading, int) or not 0 <= heading < 360:
        raise SpatialContractError("heading must be a normalized integer in 0..359")
    radians = math.radians(heading)
    return (
        _round_away(math.cos(radians) * Q12_ONE),
        _round_away(-math.sin(radians) * Q12_ONE),
    )


def _trunc_div(numerator: int, denominator: int) -> int:
    """C-style signed division, truncating toward zero."""

    quotient = abs(numerator) // abs(denominator)
    return -quotient if numerator < 0 else quotient


def mul_q8_q12(value_q8: int, fraction_q12: int) -> int:
    """Match original ``FixedByFrac`` per-product truncation."""

    if not -0x8000 <= value_q8 <= 0x7FFF:
        raise SpatialContractError("Q8 operand is outside signed 16-bit range")
    if not -Q12_ONE <= fraction_q12 <= Q12_ONE:
        raise SpatialContractError("Q12 fraction is outside -1..+1")
    return _trunc_div(value_q8 * fraction_q12, Q12_ONE)


def reduce_relative_q8(source_16_16: int, player_16_16: int) -> int:
    """Subtract full 16.16 coordinates, then arithmetically discard 8 bits."""

    relative = (source_16_16 - player_16_16) >> 8
    if not -0x8000 <= relative <= 0x7FFF:
        raise SpatialContractError("relative coordinate is outside signed Q8 range")
    return relative


def spatialize_relative_q8(
    sound_id: int,
    relative_x_q8: int,
    relative_y_q8: int,
    heading: int,
    gain_table: tuple[int, ...],
) -> SpatialRequest:
    """Spatialize one already-reduced source in the listener frame."""

    if not 0 <= sound_id <= 0xFF:
        raise SpatialContractError("logical sound id must fit one byte")
    if len(gain_table) != FORWARD_ROWS * LATERAL_COLUMNS:
        raise SpatialContractError("mono gain table must contain exactly 450 bytes")
    cos_q12, forward_y_q12 = motion_basis_q12(heading)

    # Original x/forward = gx*cos - gy*sin.  The production motion table's
    # second value is already -sin for map-Y-down coordinates.
    forward_q8 = (
        mul_q8_q12(relative_x_q8, cos_q12)
        + mul_q8_q12(relative_y_q8, forward_y_q12)
        + FOCAL_Q8
    )

    # Original y/lateral = gy*cos + gx*sin.  Reusing -sin makes the second
    # product a subtraction, exactly as in the assembly adapter.
    lateral_q8 = (
        mul_q8_q12(relative_y_q8, cos_q12)
        - mul_q8_q12(relative_x_q8, forward_y_q12)
    )

    forward_cell = forward_q8 >> 8
    lateral_cell = lateral_q8 >> 8
    row = min(abs(forward_cell), FORWARD_ROWS - 1)
    lateral_cell = max(-LATERAL_BIAS, min(LATERAL_BIAS - 1, lateral_cell))
    column = lateral_cell + LATERAL_BIAS
    gain = gain_table[row * LATERAL_COLUMNS + column]
    return SpatialRequest(
        sound_id=sound_id,
        gain=gain,
        flags=POSITIONED_FLAG,
        relative_x_q8=relative_x_q8,
        relative_y_q8=relative_y_q8,
        forward_q8=forward_q8,
        lateral_q8=lateral_q8,
        row=row,
        column=column,
    )


def spatialize_actor(
    sound_id: int,
    source_x_16_16: int,
    source_y_16_16: int,
    player_x_16_16: int,
    player_y_16_16: int,
    heading: int,
    gain_table: tuple[int, ...],
) -> SpatialRequest:
    """Spatialize one actor from authoritative full 16.16 coordinates."""

    return spatialize_relative_q8(
        sound_id,
        reduce_relative_q8(source_x_16_16, player_x_16_16),
        reduce_relative_q8(source_y_16_16, player_y_16_16),
        heading,
        gain_table,
    )


def spatialize_tile(
    sound_id: int,
    tile_x: int,
    tile_y: int,
    player_x_16_16: int,
    player_y_16_16: int,
    heading: int,
    gain_table: tuple[int, ...],
) -> SpatialRequest:
    """Spatialize the exact center of one unsigned map tile."""

    if not 0 <= tile_x <= 0xFF or not 0 <= tile_y <= 0xFF:
        raise SpatialContractError("tile coordinates must fit one byte")
    return spatialize_actor(
        sound_id,
        tile_x * TILE_GLOBAL + TILE_CENTER,
        tile_y * TILE_GLOBAL + TILE_CENTER,
        player_x_16_16,
        player_y_16_16,
        heading,
        gain_table,
    )


def parse_motion_table(path: Path | None = None) -> tuple[tuple[int, int], ...]:
    """Read production's generated 24-bit motion table as signed Q12 pairs."""

    table_path = path or PRODUCTION_SRC / "wolf3d_motion_table.inc"
    text = table_path.read_text(encoding="utf-8")
    section = text.split("w3d_motion_delta_table:\n", 1)[1]
    section = section.split("w3d_motion_delta_table_end:", 1)[0]
    entries: list[tuple[int, int]] = []
    for line in section.splitlines():
        match = re.match(r"\s*db\s+([^;]+)", line)
        if not match:
            continue
        raw = tuple(int(value.strip(), 0) for value in match.group(1).split(","))
        if len(raw) != 6 or any(not 0 <= value <= 0xFF for value in raw):
            raise SpatialContractError("malformed production motion-table row")
        values = []
        for offset in (0, 3):
            word = raw[offset] | (raw[offset + 1] << 8)
            values.append(word - 0x10000 if word & 0x8000 else word)
        entries.append((values[0], values[1]))
    if len(entries) != 360:
        raise SpatialContractError(f"motion table has {len(entries)} entries, not 360")
    return tuple(entries)


def parse_attenuation_tables(
    path: Path | None = None,
) -> tuple[tuple[tuple[int, ...], ...], tuple[tuple[int, ...], ...]]:
    """Parse the original source's 15x30 left/right attenuation tables."""

    source_path = path or ORIGINAL_WL_GAME
    text = source_path.read_text(encoding="latin-1")
    parsed: dict[str, tuple[tuple[int, ...], ...]] = {}
    for name in ("lefttable", "righttable"):
        match = re.search(
            rf"\bbyte\s+{name}\s*\[ATABLEMAX\]\s*"
            rf"\[ATABLEMAX\s*\*\s*2\]\s*=\s*\{{(?P<body>.*?)\}}\s*;",
            text,
            flags=re.DOTALL,
        )
        if not match:
            raise SpatialContractError(f"original source lacks {name}")
        rows = tuple(
            tuple(int(value) for value in re.findall(r"\d+", row))
            for row in re.findall(r"\{([^{}]*)\}", match.group("body"))
        )
        if len(rows) != FORWARD_ROWS or any(
            len(row) != LATERAL_COLUMNS for row in rows
        ):
            raise SpatialContractError(f"original {name} is not 15x30")
        parsed[name] = rows
    return parsed["lefttable"], parsed["righttable"]


def build_mono_gain_table(
    left: tuple[tuple[int, ...], ...],
    right: tuple[tuple[int, ...], ...],
) -> tuple[int, ...]:
    """Apply the settled source-grounded stereo-to-mono gain mapping."""

    if len(left) != FORWARD_ROWS or len(right) != FORWARD_ROWS:
        raise SpatialContractError("attenuation tables must contain 15 rows")
    output: list[int] = []
    for left_row, right_row in zip(left, right):
        if len(left_row) != LATERAL_COLUMNS or len(right_row) != LATERAL_COLUMNS:
            raise SpatialContractError("attenuation rows must contain 30 values")
        for left_value, right_value in zip(left_row, right_row):
            if not 0 <= left_value <= 15 or not 0 <= right_value <= 15:
                raise SpatialContractError("attenuation value is outside 0..15")
            attenuation = (left_value + right_value + 1) // 2
            output.append(((15 - attenuation) * 127 + 7) // 15)
    return tuple(output)


def parse_production_gain_table(path: Path | None = None) -> tuple[int, ...]:
    """Read the generated 450-byte table included by production assembly."""

    table_path = path or PRODUCTION_SRC / "wolf3d_audio_assets.inc"
    text = table_path.read_text(encoding="utf-8")
    section = text.split("w3d_audio_mono_gain_table:\n", 1)[1]
    section = section.split("w3d_audio_mono_gain_table_end:", 1)[0]
    values = tuple(
        int(value.strip(), 0)
        for line in section.splitlines()
        if line.strip().startswith("db ")
        for value in line.split("db ", 1)[1].split(",")
    )
    if len(values) != FORWARD_ROWS * LATERAL_COLUMNS:
        raise SpatialContractError(f"production gain table has {len(values)} bytes")
    if any(not 0 <= value <= 127 for value in values):
        raise SpatialContractError("production gain table contains invalid VDP gain")
    return values


def source_gain_table() -> tuple[int, ...]:
    """Convenience: construct the gain oracle from original C source."""

    return build_mono_gain_table(*parse_attenuation_tables())
