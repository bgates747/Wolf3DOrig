#!/usr/bin/env python3
"""Directed host tests for the independent Wolf3D sight oracle."""

from __future__ import annotations

import hashlib
import unittest

import generate_dda_vectors as dda


def empty_map() -> bytes:
    payload = bytearray(4096)
    for coordinate in range(64):
        payload[coordinate] = dda.TILE_WALL
        payload[63 * 64 + coordinate] = dda.TILE_WALL
        payload[coordinate * 64] = dda.TILE_WALL
        payload[coordinate * 64 + 63] = dda.TILE_WALL
    return bytes(payload)


class SharedFixtureTests(unittest.TestCase):
    def test_shared_map_identity(self) -> None:
        payload = dda.load_shared_map()
        self.assertEqual(len(payload), 4096)
        self.assertEqual(payload[13 * 64 + 13], 0x80)
        self.assertEqual(
            hashlib.sha256(payload).hexdigest(),
            "640b7d254f1d887b122a126414fefc708718a8f044f35ca7b6130f6b56d81ce2",
        )

    def test_canonical_midpoint_door_threshold(self) -> None:
        payload = dda.load_shared_map()
        endpoints = (dda.fixed(11), dda.fixed(13), dda.fixed(15), dda.fixed(13))
        self.assertFalse(
            dda.check_line(
                payload, *endpoints, door_vertical=True, door_position=0x7FFF
            )
        )
        self.assertTrue(
            dda.check_line(
                payload, *endpoints, door_vertical=True, door_position=0x8000
            )
        )

    def test_canonical_door_remains_configured_with_unrelated_patch(
        self,
    ) -> None:
        payload = dda.load_shared_map()
        endpoints = (dda.fixed(11), dda.fixed(13), dda.fixed(15), dda.fixed(13))
        self.assertTrue(
            dda.check_line(
                payload,
                *endpoints,
                door_vertical=True,
                door_position=0xFFFF,
                patch=(30, 30, dda.TILE_DOOR | 1),
            )
        )


class CheckLineOracleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tilemap = empty_map()

    def test_wall_blocks_in_both_axis_directions(self) -> None:
        patch = (30, 30, dda.TILE_WALL)
        eastward = (
            dda.fixed(27), dda.fixed(30), dda.fixed(33), dda.fixed(30)
        )
        northward = (
            dda.fixed(30), dda.fixed(33), dda.fixed(30), dda.fixed(27)
        )
        for endpoints in (eastward, eastward[2:] + eastward[:2]):
            self.assertFalse(
                dda.check_line(
                    self.tilemap,
                    *endpoints,
                    door_vertical=True,
                    door_position=0xFFFF,
                    patch=patch,
                )
            )
        self.assertFalse(
            dda.check_line(
                self.tilemap,
                *northward,
                door_vertical=False,
                door_position=0xFFFF,
                patch=patch,
            )
        )

    def test_vertical_door_equality_passes(self) -> None:
        endpoints = (
            dda.fixed(27),
            dda.fixed(30, 0x4000),
            dda.fixed(33),
            dda.fixed(30, 0x4000),
        )
        patch = (30, 30, dda.TILE_DOOR)
        self.assertFalse(
            dda.check_line(
                self.tilemap,
                *endpoints,
                door_vertical=True,
                door_position=0x3FFF,
                patch=patch,
            )
        )
        self.assertTrue(
            dda.check_line(
                self.tilemap,
                *endpoints,
                door_vertical=True,
                door_position=0x4000,
                patch=patch,
            )
        )

    def test_nonzero_door_index_uses_configured_slot(self) -> None:
        endpoints = (
            dda.fixed(27),
            dda.fixed(30, 0x4000),
            dda.fixed(33),
            dda.fixed(30, 0x4000),
        )
        for door_index in (1, 17, 63):
            with self.subTest(door_index=door_index):
                self.assertTrue(
                    dda.check_line(
                        self.tilemap,
                        *endpoints,
                        door_vertical=True,
                        door_position=0x4000,
                        patch=(
                            30,
                            30,
                            dda.TILE_DOOR | door_index,
                        ),
                    )
                )

    def test_horizontal_door_equality_passes(self) -> None:
        endpoints = (
            dda.fixed(30, 0xC000),
            dda.fixed(27),
            dda.fixed(30, 0xC000),
            dda.fixed(33),
        )
        patch = (30, 30, dda.TILE_DOOR)
        self.assertFalse(
            dda.check_line(
                self.tilemap,
                *endpoints,
                door_vertical=False,
                door_position=0xBFFF,
                patch=patch,
            )
        )
        self.assertTrue(
            dda.check_line(
                self.tilemap,
                *endpoints,
                door_vertical=False,
                door_position=0xC000,
                patch=patch,
            )
        )

    def test_angled_vertical_door_uses_center_plane_both_directions(
        self,
    ) -> None:
        endpoints = (
            dda.fixed(27, 0x8000),
            dda.fixed(29, 0),
            dda.fixed(33, 0x8000),
            dda.fixed(32, 0),
        )
        patch = (30, 30, dda.TILE_DOOR)
        for ordered in (endpoints, endpoints[2:] + endpoints[:2]):
            with self.subTest(ordered=ordered):
                self.assertFalse(
                    dda.check_line(
                        self.tilemap,
                        *ordered,
                        door_vertical=True,
                        door_position=0x7FFF,
                        patch=patch,
                    )
                )
                self.assertTrue(
                    dda.check_line(
                        self.tilemap,
                        *ordered,
                        door_vertical=True,
                        door_position=0x8000,
                        patch=patch,
                    )
                )

    def test_angled_horizontal_door_uses_center_plane_both_directions(
        self,
    ) -> None:
        endpoints = (
            dda.fixed(29, 0),
            dda.fixed(27, 0x8000),
            dda.fixed(32, 0),
            dda.fixed(33, 0x8000),
        )
        patch = (30, 30, dda.TILE_DOOR)
        for ordered in (endpoints, endpoints[2:] + endpoints[:2]):
            with self.subTest(ordered=ordered):
                self.assertFalse(
                    dda.check_line(
                        self.tilemap,
                        *ordered,
                        door_vertical=False,
                        door_position=0x7FFF,
                        patch=patch,
                    )
                )
                self.assertTrue(
                    dda.check_line(
                        self.tilemap,
                        *ordered,
                        door_vertical=False,
                        door_position=0x8000,
                        patch=patch,
                    )
                )

    def test_full_fraction_door_threshold_is_not_reduced_to_8_8(
        self,
    ) -> None:
        endpoints = (
            dda.fixed(27),
            dda.fixed(30, 0x40FF),
            dda.fixed(33),
            dda.fixed(30, 0x40FF),
        )
        patch = (30, 30, dda.TILE_DOOR)
        for ordered in (endpoints, endpoints[2:] + endpoints[:2]):
            with self.subTest(ordered=ordered):
                self.assertFalse(
                    dda.check_line(
                        self.tilemap,
                        *ordered,
                        door_vertical=True,
                        door_position=0x4000,
                        patch=patch,
                    )
                )

    def test_odd_slope_door_center_is_direction_independent(self) -> None:
        endpoints = (
            dda.fixed(27),
            dda.fixed(30, 0x1000),
            dda.fixed(33),
            dda.fixed(30, 0xF000),
        )
        patch = (30, 30, dda.TILE_DOOR)
        for ordered in (endpoints, endpoints[2:] + endpoints[:2]):
            with self.subTest(ordered=ordered):
                self.assertFalse(
                    dda.check_line(
                        self.tilemap,
                        *ordered,
                        door_vertical=True,
                        door_position=0x7FFF,
                        patch=patch,
                    )
                )
                self.assertTrue(
                    dda.check_line(
                        self.tilemap,
                        *ordered,
                        door_vertical=True,
                        door_position=0x8000,
                        patch=patch,
                    )
                )

    def test_long_shallow_door_intercept_uses_original_endpoints(
        self,
    ) -> None:
        endpoints = (
            dda.fixed(1),
            dda.fixed(30, 0),
            dda.fixed(62),
            dda.fixed(30, 0x3C00),
        )
        patch = (60, 30, dda.TILE_DOOR)
        for ordered in (endpoints, endpoints[2:] + endpoints[:2]):
            with self.subTest(ordered=ordered):
                self.assertFalse(
                    dda.check_line(
                        self.tilemap,
                        *ordered,
                        door_vertical=True,
                        door_position=0x1000,
                        patch=patch,
                    )
                )

    def test_center_plane_outside_door_row_does_not_block(self) -> None:
        endpoints = (
            dda.fixed(25, 0x2000),
            dda.fixed(25, 0x2000),
            dda.fixed(31, 0x2000),
            dda.fixed(30, 0x2000),
        )
        patch = (30, 30, dda.TILE_DOOR)
        for ordered in (endpoints, endpoints[2:] + endpoints[:2]):
            with self.subTest(ordered=ordered):
                self.assertTrue(
                    dda.check_line(
                        self.tilemap,
                        *ordered,
                        door_vertical=True,
                        door_position=0,
                        patch=patch,
                    )
                )

    def test_wrong_door_orientation_does_not_block_parallel_ray(self) -> None:
        endpoints = (
            dda.fixed(27), dda.fixed(30), dda.fixed(33), dda.fixed(30)
        )
        self.assertTrue(
            dda.check_line(
                self.tilemap,
                *endpoints,
                door_vertical=False,
                door_position=0,
                patch=(30, 30, dda.TILE_DOOR),
            )
        )

    def test_reserved_tile_blocks_conservatively(self) -> None:
        self.assertFalse(
            dda.check_line(
                self.tilemap,
                dda.fixed(27),
                dda.fixed(30),
                dda.fixed(33),
                dda.fixed(30),
                door_vertical=True,
                door_position=0xFFFF,
                patch=(30, 30, 0xC0),
            )
        )


class CheckSightOracleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tilemap = empty_map()
        self.actor = (dda.fixed(30), dda.fixed(30))

    def sight(self, player: tuple[int, int], **kwargs: object) -> bool:
        defaults: dict[str, object] = {
            "direction": dda.DIR_EAST,
            "area_connected": True,
            "made_noise": False,
            "door_vertical": True,
            "door_position": 0xFFFF,
        }
        defaults.update(kwargs)
        return dda.check_sight(
            self.tilemap, *self.actor, *player, **defaults
        )

    def test_disconnected_area_always_rejects(self) -> None:
        self.assertFalse(
            self.sight(
                (dda.fixed(30, 0x9000), dda.fixed(30)),
                area_connected=False,
                made_noise=True,
            )
        )

    def test_close_distance_is_automatic_after_area_gate(self) -> None:
        self.assertTrue(
            self.sight(
                (dda.fixed(29), dda.fixed(30)),
                direction=dda.DIR_EAST,
            )
        )

    def test_close_distance_uses_full_16_16_strict_boundary(self) -> None:
        actor_x, actor_y = self.actor
        self.assertTrue(
            self.sight(
                (actor_x - 0x18000 + 1, actor_y),
                direction=dda.DIR_EAST,
            )
        )
        self.assertFalse(
            self.sight(
                (actor_x - 0x18000, actor_y),
                direction=dda.DIR_EAST,
            )
        )

    def test_all_eight_facing_half_planes(self) -> None:
        cases = (
            (dda.DIR_EAST, (34, 30)),
            (dda.DIR_NORTHEAST, (34, 26)),
            (dda.DIR_NORTH, (30, 26)),
            (dda.DIR_NORTHWEST, (26, 26)),
            (dda.DIR_WEST, (26, 30)),
            (dda.DIR_SOUTHWEST, (26, 34)),
            (dda.DIR_SOUTH, (30, 34)),
            (dda.DIR_SOUTHEAST, (34, 34)),
        )
        for direction, (x, y) in cases:
            with self.subTest(direction=direction):
                self.assertTrue(
                    self.sight(
                        (dda.fixed(x), dda.fixed(y)), direction=direction
                    )
                )
                opposite = (60 - x, 60 - y)
                self.assertFalse(
                    self.sight(
                        (dda.fixed(opposite[0]), dda.fixed(opposite[1])),
                        direction=direction,
                    )
                )

    def test_noise_bypasses_facing_but_not_walls(self) -> None:
        behind = (dda.fixed(26), dda.fixed(30))
        self.assertTrue(self.sight(behind, made_noise=True))
        self.assertFalse(
            self.sight(
                behind,
                made_noise=True,
                patch=(28, 30, dda.TILE_WALL),
            )
        )


if __name__ == "__main__":
    unittest.main()
