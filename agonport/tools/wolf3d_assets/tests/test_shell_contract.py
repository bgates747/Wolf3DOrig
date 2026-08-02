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

from formats.shell import (  # noqa: E402
    SHELL_CHUNKS,
    SHELL_EXPECTED_DIMENSIONS,
    chunk_buffer_id,
)
from formats.vgagraph import read_vgagraph  # noqa: E402
from scripts.build_shell_assets import build_shell_assets  # noqa: E402

DATA_DIR = PROJECT_ROOT / "orig/data"
PALETTE_FILE = TOOLS_ROOT / "palettes/Agon64.gpl"


class ShellArchiveTests(unittest.TestCase):
    def test_real_v14_chunk_dimensions(self) -> None:
        archive = read_vgagraph(
            DATA_DIR / "VGADICT.WL1",
            DATA_DIR / "VGAHEAD.WL1",
            DATA_DIR / "VGAGRAPH.WL1",
        )
        for chunk_id in SHELL_CHUNKS:
            self.assertEqual(
                archive.decode_picture(chunk_id).size,
                SHELL_EXPECTED_DIMENSIONS[chunk_id],
            )

    def test_build_has_stable_names_ids_and_payloads(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            out = Path(temporary) / "shell"
            entries = build_shell_assets(DATA_DIR, out, PALETTE_FILE, override_dir=None)
            self.assertEqual(len(entries), len(SHELL_CHUNKS))
            self.assertEqual({entry.chunkId for entry in entries}, set(SHELL_CHUNKS))
            self.assertEqual(
                {entry.bufferId for entry in entries},
                {chunk_buffer_id(chunk_id) for chunk_id in SHELL_CHUNKS},
            )
            manifest = [json.loads(line) for line in (out / "shell_assets.jsonl").read_text().splitlines()]
            self.assertEqual(len(manifest), len(SHELL_CHUNKS))
            self.assertTrue((out / "shell.agnb").read_bytes().startswith(b"RIFF"))
            constants = (out / "wolf3d_shell_assets.inc").read_text()
            self.assertIn("W3D_SHELL_TITLE_BUFFER equ $4263", constants)

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
