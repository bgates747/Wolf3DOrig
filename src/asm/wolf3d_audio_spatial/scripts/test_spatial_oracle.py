#!/usr/bin/env python3
"""Host regression for :mod:`spatial_oracle`."""

from __future__ import annotations

import random
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import spatial_oracle as so


GAIN_TABLE = so.source_gain_table()
PRODUCTION_MOTION = so.parse_motion_table()
PRODUCTION_GAIN = so.parse_production_gain_table()


def fixed(tile: int, fraction: int = 0x8000) -> int:
    return tile * so.TILE_GLOBAL + fraction


def bytewise_reduced_delta(source: int, player: int) -> int:
    """Independent model of the production three-byte subtract and discard."""

    source_bytes = source.to_bytes(4, "little", signed=False)
    player_bytes = player.to_bytes(4, "little", signed=False)
    borrow = 0
    difference: list[int] = []
    for source_byte, player_byte in zip(source_bytes[:3], player_bytes[:3]):
        value = source_byte - player_byte - borrow
        difference.append(value & 0xFF)
        borrow = int(value < 0)
    word = difference[1] | (difference[2] << 8)
    return word - 0x10000 if word & 0x8000 else word


def byte_model_spatialize(
    source_x: int,
    source_y: int,
    player_x: int,
    player_y: int,
    heading: int,
) -> tuple[int, int, int, int, int, int]:
    """Second formulation based on parsed production data and byte arithmetic."""

    relative_x = bytewise_reduced_delta(source_x, player_x)
    relative_y = bytewise_reduced_delta(source_y, player_y)
    cos_q12, forward_y_q12 = PRODUCTION_MOTION[heading]

    def product(value: int, fraction: int) -> int:
        magnitude = abs(value * fraction) // so.Q12_ONE
        return -magnitude if (value < 0) != (fraction < 0) else magnitude

    forward = product(relative_x, cos_q12) + product(relative_y, forward_y_q12)
    forward += so.FOCAL_Q8
    lateral = product(relative_y, cos_q12) - product(relative_x, forward_y_q12)
    row = min(abs(forward >> 8), 14)
    column = max(-15, min(14, lateral >> 8)) + 15
    gain = PRODUCTION_GAIN[row * 30 + column]
    return relative_x, relative_y, forward, lateral, row, column, gain


class SourceTableTests(unittest.TestCase):
    def test_generated_motion_basis_matches_all_360_mathematical_entries(self) -> None:
        production = so.parse_motion_table()
        self.assertEqual(len(production), 360)
        self.assertEqual(production, tuple(so.motion_basis_q12(i) for i in range(360)))
        self.assertEqual(production[0], (4096, 0))
        self.assertEqual(production[45], (2896, -2896))
        self.assertEqual(production[90], (0, -4096))
        self.assertEqual(production[180], (-4096, 0))
        self.assertEqual(production[270], (0, 4096))
        self.assertEqual(production[315], (2896, 2896))

    def test_generated_gain_table_matches_original_setsoundloc_tables(self) -> None:
        left, right = so.parse_attenuation_tables()
        self.assertEqual(len(left), 15)
        self.assertTrue(all(len(row) == 30 for row in left + right))
        self.assertEqual(GAIN_TABLE, so.parse_production_gain_table())
        self.assertEqual(len(GAIN_TABLE), 450)
        for row in range(15):
            values = GAIN_TABLE[row * 30 : (row + 1) * 30]
            self.assertEqual(values, tuple(reversed(values)))
        self.assertEqual(GAIN_TABLE[0 * 30 + 15], 127)
        self.assertEqual(GAIN_TABLE[0 * 30 + 0], 59)
        self.assertEqual(GAIN_TABLE[14 * 30 + 15], 59)


class CoordinateReductionTests(unittest.TestCase):
    def test_actor_fractional_borrow_boundaries(self) -> None:
        boundaries = (
            (fixed(10, 0x0000), fixed(9, 0xFFFF), 0),
            (fixed(9, 0xFFFF), fixed(10, 0x0000), -1),
            (fixed(10, 0x0100), fixed(10, 0x0001), 0),
            (fixed(10, 0x0101), fixed(10, 0x0001), 1),
            (fixed(10, 0x0001), fixed(10, 0x0101), -1),
            (fixed(63, 0xFFFF), fixed(0, 0x0000), 0x3FFF),
            (fixed(0, 0x0000), fixed(63, 0xFFFF), -0x4000),
        )
        for source, player, expected in boundaries:
            with self.subTest(source=source, player=player):
                self.assertEqual(so.reduce_relative_q8(source, player), expected)
                self.assertEqual(bytewise_reduced_delta(source, player), expected)

    def test_tile_centers_preserve_fractional_borrow(self) -> None:
        exact = so.spatialize_tile(18, 10, 11, fixed(10), fixed(11), 0, GAIN_TABLE)
        below = so.spatialize_tile(
            18, 10, 11, fixed(10, 0x8001), fixed(11, 0x8001), 0, GAIN_TABLE
        )
        above = so.spatialize_tile(
            18, 10, 11, fixed(10, 0x7FFF), fixed(11, 0x7FFF), 0, GAIN_TABLE
        )
        self.assertEqual((exact.relative_x_q8, exact.relative_y_q8), (0, 0))
        self.assertEqual((below.relative_x_q8, below.relative_y_q8), (-1, -1))
        self.assertEqual((above.relative_x_q8, above.relative_y_q8), (0, 0))


class TransformTests(unittest.TestCase):
    def test_cardinals_and_diagonals(self) -> None:
        player_x = fixed(20)
        player_y = fixed(20)
        source_x = fixed(24)
        source_y = fixed(18)
        expected = {
            0: (1111, -512),
            45: (1173, 362),
            90: (599, 1024),
            135: (-275, 1086),
            180: (-937, 512),
            225: (-999, -362),
            270: (-425, -1024),
            315: (449, -1086),
        }
        for heading, (forward, lateral) in expected.items():
            with self.subTest(heading=heading):
                request = so.spatialize_actor(
                    58,
                    source_x,
                    source_y,
                    player_x,
                    player_y,
                    heading,
                    GAIN_TABLE,
                )
                self.assertEqual((request.forward_q8, request.lateral_q8), (forward, lateral))
                self.assertEqual((request.sound_id, request.flags), (58, 1))

    def test_focal_bias_and_ahead_behind_reference(self) -> None:
        at_listener = so.spatialize_actor(
            6, fixed(12), fixed(12), fixed(12), fixed(12), 0, GAIN_TABLE
        )
        ahead = so.spatialize_actor(
            6, fixed(16), fixed(12), fixed(12), fixed(12), 0, GAIN_TABLE
        )
        behind = so.spatialize_actor(
            6, fixed(8), fixed(12), fixed(12), fixed(12), 0, GAIN_TABLE
        )
        self.assertEqual(at_listener.forward_q8, 0x57)
        self.assertEqual((at_listener.row, at_listener.column), (0, 15))
        self.assertEqual((ahead.forward_q8, ahead.row), (4 * 256 + 0x57, 4))
        self.assertEqual((behind.forward_q8, behind.row), (-4 * 256 + 0x57, 4))
        self.assertEqual(ahead.gain, behind.gain)

    def test_lateral_and_distance_clamps_are_asymmetric_at_source_edges(self) -> None:
        # SetSoundLoc admits -15 but clamps +15 down to +14; after the +15
        # bias these become columns 0 and 29.
        far_left = so.spatialize_actor(
            31, fixed(10), fixed(0), fixed(10), fixed(32), 0, GAIN_TABLE
        )
        far_right = so.spatialize_actor(
            31, fixed(10), fixed(63), fixed(10), fixed(31), 0, GAIN_TABLE
        )
        far_forward = so.spatialize_actor(
            31, fixed(63), fixed(10), fixed(0), fixed(10), 0, GAIN_TABLE
        )
        self.assertEqual(far_left.column, 0)
        self.assertEqual(far_right.column, 29)
        self.assertEqual(far_forward.row, 14)

    def test_each_product_truncates_before_terms_are_combined(self) -> None:
        request = so.spatialize_actor(
            60,
            fixed(10) - 1,
            fixed(10) - 200 * 256,
            fixed(10),
            fixed(10),
            30,
            GAIN_TABLE,
        )
        self.assertEqual((request.relative_x_q8, request.relative_y_q8), (-1, -200))
        self.assertEqual((request.forward_q8, request.lateral_q8), (187, -173))


class RandomizedComparisonTests(unittest.TestCase):
    def test_20000_actor_vectors_match_byte_and_generated_table_reference(self) -> None:
        rng = random.Random(0x573DA0)
        for index in range(20_000):
            player_x = rng.randrange(0, 64 << 16)
            player_y = rng.randrange(0, 64 << 16)
            source_x = rng.randrange(0, 64 << 16)
            source_y = rng.randrange(0, 64 << 16)
            heading = rng.randrange(360)
            expected = byte_model_spatialize(
                source_x, source_y, player_x, player_y, heading
            )
            actual = so.spatialize_actor(
                index & 0xFF,
                source_x,
                source_y,
                player_x,
                player_y,
                heading,
                GAIN_TABLE,
            )
            self.assertEqual(
                (
                    actual.relative_x_q8,
                    actual.relative_y_q8,
                    actual.forward_q8,
                    actual.lateral_q8,
                    actual.row,
                    actual.column,
                    actual.gain,
                ),
                expected,
                f"random actor vector {index}",
            )

    def test_5000_tile_vectors_equal_explicit_center_actor_vectors(self) -> None:
        rng = random.Random(0x71E573)
        for index in range(5_000):
            tile_x = rng.randrange(64)
            tile_y = rng.randrange(64)
            player_x = rng.randrange(0, 64 << 16)
            player_y = rng.randrange(0, 64 << 16)
            heading = rng.randrange(360)
            tile = so.spatialize_tile(
                index & 0xFF,
                tile_x,
                tile_y,
                player_x,
                player_y,
                heading,
                GAIN_TABLE,
            )
            actor = so.spatialize_actor(
                index & 0xFF,
                fixed(tile_x),
                fixed(tile_y),
                player_x,
                player_y,
                heading,
                GAIN_TABLE,
            )
            self.assertEqual(tile, actor, f"random tile vector {index}")


if __name__ == "__main__":
    unittest.main()
