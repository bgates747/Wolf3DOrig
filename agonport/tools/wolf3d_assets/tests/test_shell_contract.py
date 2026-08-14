from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

TOOLS_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(TOOLS_ROOT))

from formats.palette import WOLF3D_PALETTE_RGB888  # noqa: E402
from formats.shell import (  # noqa: E402
    BKGDCOLOR,
    BORDCOLOR,
    COMPOSED_DEACTIVE_RGB,
    EPISODE_UNAVAILABLE_MESSAGE,
    SHELL_CHUNKS,
    SHELL_CHUNK_NAMES,
    SHELL_COMPOSITE_BUFFER_IDS,
    SHELL_EXPECTED_DIMENSIONS,
    STRIPE,
    chunk_buffer_id,
    decode_wolf_font,
)
from formats.vgagraph import read_vgagraph  # noqa: E402
from scripts.build_shell_assets import build_shell_assets  # noqa: E402

DATA_DIR = PROJECT_ROOT / "orig/data"
PALETTE_FILE = TOOLS_ROOT / "palettes/Agon64.gpl"

EXPECTED_COMPOSITES = {
    "main_base": (0x4300, 320, 200, 0, 0),
    "episode_base": (0x4301, 320, 200, 0, 0),
    "difficulty_base": (0x4302, 320, 200, 0, 0),
    "episode_unavailable_notice": (0x4303, 251, 63, 35, 69),
    "main_new_game_selected": (0x4310, 82, 13, 100, 55),
    "main_quit_selected": (0x4311, 35, 13, 100, 172),
    "episode_1_selected": (0x4320, 215, 26, 98, 23),
    "episode_2_selected": (0x4321, 190, 26, 98, 49),
    "episode_3_selected": (0x4322, 140, 26, 98, 75),
    "episode_4_selected": (0x4323, 126, 26, 98, 101),
    "episode_5_selected": (0x4324, 175, 26, 98, 127),
    "episode_6_selected": (0x4325, 123, 26, 98, 153),
    "difficulty_baby_selected": (0x4330, 157, 13, 74, 100),
    "difficulty_easy_selected": (0x4331, 126, 13, 74, 113),
    "difficulty_normal_selected": (0x4332, 111, 13, 74, 126),
    "difficulty_hard_selected": (0x4333, 189, 13, 74, 139),
}


def _archive():
    return read_vgagraph(
        DATA_DIR / "VGADICT.WL1",
        DATA_DIR / "VGAHEAD.WL1",
        DATA_DIR / "VGAGRAPH.WL1",
    )


class ShellArchiveTests(unittest.TestCase):
    def test_real_v14_chunk_dimensions_and_false_backdrop_is_absent(self) -> None:
        archive = _archive()
        self.assertNotIn(21, SHELL_CHUNKS)
        self.assertNotIn(21, SHELL_CHUNK_NAMES)
        with self.assertRaisesRegex(ValueError, "not in the staged shell set"):
            chunk_buffer_id(21)
        for chunk_id in SHELL_CHUNKS:
            self.assertEqual(
                archive.decode_picture(chunk_id).size,
                SHELL_EXPECTED_DIMENSIONS[chunk_id],
            )

    def test_original_control_panel_font_contract(self) -> None:
        font = decode_wolf_font(_archive())
        self.assertEqual(font.height, 13)
        self.assertEqual(font.glyph_width("A"), 10)
        self.assertEqual(font.glyph_width(" "), 8)
        self.assertEqual(font.measure("New Game"), (82, 13))
        self.assertEqual(font.measure(EPISODE_UNAVAILABLE_MESSAGE), (240, 52))
        width, height, glyph = font.glyph_mask("A")
        self.assertEqual((width, height, len(glyph)), (10, 13, 130))
        self.assertTrue(any(glyph))

    def test_build_has_stable_raw_and_composed_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            out = Path(temporary) / "shell"
            entries = build_shell_assets(DATA_DIR, out, PALETTE_FILE, override_dir=None)
            self.assertEqual(len(entries), len(SHELL_CHUNKS) + len(EXPECTED_COMPOSITES))
            self.assertEqual(
                len({entry.bufferId for entry in entries}),
                len(entries),
            )

            raw = {entry.name: entry for entry in entries if entry.chunkId is not None}
            self.assertEqual(
                {entry.chunkId for entry in raw.values()}, set(SHELL_CHUNKS)
            )
            self.assertEqual(
                {entry.bufferId for entry in raw.values()},
                {chunk_buffer_id(chunk_id) for chunk_id in SHELL_CHUNKS},
            )
            self.assertEqual(raw["title"].bufferId, 0x4263)

            composed = {
                entry.name: entry for entry in entries if entry.chunkId is None
            }
            self.assertEqual(set(composed), set(EXPECTED_COMPOSITES))
            self.assertEqual(
                SHELL_COMPOSITE_BUFFER_IDS,
                {
                    name: contract[0]
                    for name, contract in EXPECTED_COMPOSITES.items()
                },
            )
            for name, (buffer_id, width, height, x, y) in EXPECTED_COMPOSITES.items():
                entry = composed[name]
                self.assertEqual(
                    (
                        entry.bufferId,
                        entry.width,
                        entry.height,
                        entry.plotX,
                        entry.plotY,
                    ),
                    (buffer_id, width, height, x, y),
                )

            manifest = [
                json.loads(line)
                for line in (out / "shell_assets.jsonl").read_text().splitlines()
            ]
            self.assertEqual(len(manifest), len(entries))
            self.assertTrue((out / "shell.agnb").read_bytes().startswith(b"RIFF"))
            constants = (out / "wolf3d_shell_assets.inc").read_text()
            self.assertIn("W3D_SHELL_TITLE_BUFFER: equ $4263", constants)
            self.assertIn("W3D_SHELL_MAIN_BASE_BUFFER: equ $4300", constants)
            self.assertIn("W3D_SHELL_MAIN_BASE_WIDTH: equ 320", constants)
            self.assertIn(
                "W3D_SHELL_EPISODE_UNAVAILABLE_NOTICE_X: equ 35", constants
            )

            with Image.open(out / "orig/main_base.png") as main_base:
                self.assertEqual(main_base.size, (320, 200))
                self.assertEqual(
                    main_base.getpixel((0, 0)), WOLF3D_PALETTE_RGB888[BORDCOLOR]
                )
                self.assertEqual(main_base.getpixel((0, 10)), WOLF3D_PALETTE_RGB888[0])
                self.assertEqual(
                    main_base.getpixel((0, 32)), WOLF3D_PALETTE_RGB888[STRIPE]
                )
                self.assertEqual(
                    main_base.getpixel((80, 80)), WOLF3D_PALETTE_RGB888[BKGDCOLOR]
                )

            # The original DEACTIVE and BKGDCOLOR reds collapse onto the same
            # Agon64 entry.  Verify a real pixel in the disabled "Sound" S
            # uses the deliberately brighter composed color after conversion.
            font = decode_wolf_font(_archive())
            width, _, mask = font.glyph_mask("S")
            glyph_offset = next(index for index, value in enumerate(mask) if value)
            glyph_x = 100 + glyph_offset % width
            glyph_y = 68 + glyph_offset // width
            with Image.open(out / "processed/main_base.png") as processed_main:
                background = processed_main.getpixel((99, 68))[:3]
                disabled_glyph = processed_main.getpixel((glyph_x, glyph_y))[:3]
                self.assertEqual(background, (85, 0, 0))
                self.assertEqual(disabled_glyph, COMPOSED_DEACTIVE_RGB)
                self.assertNotEqual(disabled_glyph, background)

    def test_override_dimensions_are_enforced(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            overrides = root / "overrides"
            overrides.mkdir()
            Image.new("RGB", (1, 1)).save(overrides / "title.png")
            with self.assertRaisesRegex(ValueError, "expected"):
                build_shell_assets(
                    DATA_DIR, root / "out", PALETTE_FILE, override_dir=overrides
                )


if __name__ == "__main__":
    unittest.main()
