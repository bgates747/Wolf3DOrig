from __future__ import annotations

import sys
import unittest
from pathlib import Path

TOOLS_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(TOOLS_ROOT))

from formats import actorinfo, mapfile  # noqa: E402
from formats.level_package import (  # noqa: E402
    HEADER_SIZE,
    MAX_DOORS,
    MAX_NONPLAYER_ACTORS,
    MAX_PACKAGE_SIZE,
    MAX_STATICS,
    parse_package,
)
from scripts.build_level_packages import build_one  # noqa: E402

DATA_DIR = PROJECT_ROOT / "orig/data"


class RuntimeLevelPackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.maphead = mapfile.read_maphead((DATA_DIR / "MAPHEAD.WL1").read_bytes())
        cls.gamemaps = (DATA_DIR / "GAMEMAPS.WL1").read_bytes()

    def level(self, index: int) -> mapfile.Level:
        return mapfile.read_level(self.gamemaps, self.maphead, index, self.maphead.magic)

    def test_all_shareware_levels_and_difficulties_round_trip(self) -> None:
        packages = 0
        maximum_doors = 0
        maximum_statics = 0
        maximum_actors = 0
        for level_index, offset in enumerate(self.maphead.level_offsets):
            if offset <= 0:
                continue
            level = self.level(level_index)
            for difficulty in actorinfo.Difficulty:
                encoded = build_one(level, level_index, difficulty)
                decoded = parse_package(encoded)
                self.assertEqual(decoded.level, level_index)
                self.assertEqual(decoded.difficulty, int(difficulty))
                self.assertLessEqual(len(encoded), MAX_PACKAGE_SIZE)
                self.assertGreaterEqual(len(encoded), HEADER_SIZE)
                maximum_doors = max(maximum_doors, decoded.door_count)
                maximum_statics = max(maximum_statics, decoded.static_count)
                maximum_actors = max(maximum_actors, decoded.actor_count)
                packages += 1
        self.assertEqual(packages, 40)
        self.assertEqual((maximum_doors, maximum_statics, maximum_actors), (47, 344, 109))
        self.assertLessEqual(maximum_doors, MAX_DOORS)
        self.assertLessEqual(maximum_statics, MAX_STATICS)
        self.assertLessEqual(maximum_actors, MAX_NONPLAYER_ACTORS)

    def test_actor_population_varies_without_changing_world_geometry(self) -> None:
        level = self.level(4)
        easy = parse_package(build_one(level, 4, actorinfo.Difficulty.EASY))
        hard = parse_package(build_one(level, 4, actorinfo.Difficulty.HARD))
        self.assertLess(easy.actor_count, hard.actor_count)
        for name in ("doors", "statics", "blocking", "areas", "paths", "tilemap"):
            self.assertEqual(easy.sections[name], hard.sections[name])

    def test_reserved_header_bytes_are_rejected(self) -> None:
        encoded = bytearray(build_one(self.level(0), 0, actorinfo.Difficulty.MEDIUM))
        encoded[63] = 1
        with self.assertRaisesRegex(ValueError, "reserved"):
            parse_package(bytes(encoded))

    def test_truncation_and_noncanonical_offsets_are_rejected(self) -> None:
        encoded = build_one(self.level(0), 0, actorinfo.Difficulty.MEDIUM)
        with self.assertRaisesRegex(ValueError, "declared size"):
            parse_package(encoded[:-1])
        malformed = bytearray(encoded)
        malformed[26] += 1
        with self.assertRaisesRegex(ValueError, "doors section"):
            parse_package(bytes(malformed))


if __name__ == "__main__":
    unittest.main()
