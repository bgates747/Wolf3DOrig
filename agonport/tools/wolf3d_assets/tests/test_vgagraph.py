from __future__ import annotations

import sys
import unittest
from pathlib import Path

TOOLS_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS_ROOT))

from formats.vgagraph import HuffmanNode, huffman_expand, planar_to_row_major


class HuffmanTests(unittest.TestCase):
    def test_lsb_first_and_root_reset(self) -> None:
        nodes = [HuffmanNode(0, 0) for _ in range(255)]
        nodes[254] = HuffmanNode(ord("A"), 256)
        nodes[0] = HuffmanNode(ord("B"), ord("C"))
        # bits 0, 10, 11 (LSB first) => A, B, C
        self.assertEqual(huffman_expand(bytes((0b00011010,)), 3, tuple(nodes)), b"ABC")

    def test_truncated_stream_is_rejected(self) -> None:
        nodes = [HuffmanNode(256, 256) for _ in range(255)]
        with self.assertRaisesRegex(ValueError, "ended"):
            huffman_expand(b"", 1, tuple(nodes))


class PlanarTests(unittest.TestCase):
    def test_four_planes_interleave_by_x_modulo_four(self) -> None:
        # 8x2: each plane contains two bytes per row.
        planar = bytes(
            (
                0, 4, 8, 12,
                1, 5, 9, 13,
                2, 6, 10, 14,
                3, 7, 11, 15,
            )
        )
        self.assertEqual(planar_to_row_major(planar, 8, 2), bytes(range(16)))

    def test_invalid_size_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "expected"):
            planar_to_row_major(b"short", 8, 2)


if __name__ == "__main__":
    unittest.main()
