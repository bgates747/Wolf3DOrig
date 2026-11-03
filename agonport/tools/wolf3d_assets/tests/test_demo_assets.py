from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest


TOOLS_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(TOOLS_ROOT))

from formats.demo import DEMO_MAPS, find_recorded_demos
from formats.vgagraph import read_vgagraph
from scripts.build_demo_assets import (
    DEFAULT_DATA,
    DEFAULT_INCLUDE,
    build_assets,
    write_assets,
)


class DemoAssetTests(unittest.TestCase):
    def test_canonical_archive_contains_the_four_recorded_demos(self) -> None:
        archive = read_vgagraph(
            DEFAULT_DATA / "VGADICT.WL1",
            DEFAULT_DATA / "VGAHEAD.WL1",
            DEFAULT_DATA / "VGAGRAPH.WL1",
        )
        demos = find_recorded_demos(archive)
        self.assertEqual([demo.chunk_id for demo in demos], [151, 152, 153, 154])
        self.assertEqual(tuple(demo.map_index for demo in demos), DEMO_MAPS)
        self.assertEqual([len(demo.expanded) for demo in demos], [3460, 3856, 2017, 1903])
        self.assertEqual([demo.record_count for demo in demos], [1152, 1284, 671, 633])
        self.assertEqual([demo.reserved for demo in demos], [0, 19, 19, 19])

    def test_generated_include_and_manifest_are_deterministic_and_current(self) -> None:
        text, manifest = build_assets()
        second_text, second_manifest = build_assets()
        self.assertEqual((text, manifest), (second_text, second_manifest))
        self.assertEqual(DEFAULT_INCLUDE.read_text(), text)
        self.assertEqual([item["mapIndex"] for item in manifest["demos"]], [0, 2, 4, 6])
        self.assertIn("w3d_demo_stream_3_end:", text)

        with tempfile.TemporaryDirectory() as name:
            output = Path(name) / "demos"
            include = Path(name) / "wolf3d_demo_assets.inc"
            write_assets(output, include, text, manifest)
            self.assertEqual(include.read_text(), text)
            self.assertEqual(
                json.loads((output / "demo_manifest.json").read_text()), manifest
            )


if __name__ == "__main__":
    unittest.main()
