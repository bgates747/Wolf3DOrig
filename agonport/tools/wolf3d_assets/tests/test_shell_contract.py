from __future__ import annotations

import json
import hashlib
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

TOOLS_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(TOOLS_ROOT))

from formats.palette import WOLF3D_PALETTE_RGB888  # noqa: E402
from formats.omf import OmfError, extract_ledata_segment  # noqa: E402
from formats.article import (  # noqa: E402
    ARTICLE_BUFFER_BASE,
    ARTICLE_PAGE_COUNT,
    END_ARTICLE_BUFFER_BASE,
    END_ARTICLE_PAGE_COUNT,
    render_end_article,
    render_help_article,
)
from formats.shell import (  # noqa: E402
    BKGDCOLOR,
    BORDCOLOR,
    CHEATER_MESSAGE,
    COMPOSED_DEACTIVE_RGB,
    CURRENT_GAME_MESSAGE,
    END_GAME_MESSAGE,
    EPISODE_UNAVAILABLE_MESSAGE,
    HIGHSCORE_FONT_CHUNK,
    HIGHSCORE_GLYPH_BUFFER_BASE,
    HIGHSCORE_GLYPH_FIRST,
    HIGHSCORE_GLYPH_LAST,
    KEEN_MESSAGE,
    QUIT_MESSAGES,
    SAVING_MESSAGE,
    SHELL_CHUNKS,
    SHELL_CHUNK_NAMES,
    SHELL_COMPOSITE_BUFFER_IDS,
    SHELL_EXPECTED_DIMENSIONS,
    SHELL_SIGNON_BUFFER_ID,
    SHELL_SIGNON_SIZE,
    STRIPE,
    chunk_buffer_id,
    decode_wolf_font,
    highscore_glyph_buffer_id,
)
from formats.vgagraph import read_vgagraph  # noqa: E402
from scripts.build_shell_assets import build_shell_assets  # noqa: E402

DATA_DIR = PROJECT_ROOT / "orig/data"
SIGNON_OBJ = PROJECT_ROOT / "orig/src/WOLFSRC/OBJ/SIGNON.OBJ"
PALETTE_FILE = TOOLS_ROOT / "palettes/Agon64.gpl"
TRACKED_CONSTANTS = PROJECT_ROOT / "src/asm/wolf3d/src/wolf3d_shell_assets.inc"

EXPECTED_COMPOSITES = {
    "main_base": (0x4300, 320, 200, 0, 0),
    "episode_base": (0x4301, 320, 200, 0, 0),
    "difficulty_base": (0x4302, 320, 200, 0, 0),
    "episode_unavailable_notice": (0x4303, 251, 63, 35, 69),
    "high_scores_base": (0x4304, 320, 200, 0, 0),
    "main_ingame_tail": (0x4305, 145, 44, 96, 143),
    "end_game_notice": (0x4306, 215, 50, 53, 76),
    "main_save_game_active": (0x4307, 90, 13, 100, 107),
    "main_new_game_selected": (0x4310, 82, 13, 100, 55),
    "main_quit_selected": (0x4311, 35, 13, 100, 172),
    "main_view_scores_selected": (0x4312, 105, 13, 100, 146),
    "main_end_game_selected": (0x4313, 80, 13, 100, 146),
    "main_back_to_game_selected": (0x4314, 118, 13, 100, 159),
    "main_load_game_selected": (0x4315, 90, 13, 100, 94),
    "main_save_game_selected": (0x4316, 90, 13, 100, 107),
    "main_sound_selected": (0x4317, 50, 13, 100, 68),
    "main_control_selected": (0x4318, 64, 13, 100, 81),
    "main_change_view_selected": (0x4319, 105, 13, 100, 120),
    "main_read_this_selected": (0x431A, 87, 13, 100, 133),
    "main_back_to_demo_selected": (0x431B, 118, 13, 100, 159),
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
    "sound_on_page": (0x4340, 320, 200, 0, 0),
    "sound_off_page": (0x4341, 320, 200, 0, 0),
    "control_page": (0x4342, 320, 200, 0, 0),
    "change_view_page": (0x4343, 320, 200, 0, 0),
    "read_this_page": (0x4344, 320, 200, 0, 0),
    "sound_on_music_off_page": (0x4345, 320, 200, 0, 0),
    "sound_off_music_off_page": (0x4346, 320, 200, 0, 0),
    "quit_notice_0": (0x4350, 206, 50, 58, 76),
    "quit_notice_1": (0x4351, 151, 37, 85, 82),
    "quit_notice_2": (0x4352, 247, 37, 37, 82),
    "quit_notice_3": (0x4353, 209, 37, 56, 82),
    "quit_notice_4": (0x4354, 251, 50, 35, 76),
    "quit_notice_5": (0x4355, 264, 37, 29, 82),
    "quit_notice_6": (0x4356, 156, 37, 83, 82),
    "quit_notice_7": (0x4357, 276, 50, 23, 76),
    "quit_notice_8": (0x4358, 284, 37, 19, 82),
    "current_game_notice": (0x4359, 206, 50, 58, 76),
    "saving_notice": (0x435A, 88, 24, 117, 89),
    "quick_load_notice": (0x435B, 284, 37, 19, 82),
    "cheater_notice": (0x435C, 266, 89, 28, 56),
    "keen_notice": (0x435D, 274, 63, 24, 69),
}


def _archive():
    return read_vgagraph(
        DATA_DIR / "VGADICT.WL1",
        DATA_DIR / "VGAHEAD.WL1",
        DATA_DIR / "VGAGRAPH.WL1",
    )


class ShellArchiveTests(unittest.TestCase):
    def test_linked_signon_omf_contract(self) -> None:
        pixels = extract_ledata_segment(
            SIGNON_OBJ.read_bytes(), segment_index=1, expected_size=320 * 200
        )
        self.assertEqual(len(pixels), 64_000)
        self.assertEqual(
            hashlib.sha256(pixels).hexdigest(),
            "4fd711cdde7929645a46dd572ab61feacc8d3b79844250835b0ce87312a2c999",
        )
        self.assertEqual(pixels[0], 0x29)

    def test_omf_extractor_rejects_gaps_overlaps_and_bad_checksums(self) -> None:
        def record(payload: bytes, checksum: int = 0) -> bytes:
            length = len(payload) + 1
            return bytes((0xA0, length & 0xFF, length >> 8)) + payload + bytes((checksum,))

        gap = record(b"\x01\x00\x00A")
        with self.assertRaisesRegex(OmfError, "gaps"):
            extract_ledata_segment(gap, segment_index=1, expected_size=2)

        overlap = record(b"\x01\x00\x00AB") + record(b"\x01\x01\x00C")
        with self.assertRaisesRegex(OmfError, "overlap"):
            extract_ledata_segment(overlap, segment_index=1, expected_size=2)

        bad_checksum = record(b"\x01\x00\x00A", checksum=1)
        with self.assertRaisesRegex(OmfError, "checksum"):
            extract_ledata_segment(
                bad_checksum, segment_index=1, expected_size=1
            )

        two_byte_index = record(b"\x81\x01\x00\x00Z")
        self.assertEqual(
            extract_ledata_segment(
                two_byte_index, segment_index=0x101, expected_size=1
            ),
            b"Z",
        )

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
        self.assertEqual(font.measure(END_GAME_MESSAGE), (204, 39))
        self.assertEqual(font.measure(CURRENT_GAME_MESSAGE), (195, 39))
        self.assertEqual(font.measure(SAVING_MESSAGE), (67, 13))
        self.assertEqual(len(QUIT_MESSAGES), 9)
        self.assertEqual(font.measure(QUIT_MESSAGES[0]), (195, 39))
        self.assertEqual(font.measure(QUIT_MESSAGES[8]), (263, 26))
        width, height, glyph = font.glyph_mask("A")
        self.assertEqual((width, height, len(glyph)), (10, 13, 130))
        self.assertTrue(any(glyph))

    def test_original_help_article_layout_contract(self) -> None:
        archive = _archive()
        pages = render_help_article(archive, decode_wolf_font(archive, 1))
        self.assertEqual(len(pages), ARTICLE_PAGE_COUNT)
        self.assertTrue(all(page.size == (320, 200) for page in pages))
        self.assertEqual(
            hashlib.sha256(pages[0].tobytes()).hexdigest(),
            "239597d60bb0e73e11aeeb648c9cca04f798c21d695dfee48bf9874528176a3f",
        )
        self.assertEqual(
            hashlib.sha256(pages[-1].tobytes()).hexdigest(),
            "0749d9287fe586eea04ddda1ab0796aee313c6feac6b810987706bd7a63cbab2",
        )

    def test_original_end_article_layout_contract(self) -> None:
        archive = _archive()
        pages = render_end_article(archive, decode_wolf_font(archive, 1))
        self.assertEqual(len(pages), END_ARTICLE_PAGE_COUNT)
        self.assertTrue(all(page.size == (320, 200) for page in pages))
        self.assertEqual(
            hashlib.sha256(pages[0].tobytes()).hexdigest(),
            "051259805f8638f0c0cc4f39e332ba91200a8143788bfc624fd5fbfd1a4438fa",
        )
        self.assertEqual(
            hashlib.sha256(pages[1].tobytes()).hexdigest(),
            "db0bdc962800954f27feec3610660085f7228aff1443f1bd4e6b7a0dec78c8cd",
        )

    def test_build_has_stable_raw_and_composed_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            out = Path(temporary) / "shell"
            entries = build_shell_assets(DATA_DIR, out, PALETTE_FILE, override_dir=None)
            self.assertEqual(
                len(entries),
                len(SHELL_CHUNKS)
                + len(EXPECTED_COMPOSITES)
                + 1
                + HIGHSCORE_GLYPH_LAST
                - HIGHSCORE_GLYPH_FIRST
                + 1,
            )
            self.assertEqual(
                len({entry.bufferId for entry in entries}),
                len(entries),
            )

            raw = {
                entry.name: entry
                for entry in entries
                if entry.name in SHELL_CHUNK_NAMES.values()
            }
            self.assertEqual(
                {entry.chunkId for entry in raw.values()}, set(SHELL_CHUNKS)
            )
            self.assertEqual(
                {entry.bufferId for entry in raw.values()},
                {chunk_buffer_id(chunk_id) for chunk_id in SHELL_CHUNKS},
            )
            self.assertEqual(raw["title"].bufferId, 0x4263)
            self.assertEqual(raw["pg13"].bufferId, 0x4264)
            self.assertEqual(
                (
                    raw["pg13"].width,
                    raw["pg13"].height,
                    raw["pg13"].plotX,
                    raw["pg13"].plotY,
                ),
                (88, 64, 216, 110),
            )
            self.assertEqual(raw["credits"].bufferId, 0x4265)
            self.assertEqual(raw["high_scores_heading"].bufferId, 0x4266)
            self.assertEqual(raw["paused"].bufferId, 0x4289)
            self.assertEqual(
                (raw["paused"].width, raw["paused"].height), (24, 32)
            )

            highscore_font = decode_wolf_font(_archive(), HIGHSCORE_FONT_CHUNK)
            glyphs = {
                entry.name: entry
                for entry in entries
                if entry.name.startswith("highscore_glyph_")
            }
            self.assertEqual(
                len(glyphs), HIGHSCORE_GLYPH_LAST - HIGHSCORE_GLYPH_FIRST + 1
            )
            for code in range(HIGHSCORE_GLYPH_FIRST, HIGHSCORE_GLYPH_LAST + 1):
                entry = glyphs[f"highscore_glyph_{code:03d}"]
                self.assertEqual(entry.chunkId, HIGHSCORE_FONT_CHUNK)
                self.assertEqual(entry.bufferId, highscore_glyph_buffer_id(code))
                self.assertEqual(entry.width, highscore_font.widths[code])
                self.assertEqual(entry.height, highscore_font.height)
            self.assertEqual(highscore_glyph_buffer_id(32), HIGHSCORE_GLYPH_BUFFER_BASE)
            self.assertEqual(highscore_font.widths[128], 2)
            self.assertEqual(list(highscore_font.widths[129:139]), [8] * 10)

            signon = next(entry for entry in entries if entry.name == "signon")
            self.assertEqual(signon.bufferId, SHELL_SIGNON_BUFFER_ID)
            self.assertEqual((signon.width, signon.height), SHELL_SIGNON_SIZE)
            self.assertEqual((signon.plotX, signon.plotY), (0, 0))
            self.assertIn("SIGNON.OBJ", signon.source)
            composed = {
                entry.name: entry
                for entry in entries
                if entry.chunkId is None and entry.name != "signon"
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
            self.assertTrue((out / "help.agnb").read_bytes().startswith(b"RIFF"))
            self.assertTrue((out / "end.agnb").read_bytes().startswith(b"RIFF"))
            help_manifest = [
                json.loads(line)
                for line in (out / "help_assets.jsonl").read_text().splitlines()
            ]
            self.assertEqual(len(help_manifest), ARTICLE_PAGE_COUNT)
            self.assertEqual(help_manifest[0]["bufferId"], ARTICLE_BUFFER_BASE)
            self.assertEqual(
                help_manifest[-1]["bufferId"],
                ARTICLE_BUFFER_BASE + ARTICLE_PAGE_COUNT - 1,
            )
            end_manifest = [
                json.loads(line)
                for line in (out / "end_assets.jsonl").read_text().splitlines()
            ]
            self.assertEqual(len(end_manifest), END_ARTICLE_PAGE_COUNT)
            self.assertEqual(end_manifest[0]["bufferId"], END_ARTICLE_BUFFER_BASE)
            self.assertEqual(
                end_manifest[-1]["bufferId"],
                END_ARTICLE_BUFFER_BASE + END_ARTICLE_PAGE_COUNT - 1,
            )
            constants = (out / "wolf3d_shell_assets.inc").read_text()
            self.assertEqual(constants, TRACKED_CONSTANTS.read_text())
            self.assertIn("W3D_SHELL_TITLE_BUFFER: equ $4263", constants)
            self.assertIn("W3D_SHELL_PG13_BUFFER: equ $4264", constants)
            self.assertIn("W3D_SHELL_PG13_X: equ 216", constants)
            self.assertIn("W3D_SHELL_PG13_Y: equ 110", constants)
            self.assertIn("W3D_SHELL_PAUSED_BUFFER: equ $4289", constants)
            self.assertIn("W3D_SHELL_SIGNON_BUFFER: equ $428A", constants)
            self.assertIn("W3D_SHELL_MAIN_BASE_BUFFER: equ $4300", constants)
            self.assertIn("W3D_SHELL_MAIN_BASE_WIDTH: equ 320", constants)
            self.assertIn("W3D_HELP_PAGE_BUFFER_BASE: equ $4600", constants)
            self.assertIn("W3D_HELP_PAGE_COUNT: equ 41", constants)
            self.assertIn("W3D_END_PAGE_BUFFER_BASE: equ $4629", constants)
            self.assertIn("W3D_END_PAGE_COUNT: equ 2", constants)
            self.assertIn("W3D_HIGHSCORE_GLYPH_BUFFER_BASE: equ $4380", constants)
            self.assertIn("W3D_HIGHSCORE_GLYPH_FIRST: equ 32", constants)
            self.assertIn("W3D_HIGHSCORE_GLYPH_LAST: equ 138", constants)
            self.assertIn("W3D_HIGHSCORE_GLYPH_HEIGHT: equ 10", constants)
            self.assertIn("W3D_SHELL_HIGH_SCORES_BASE_BUFFER: equ $4304", constants)
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
            # Agon64 entry. Verify a real pixel in disabled "Save Game" uses
            # the deliberately brighter composed color after conversion.
            font = decode_wolf_font(_archive())
            width, _, mask = font.glyph_mask("S")
            glyph_offset = next(index for index, value in enumerate(mask) if value)
            glyph_x = 100 + glyph_offset % width
            glyph_y = 107 + glyph_offset // width
            with Image.open(out / "processed/main_base.png") as processed_main:
                background = processed_main.getpixel((99, 68))[:3]
                disabled_glyph = processed_main.getpixel((glyph_x, glyph_y))[:3]
                self.assertEqual(background, (85, 0, 0))
                self.assertEqual(disabled_glyph, COMPOSED_DEACTIVE_RGB)
                self.assertNotEqual(disabled_glyph, background)

                width, _, mask = font.glyph_mask("V")
                glyph_offset = next(
                    index for index, value in enumerate(mask) if value
                )
                glyph_x = 100 + glyph_offset % width
                glyph_y = 146 + glyph_offset // width
                self.assertEqual(
                    processed_main.getpixel((glyph_x, glyph_y))[:3],
                    (170, 170, 170),
                )

            with Image.open(out / "orig/signon.png") as signon_image:
                self.assertEqual(signon_image.size, SHELL_SIGNON_SIZE)
                self.assertEqual(
                    hashlib.sha256(signon_image.tobytes()).hexdigest(),
                    "ec4230a8566ed0c0d149debd7bff2046a52ab3381be68ff59f0bd353e151fc5a",
                )

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
