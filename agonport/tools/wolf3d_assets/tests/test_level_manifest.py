from __future__ import annotations

import sys
import unittest
from pathlib import Path


TOOLS_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS_ROOT))

from scripts.build_level_manifest import PLAYER_WEAPON_SHAPENUMS, scope_level


class LevelManifestCombatAssetsTests(unittest.TestCase):
    @staticmethod
    def empty_plane() -> list[list[int]]:
        return [[0 for _ in range(64)] for _ in range(64)]

    def test_every_level_includes_all_first_person_weapon_frames(self) -> None:
        _, _, shapes = scope_level(self.empty_plane(), self.empty_plane(), 435)
        self.assertEqual(set(PLAYER_WEAPON_SHAPENUMS), shapes)

    def test_weapon_frames_are_clipped_to_the_real_vswap_domain(self) -> None:
        _, _, shapes = scope_level(self.empty_plane(), self.empty_plane(), 425)
        self.assertEqual(set(range(416, 426)), shapes)

    def test_map_scoped_sprites_are_retained_alongside_weapon_frames(self) -> None:
        plane1 = self.empty_plane()
        plane1[7][9] = 23  # SPR_STAT_0 / shapenum 2
        _, _, shapes = scope_level(self.empty_plane(), plane1, 435)
        self.assertIn(2, shapes)
        self.assertTrue(set(PLAYER_WEAPON_SHAPENUMS).issubset(shapes))


if __name__ == "__main__":
    unittest.main()
