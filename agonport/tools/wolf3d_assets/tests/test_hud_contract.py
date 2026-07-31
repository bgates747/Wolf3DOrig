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
    HUD_EXPECTED_DIMENSIONS,
    STATUS_PANEL_BUFFER_ID,
    chunk_buffer_id,
)
from formats.vgagraph import read_vgagraph
from scripts.build_hud_assets import build_hud_assets

DATA_DIR = PROJECT_ROOT / "orig" / "data"
PALETTE_FILE = TOOLS_ROOT / "palettes" / "Agon64.gpl"


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
            self.assertEqual(archive.decode_picture(chunk_id).size, HUD_EXPECTED_DIMENSIONS[chunk_id])

    def test_full_build_has_exact_ids_dimensions_and_panel_prefix(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            out_dir = Path(temporary)
            entries = build_hud_assets(DATA_DIR, out_dir, PALETTE_FILE, method="rgb")
            self.assertEqual(len(entries), len(HUD_CHUNKS) + 1)
            self.assertEqual(
                {entry.bufferId for entry in entries},
                {chunk_buffer_id(chunk_id) for chunk_id in HUD_CHUNKS}
                | {STATUS_PANEL_BUFFER_ID},
            )

            records = _agnb_records(out_dir / "hud.agnb")
            for chunk_id in HUD_CHUNKS:
                self.assertEqual(
                    records[chunk_buffer_id(chunk_id)],
                    (*HUD_EXPECTED_DIMENSIONS[chunk_id], 1),
                )
            self.assertEqual(records[STATUS_PANEL_BUFFER_ID], (320, 80, 1))

            statusbar = (out_dir / "processed" / "statusbar.rgba2").read_bytes()
            panel = (out_dir / "processed" / "status_panel.rgba2").read_bytes()
            self.assertEqual(panel[: 320 * 40], statusbar)

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
            self.assertTrue(by_name["weapon_knife"].source.startswith("hand-edited override:"))
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


if __name__ == "__main__":
    unittest.main()
