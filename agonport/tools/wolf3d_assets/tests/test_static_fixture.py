from __future__ import annotations

import struct
import sys
import unittest
from pathlib import Path

TOOLS_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS_ROOT))

from formats import mapfile, staticinfo
from scripts.gen_render_fixture import (
    BUFFERED_WOLF3D,
    SUB_INIT_LEVEL,
    SUB_RENDER_FRAME,
    SUB_SET_PLAYER_POSE,
    SUB_SET_VIEW_WEAPON,
    SUB_SET_STATIC,
    build_command_stream,
    build_statics,
)


class StaticMetadataTests(unittest.TestCase):
    def test_non_spear_table_matches_original_shape_and_kind_anchors(self) -> None:
        self.assertEqual(len(staticinfo.STATIC_INFO), 49)
        self.assertEqual(
            [entry.shapenum for entry in staticinfo.STATIC_INFO],
            list(range(2, 50)) + [28],
        )
        self.assertEqual(staticinfo.STATIC_INFO[0].kind, staticinfo.StatKind.DRESSING)
        self.assertEqual(staticinfo.STATIC_INFO[1].kind, staticinfo.StatKind.BLOCK)
        self.assertEqual(staticinfo.STATIC_INFO[20].kind, staticinfo.StatKind.BO_KEY1)
        self.assertEqual(staticinfo.STATIC_INFO[48].kind, staticinfo.StatKind.BO_CLIP2)

    def test_block_and_bonus_cases_match_spawn_static(self) -> None:
        blocking_indices = {
            1, 2, 3, 5, 7, 8, 10, 11, 12, 13, 16, 17, 18, 22,
            35, 36, 37, 39, 40, 45, 46,
        }
        bonus_indices = {6, 20, 21, *range(24, 35), 38}
        self.assertEqual(
            {i for i, entry in enumerate(staticinfo.STATIC_INFO) if entry.blocking},
            blocking_indices,
        )
        self.assertEqual(
            {i for i, entry in enumerate(staticinfo.STATIC_INFO) if entry.bonus},
            bonus_indices,
        )
        # bo_clip2 is a runtime-drop lookup entry, omitted from SpawnStatic's
        # FL_BONUS switch in the original source.
        self.assertFalse(staticinfo.STATIC_INFO[48].bonus)

    def test_plane1_bounds(self) -> None:
        self.assertIsNone(staticinfo.from_plane1(22))
        self.assertIs(staticinfo.from_plane1(23), staticinfo.STATIC_INFO[0])
        self.assertIs(staticinfo.from_plane1(71), staticinfo.STATIC_INFO[48])
        self.assertIsNone(staticinfo.from_plane1(72))


class StaticFixtureTests(unittest.TestCase):
    @staticmethod
    def empty_plane() -> list[list[int]]:
        return [
            [0 for _x in range(mapfile.MAP_WIDTH)]
            for _y in range(mapfile.MAP_HEIGHT)
        ]

    def test_row_major_seeds_flags_itemnumbers_and_blocking_bits(self) -> None:
        plane1 = self.empty_plane()
        plane1[1][9] = 29   # index 6: bo_alpo pickup
        plane1[1][2] = 24   # index 1: blocking barrel, encountered first
        plane1[3][0] = 71   # index 48: duplicate bo_clip2, not a map bonus

        statics, blocking = build_statics(plane1)

        self.assertEqual(
            statics,
            [
                (2, 1, 3, 0, 0),
                (9, 1, 8, staticinfo.FL_BONUS, int(staticinfo.StatKind.BO_ALPO)),
                (0, 3, 28, 0, 0),
            ],
        )
        self.assertEqual(len(blocking), 512)
        barrel_bit = mapfile.MAP_WIDTH + 2
        self.assertEqual(blocking[barrel_bit >> 3], 1 << (barrel_bit & 7))
        self.assertEqual(sum(byte.bit_count() for byte in blocking), 1)

    def test_set_static_wire_records_precede_player_and_render(self) -> None:
        statics = [
            (2, 1, 3, 0, 0),
            (9, 1, 8, staticinfo.FL_BONUS, int(staticinfo.StatKind.BO_ALPO)),
        ]
        stream = build_command_stream(1, 2, [], statics, 0x12345, 0x23456, 90)

        header_prefix = bytes((23, 0, 0xA0, 1, 0, BUFFERED_WOLF3D))
        self.assertEqual(stream[:7], header_prefix + bytes((SUB_INIT_LEVEL,)))

        first_static = 9
        second_static = first_static + 14
        player = second_static + 14
        weapon = player + 17
        render = weapon + 9
        self.assertEqual(stream[first_static:first_static + 7], header_prefix + bytes((SUB_SET_STATIC,)))
        self.assertEqual(stream[first_static + 7:first_static + 14], bytes((0, 0, 2, 1, 3, 0, 0)))
        self.assertEqual(stream[second_static:second_static + 7], header_prefix + bytes((SUB_SET_STATIC,)))
        self.assertEqual(
            stream[second_static + 7:second_static + 14],
            bytes((1, 0, 9, 1, 8, 0, staticinfo.FL_BONUS)),
        )
        self.assertEqual(stream[player:player + 7], header_prefix + bytes((SUB_SET_PLAYER_POSE,)))
        self.assertEqual(stream[weapon:weapon + 7], header_prefix + bytes((SUB_SET_VIEW_WEAPON,)))
        self.assertEqual(struct.unpack_from("<h", stream, weapon + 7)[0], 421)
        self.assertEqual(stream[render:render + 7], header_prefix + bytes((SUB_RENDER_FRAME,)))
        self.assertEqual(len(stream), render + 7)

    def test_plane_dimensions_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "64x64"):
            build_statics([[0]])


if __name__ == "__main__":
    unittest.main()
