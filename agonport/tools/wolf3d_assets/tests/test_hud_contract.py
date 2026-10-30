from __future__ import annotations

import struct
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

TOOLS_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(TOOLS_ROOT))

from formats.hud import (
    HUD_CHUNKS,
    HUD_COMPOSITE_BUFFER_IDS,
    HUD_EXPECTED_DIMENSIONS,
    LEVEL_END_CHUNKS,
    LEVEL_END_CHUNK_NAMES,
    chunk_buffer_id,
)
from formats.palette import WOLF3D_PALETTE_RGB888
from formats.vgagraph import read_vgagraph
from scripts.build_hud_assets import build_hud_assets

DATA_DIR = PROJECT_ROOT / "orig" / "data"
PALETTE_FILE = TOOLS_ROOT / "palettes" / "Agon64.gpl"

EXPECTED_COMPOSITES = {
    "floor_complete_base": (0x4100, 320, 200, 0, 0),
    "secret_floor_complete_base": (0x4101, 320, 200, 0, 0),
}


def _riff_chunks(data: bytes, start: int, end: int):
    offset = start
    while offset < end:
        chunk_id = data[offset : offset + 4]
        size = struct.unpack_from("<I", data, offset + 4)[0]
        payload_start = offset + 8
        payload_end = payload_start + size
        yield chunk_id, data[payload_start:payload_end]
        offset = payload_start + ((size + 3) & ~3)
    if offset != end:
        raise AssertionError(f"RIFF chunk alignment ended at {offset}, expected {end}")


def _agnb_records(path: Path) -> dict[int, tuple[int, int, int]]:
    data = path.read_bytes()
    if data[:4] != b"RIFF" or data[8:12] != b"AGNB":
        raise AssertionError("not an AGNB RIFF file")
    records = {}
    for chunk_id, payload in _riff_chunks(data, 12, len(data)):
        if chunk_id != b"LIST":
            continue
        if payload[:4] != b"BUFR":
            continue
        fields = {key: value for key, value in _riff_chunks(payload, 4, len(payload))}
        buffer_id = struct.unpack("<H", fields[b"BHDR"])[0]
        width, height, image_format = struct.unpack("<HHB", fields[b"IMAG"])
        if len(fields[b"DATA"]) != width * height:
            raise AssertionError("AGNB DATA length disagrees with IMAG")
        records[buffer_id] = (width, height, image_format)
    return records


class HudArchiveTests(unittest.TestCase):
    def test_real_wl1_chunk_dimensions(self) -> None:
        archive = read_vgagraph(
            DATA_DIR / "VGADICT.WL1",
            DATA_DIR / "VGAHEAD.WL1",
            DATA_DIR / "VGAGRAPH.WL1",
        )
        for chunk_id in HUD_CHUNKS:
            self.assertEqual(
                archive.decode_picture(chunk_id).size,
                HUD_EXPECTED_DIMENSIONS[chunk_id],
            )

        self.assertEqual(LEVEL_END_CHUNKS, tuple(range(55, 97)))
        self.assertEqual(LEVEL_END_CHUNK_NAMES[55], "level_end_guy_1")
        self.assertEqual(LEVEL_END_CHUNK_NAMES[56], "level_end_colon")
        self.assertEqual(LEVEL_END_CHUNK_NAMES[57], "level_end_digit_0")
        self.assertEqual(LEVEL_END_CHUNK_NAMES[67], "level_end_percent")
        self.assertEqual(LEVEL_END_CHUNK_NAMES[68], "level_end_letter_a")
        self.assertEqual(LEVEL_END_CHUNK_NAMES[93], "level_end_letter_z")
        self.assertEqual(LEVEL_END_CHUNK_NAMES[96], "level_end_guy_2")

    def test_full_build_has_exact_original_ids_and_dimensions(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            out_dir = Path(temporary)
            entries = build_hud_assets(DATA_DIR, out_dir, PALETTE_FILE, method="rgb")
            self.assertEqual(
                len(entries), len(HUD_CHUNKS) + len(EXPECTED_COMPOSITES)
            )
            raw = [entry for entry in entries if entry.chunkId is not None]
            composites = {
                entry.name: entry for entry in entries if entry.chunkId is None
            }
            self.assertEqual({entry.chunkId for entry in raw}, set(HUD_CHUNKS))
            self.assertEqual(
                {entry.bufferId for entry in raw},
                {chunk_buffer_id(chunk_id) for chunk_id in HUD_CHUNKS},
            )
            self.assertEqual(set(composites), set(EXPECTED_COMPOSITES))
            self.assertEqual(
                HUD_COMPOSITE_BUFFER_IDS,
                {name: contract[0] for name, contract in EXPECTED_COMPOSITES.items()},
            )
            for name, contract in EXPECTED_COMPOSITES.items():
                entry = composites[name]
                self.assertEqual(
                    (
                        entry.bufferId,
                        entry.width,
                        entry.height,
                        entry.plotX,
                        entry.plotY,
                    ),
                    contract,
                )

            records = _agnb_records(out_dir / "hud.agnb")
            self.assertEqual(
                set(records),
                {
                    *(chunk_buffer_id(chunk_id) for chunk_id in HUD_CHUNKS),
                    *HUD_COMPOSITE_BUFFER_IDS.values(),
                },
            )
            for chunk_id in HUD_CHUNKS:
                self.assertEqual(
                    records[chunk_buffer_id(chunk_id)],
                    (*HUD_EXPECTED_DIMENSIONS[chunk_id], 1),
                )
            for buffer_id, width, height, _, _ in EXPECTED_COMPOSITES.values():
                self.assertEqual(records[buffer_id], (width, height, 1))

            raw_ids = {chunk_buffer_id(chunk_id) for chunk_id in HUD_CHUNKS}
            composite_ids = set(HUD_COMPOSITE_BUFFER_IDS.values())
            self.assertTrue(raw_ids.isdisjoint(composite_ids))
            self.assertLess(max(raw_ids), 0x4100)
            self.assertGreaterEqual(min(composite_ids), 0x4100)
            self.assertLess(max(composite_ids), 0x4200)
            self.assertNotIn(0x40F0, records)
            self.assertNotIn(0x4061, records)  # chunk 97/BJWIN is victory-only
            self.assertFalse((out_dir / "processed" / "status_panel.rgba2").exists())
            constants = (out_dir / "hud_buffers.inc").read_text()
            self.assertIn("W3D_HUD_LEVEL_END_GUY_1_BUFFER equ $4037", constants)
            self.assertIn("W3D_HUD_STATUSBAR_BUFFER equ $4062", constants)
            self.assertIn("W3D_HUD_FLOOR_COMPLETE_BASE_BUFFER equ $4100", constants)
            self.assertIn(
                "W3D_HUD_SECRET_FLOOR_COMPLETE_BASE_BUFFER equ $4101", constants
            )
            self.assertIn("W3D_HUD_FLOOR_COMPLETE_BASE_WIDTH equ 320", constants)
            self.assertIn("W3D_HUD_FLOOR_COMPLETE_BASE_X equ 0", constants)
            self.assertNotIn("W3D_HUD_STATUS_PANEL", constants)

            background = WOLF3D_PALETTE_RGB888[127]
            with (
                Image.open(out_dir / "orig" / "floor_complete_base.png") as ordinary,
                Image.open(
                    out_dir / "orig" / "secret_floor_complete_base.png"
                ) as secret,
                Image.open(out_dir / "orig" / "level_end_guy_1.png") as guy,
                Image.open(out_dir / "orig" / "level_end_letter_f.png") as letter_f,
                Image.open(out_dir / "orig" / "level_end_letter_c.png") as letter_c,
                Image.open(out_dir / "orig" / "level_end_letter_s.png") as letter_s,
                Image.open(out_dir / "orig" / "level_end_digit_0.png") as digit_0,
                Image.open(out_dir / "orig" / "level_end_digit_1.png") as digit_1,
                Image.open(out_dir / "orig" / "level_end_percent.png") as percent,
                Image.open(
                    out_dir / "orig" / "level_end_exclamation.png"
                ) as exclamation,
            ):
                self.assertEqual(ordinary.size, (320, 200))
                self.assertEqual(secret.size, (320, 200))
                self.assertEqual(ordinary.getpixel((319, 199)), background)
                self.assertEqual(secret.getpixel((319, 199)), background)
                self.assertEqual(
                    ordinary.crop((0, 16, 104, 104)).tobytes(),
                    guy.convert("RGB").tobytes(),
                )
                self.assertEqual(
                    ordinary.crop((112, 16, 128, 32)).tobytes(),
                    letter_f.convert("RGB").tobytes(),
                )
                self.assertEqual(
                    ordinary.crop((112, 32, 128, 48)).tobytes(),
                    letter_c.convert("RGB").tobytes(),
                )
                self.assertEqual(
                    ordinary.crop((272, 56, 288, 72)).tobytes(),
                    digit_0.convert("RGB").tobytes(),
                )
                self.assertEqual(
                    ordinary.crop((296, 112, 312, 128)).tobytes(),
                    percent.convert("RGB").tobytes(),
                )
                self.assertEqual(
                    secret.crop((112, 32, 128, 48)).tobytes(),
                    letter_s.convert("RGB").tobytes(),
                )
                self.assertEqual(
                    secret.crop((128, 48, 144, 64)).tobytes(),
                    letter_c.convert("RGB").tobytes(),
                )
                self.assertEqual(
                    secret.crop((80, 128, 96, 144)).tobytes(),
                    digit_1.convert("RGB").tobytes(),
                )
                self.assertEqual(
                    secret.crop((256, 128, 264, 144)).tobytes(),
                    exclamation.convert("RGB").tobytes(),
                )

            with Image.open(
                out_dir / "processed" / "floor_complete_base.png"
            ) as processed:
                self.assertEqual(processed.getpixel((319, 199)), (0, 85, 85, 255))

    def test_matching_hand_edited_png_overrides_only_that_asset(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            override_dir = root / "overrides"
            override_dir.mkdir()
            Image.new("RGB", (48, 24), (255, 0, 0)).save(
                override_dir / "weapon_knife.png"
            )

            entries = build_hud_assets(
                DATA_DIR, root / "out", PALETTE_FILE, override_dir=override_dir
            )
            by_name = {entry.name: entry for entry in entries}
            self.assertTrue(
                by_name["weapon_knife"].source.startswith("hand-edited override:")
            )
            self.assertEqual(by_name["weapon_pistol"].source, "VGAGRAPH.WL1 chunk 104")
            with Image.open(root / "out" / "orig" / "weapon_knife.png") as image:
                self.assertEqual(image.convert("RGB").getpixel((0, 0)), (255, 0, 0))

    def test_hand_edited_override_dimensions_are_checked(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            override_dir = root / "overrides"
            override_dir.mkdir()
            Image.new("RGB", (1, 1)).save(override_dir / "weapon_knife.png")
            with self.assertRaisesRegex(ValueError, "expected"):
                build_hud_assets(
                    DATA_DIR, root / "out", PALETTE_FILE, override_dir=override_dir
                )

    def test_level_end_override_is_inherited_by_composed_screen(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            override_dir = root / "overrides"
            override_dir.mkdir()
            Image.new("RGB", (16, 16), (255, 0, 0)).save(
                override_dir / "level_end_letter_f.png"
            )

            entries = build_hud_assets(
                DATA_DIR, root / "out", PALETTE_FILE, override_dir=override_dir
            )
            by_name = {entry.name: entry for entry in entries}
            self.assertTrue(
                by_name["level_end_letter_f"].source.startswith(
                    "hand-edited override:"
                )
            )
            with Image.open(
                root / "out" / "orig" / "floor_complete_base.png"
            ) as image:
                self.assertEqual(
                    image.convert("RGB").crop((112, 16, 128, 32)).getextrema(),
                    ((255, 255), (0, 0), (0, 0)),
                )


if __name__ == "__main__":
    unittest.main()
