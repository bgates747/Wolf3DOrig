from __future__ import annotations

import sys
import unittest
from pathlib import Path


TOOLS_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS_ROOT))

from scripts.build_level_manifest import (
    EPISODE_1_VICTORY_SHAPENUMS,
    CREATURE_RUNTIME_DROP_SHAPENUMS,
    PLAYER_WEAPON_SHAPENUMS,
    add_level_runtime_shapes,
    scope_level,
)


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

    def test_ss_scope_includes_both_inventory_dependent_death_drops(self) -> None:
        plane1 = self.empty_plane()
        plane1[10][47] = 126  # SS stand, present on every difficulty
        _, _, shapes = scope_level(self.empty_plane(), plane1, 435)
        self.assertEqual(CREATURE_RUNTIME_DROP_SHAPENUMS["SS"], {28, 29})
        self.assertTrue({28, 29}.issubset(shapes))

    def test_ordinary_enemy_and_hans_scopes_include_runtime_drops(self) -> None:
        plane1 = self.empty_plane()
        plane1[1][1] = 108  # guard stand -> clip2
        plane1[2][2] = 214  # Hans -> gold key
        _, _, shapes = scope_level(self.empty_plane(), plane1, 435)
        self.assertTrue({22, 28}.issubset(shapes))

    def test_runtime_drop_shapes_respect_truncated_vswap_domain(self) -> None:
        plane1 = self.empty_plane()
        plane1[10][47] = 126
        _, _, shapes = scope_level(self.empty_plane(), plane1, 28)
        self.assertIn(28, shapes)
        self.assertNotIn(29, shapes)

    def test_only_boss_floor_adds_complete_bj_victory_animation(self) -> None:
        boss_shapes: set[int] = set()
        ordinary_shapes: set[int] = set()
        add_level_runtime_shapes(8, boss_shapes, 435)
        add_level_runtime_shapes(7, ordinary_shapes, 435)
        self.assertEqual(set(EPISODE_1_VICTORY_SHAPENUMS), boss_shapes)
        self.assertEqual(set(), ordinary_shapes)

    def test_bj_victory_shapes_respect_truncated_vswap_domain(self) -> None:
        shapes: set[int] = set()
        add_level_runtime_shapes(8, shapes, 411)
        self.assertEqual(set(range(408, 412)), shapes)


if __name__ == "__main__":
    unittest.main()
