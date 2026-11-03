from __future__ import annotations

from pathlib import Path
import struct
import sys
import tempfile
import unittest


HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[3]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(PROJECT / "agonport/tools/wolf3d_assets"))

import prepare  # noqa: E402
import stage_oryx  # noqa: E402
from formats.level_package import ACTOR_SIZE, DOOR_SIZE, parse_package  # noqa: E402


class AcceptancePackageTests(unittest.TestCase):
    def state(self, level: int) -> bytes:
        return (
            PROJECT
            / f"agonport/assets/generated/wolf3d/levels/level_{level:02d}"
            / "state_medium.w3l"
        ).read_bytes()

    def test_catalog_covers_both_transitions_and_special_actor_scenes(self) -> None:
        self.assertEqual(
            [scenario.name for scenario in prepare.SCENARIOS],
            ["pushwall", "ordinary-transition", "secret-transition", "hans", "victory", "ghosts", "pause-resume"],
        )
        self.assertEqual(
            [scenario.initial_level for scenario in prepare.SCENARIOS],
            [0, 0, 9, 8, 8, 9, 0],
        )
        self.assertEqual(
            [scenario.invulnerable for scenario in prepare.SCENARIOS],
            [False, False, False, True, False, False, False],
        )
        self.assertFalse(prepare.SCENARIOS[3].one_hit_hans)
        self.assertEqual(
            stage_oryx.SCENARIOS,
            tuple(scenario.name for scenario in prepare.SCENARIOS),
        )

    def test_pushwall_pose_faces_real_e1l1_secret_wall(self) -> None:
        scenario = prepare.SCENARIOS[0]
        package = parse_package(prepare.patch_state(self.state(0), scenario))
        x, y, angle = struct.unpack("<iiH", package.player_pose)
        self.assertEqual((x >> 16, y >> 16, angle), (10, 14, 90))
        self.assertEqual(package.sections["paths"][13 * 64 + 10], 0xFD)
        self.assertEqual(package.sections["tilemap"][13 * 64 + 10], 4)

    def test_normal_transition_pose_is_inside_real_e1l1_elevator(self) -> None:
        scenario = prepare.SCENARIOS[1]
        package = parse_package(prepare.patch_state(self.state(0), scenario))
        x, y, angle = struct.unpack("<iiH", package.player_pose)
        self.assertEqual((x >> 16, y >> 16, angle), (25, 47, 0))

    def test_hans_pose_preserves_real_boss(self) -> None:
        scenario = prepare.SCENARIOS[3]
        package = parse_package(prepare.patch_state(self.state(8), scenario))
        x, y, angle = struct.unpack("<iiH", package.player_pose)
        self.assertEqual((x >> 16, y >> 16, angle), (34, 17, 90))
        self.assertEqual(package.sections["areas"][17 * 64 + 34], 2)

        actors = package.sections["actors"]
        classes = [actors[index * ACTOR_SIZE + 13]
                   for index in range(package.actor_count)]
        self.assertEqual(classes.count(7), 1)
        boss = classes.index(7) * ACTOR_SIZE
        self.assertEqual(
            tuple(actors[boss + offset] for offset in range(8, 15)),
            (34, 14, 3, 6, 0, 7, 0x41),
        )
        self.assertEqual(struct.unpack_from("<HH", actors, boss + 15), (0, 15))
        self.assertEqual(struct.unpack_from("<h", actors, boss + 25)[0], 1050)

        doors = package.sections["doors"]
        records = [
            struct.unpack_from("<BBBBBHBBB", doors, index * DOOR_SIZE)
            for index in range(package.door_count)
        ]
        entrance = [record for record in records if record[:2] == (34, 15)]
        self.assertEqual(entrance, [(34, 15, 0, 0, 0, 0, 121, 3, 2)])

    def test_hans_keeps_canonical_hit_pool_for_each_difficulty(self) -> None:
        scenario = prepare.SCENARIOS[3]
        expected = {
            "baby": 850,
            "easy": 950,
            "medium": 1050,
            "hard": 1200,
        }
        root = PROJECT / "agonport/assets/generated/wolf3d/levels/level_08"
        for name, hitpoints in expected.items():
            with self.subTest(difficulty=name):
                package = parse_package(prepare.patch_state(
                    (root / f"state_{name}.w3l").read_bytes(), scenario
                ))
                actors = package.sections["actors"]
                bosses = [
                    index for index in range(package.actor_count)
                    if actors[index * ACTOR_SIZE + 13] == 7
                ]
                self.assertEqual(len(bosses), 1)
                offset = bosses[0] * ACTOR_SIZE
                self.assertEqual(
                    struct.unpack_from("<h", actors, offset + 25)[0],
                    hitpoints,
                )

    def test_victory_pose_faces_real_e1l9_exit_tiles(self) -> None:
        scenario = prepare.SCENARIOS[4]
        package = parse_package(prepare.patch_state(self.state(8), scenario))
        x, y, angle = struct.unpack("<iiH", package.player_pose)
        self.assertEqual((x >> 16, y >> 16, angle), (34, 8, 90))
        paths = package.sections["paths"]
        self.assertEqual(
            [(column, 7) for column in (33, 34, 35)],
            [(index % 64, index // 64)
             for index, value in enumerate(paths) if value == 0xFE],
        )

    def test_ghost_scene_has_four_live_original_ghost_states(self) -> None:
        scenario = prepare.SCENARIOS[5]
        package = parse_package(prepare.patch_state(self.state(9), scenario))
        actors = package.sections["actors"]
        observed = []
        for index in range(4):
            record = actors[index * ACTOR_SIZE : (index + 1) * ACTOR_SIZE]
            observed.append((
                record[12],
                record[13],
                record[14],
                struct.unpack_from("<H", record, 17)[0],
            ))
        self.assertEqual(
            observed,
            [(1, 15, 0x40, state) for state in (11, 12, 13, 14)],
        )

    def test_synthetic_ghost_frames_are_opaque_distinct_test_art(self) -> None:
        first = prepare.ghost_proxy_pixels(0xC3, 0)
        second = prepare.ghost_proxy_pixels(0xC3, 1)
        self.assertEqual(len(first), 64 * 64)
        self.assertEqual(first[0], 0)
        self.assertIn(0xC3, first)
        self.assertIn(0xFF, first)
        self.assertNotEqual(first, second)

    def test_ghost_container_adds_all_missing_shape_buffers(self) -> None:
        source = (
            PROJECT / "agonport/assets/generated/wolf3d/levels/level_09"
        )
        with tempfile.TemporaryDirectory() as name:
            target = Path(name) / "level_09"
            target.mkdir()
            (target / "sprites.jsonl").write_bytes(
                (source / "sprites.jsonl").read_bytes()
            )
            prepare.build_ghost_sprite_container(target, Path(name))
            data = (target / "sprites.agnb").read_bytes()
        self.assertTrue(data.startswith(b"RIFF"))
        self.assertEqual(data[8:12], b"AGNB")
        for shape in prepare.GHOST_SHAPES:
            marker = b"BHDR\x02\x00\x00\x00" + struct.pack(
                "<H", prepare.buffer_id_for(prepare.KIND_SPRITE, shape)
            )
            self.assertEqual(data.count(marker), 1)


if __name__ == "__main__":
    unittest.main()
