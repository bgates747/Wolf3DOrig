"""Decode Wolfenstein 3-D VGAHEAD/VGADICT/VGAGRAPH picture chunks.

The shareware WL1 graphics archive uses 24-bit little-endian chunk offsets
and a static Huffman dictionary.  Picture chunks start with a four-byte
expanded-length field and expand into four sequential VGA planes.  This
module deliberately covers that small, durable contract instead of the
unrelated font, tile, and extern chunk formats.

The decoder is grounded in the original ``ID_CA.C``/``ID_VL.C`` routines:
node 254 is the Huffman root, input bits are consumed least-significant bit
first, values below 256 are literals, and values at least 256 refer to node
``value - 256``.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from .palette import WOLF3D_PALETTE_RGB888

HUFFMAN_ROOT = 254
SPARSE_OFFSET = 0xFFFFFF
START_PICS = 3


@dataclass(frozen=True)
class HuffmanNode:
    bit0: int
    bit1: int


@dataclass(frozen=True)
class PictureDimensions:
    width: int
    height: int


@dataclass(frozen=True)
class VgaGraph:
    """A parsed WL1 graphics archive and its static Huffman dictionary."""

    nodes: tuple[HuffmanNode, ...]
    offsets: tuple[int, ...]
    graph: bytes

    def compressed_chunk(self, chunk_id: int) -> bytes:
        """Return one chunk's stored bytes, excluding no header bytes."""
        if not 0 <= chunk_id < len(self.offsets) - 1:
            raise IndexError(f"VGAGRAPH chunk id out of range: {chunk_id}")

        start = self.offsets[chunk_id]
        if start == SPARSE_OFFSET:
            raise ValueError(f"VGAGRAPH chunk {chunk_id} is sparse")

        end = next(
            (offset for offset in self.offsets[chunk_id + 1 :] if offset != SPARSE_OFFSET),
            None,
        )
        if end is None:
            raise ValueError(f"VGAGRAPH chunk {chunk_id} has no following offset")
        if not 0 <= start <= end <= len(self.graph):
            raise ValueError(
                f"Invalid VGAGRAPH bounds for chunk {chunk_id}: "
                f"{start}..{end} of {len(self.graph)}"
            )
        return self.graph[start:end]

    def expand_chunk(self, chunk_id: int) -> bytes:
        """Expand a non-tile graphics chunk with its explicit u32 length."""
        stored = self.compressed_chunk(chunk_id)
        if len(stored) < 4:
            raise ValueError(f"VGAGRAPH chunk {chunk_id} lacks its length field")
        expanded_size = int.from_bytes(stored[:4], "little")
        return huffman_expand(stored[4:], expanded_size, self.nodes)

    def picture_dimensions(self) -> tuple[PictureDimensions, ...]:
        """Decode STRUCTPIC (chunk 0) into its width/height table."""
        data = self.expand_chunk(0)
        if len(data) % 4:
            raise ValueError(f"STRUCTPIC has a non-integral record size: {len(data)}")
        dimensions = tuple(
            PictureDimensions(width, height)
            for width, height in struct.iter_unpack("<HH", data)
        )
        if not dimensions:
            raise ValueError("STRUCTPIC contains no picture dimensions")
        return dimensions

    def decode_picture(self, chunk_id: int) -> Image.Image:
        """Decode one STARTPICS-relative planar picture as a paletted image."""
        table_index = chunk_id - START_PICS
        dimensions = self.picture_dimensions()
        if not 0 <= table_index < len(dimensions):
            raise ValueError(
                f"Chunk {chunk_id} is not in the picture table "
                f"({START_PICS}..{START_PICS + len(dimensions) - 1})"
            )

        size = dimensions[table_index]
        planar = self.expand_chunk(chunk_id)
        pixels = planar_to_row_major(planar, size.width, size.height)
        image = Image.frombytes("P", (size.width, size.height), pixels)
        image.putpalette(
            [channel for color in WOLF3D_PALETTE_RGB888 for channel in color]
        )
        return image


def parse_dictionary(data: bytes) -> tuple[HuffmanNode, ...]:
    """Parse little-endian pairs from VGADICT.WL1."""
    if len(data) % 4:
        raise ValueError(f"VGADICT length must be divisible by four: {len(data)}")
    nodes = tuple(HuffmanNode(*values) for values in struct.iter_unpack("<HH", data))
    if len(nodes) <= HUFFMAN_ROOT:
        raise ValueError(
            f"VGADICT needs node {HUFFMAN_ROOT}, but contains {len(nodes)} nodes"
        )
    return nodes


def parse_offsets(data: bytes) -> tuple[int, ...]:
    """Parse VGAHEAD's packed 24-bit little-endian offsets."""
    if len(data) % 3:
        raise ValueError(f"VGAHEAD length must be divisible by three: {len(data)}")
    offsets = tuple(
        int.from_bytes(data[index : index + 3], "little")
        for index in range(0, len(data), 3)
    )
    if len(offsets) < 2:
        raise ValueError("VGAHEAD must contain a chunk and a following sentinel")
    return offsets


def read_vgagraph(
    dictionary_file: Path, head_file: Path, graph_file: Path
) -> VgaGraph:
    """Read the three WL1 graphics archive files."""
    archive = VgaGraph(
        nodes=parse_dictionary(dictionary_file.read_bytes()),
        offsets=parse_offsets(head_file.read_bytes()),
        graph=graph_file.read_bytes(),
    )
    final_offset = next(
        (offset for offset in reversed(archive.offsets) if offset != SPARSE_OFFSET), None
    )
    if final_offset != len(archive.graph):
        raise ValueError(
            f"VGAHEAD final offset {final_offset} disagrees with "
            f"VGAGRAPH size {len(archive.graph)}"
        )
    return archive


def huffman_expand(
    source: bytes, expanded_size: int, nodes: tuple[HuffmanNode, ...]
) -> bytes:
    """Expand exactly ``expanded_size`` bytes from an LSB-first bitstream."""
    if expanded_size < 0:
        raise ValueError(f"Negative Huffman output size: {expanded_size}")
    if len(nodes) <= HUFFMAN_ROOT:
        raise ValueError(f"Huffman root node {HUFFMAN_ROOT} is unavailable")

    output = bytearray()
    source_index = 0
    bit_mask = 1
    node_index = HUFFMAN_ROOT

    while len(output) < expanded_size:
        if source_index >= len(source):
            raise ValueError(
                f"Huffman stream ended after {len(output)}/{expanded_size} output bytes"
            )
        node = nodes[node_index]
        value = node.bit1 if source[source_index] & bit_mask else node.bit0

        bit_mask <<= 1
        if bit_mask == 0x100:
            bit_mask = 1
            source_index += 1

        if value < 256:
            output.append(value)
            node_index = HUFFMAN_ROOT
        else:
            node_index = value - 256
            if not 0 <= node_index < len(nodes):
                raise ValueError(f"Huffman dictionary references invalid node {node_index}")

    return bytes(output)


def planar_to_row_major(planar: bytes, width: int, height: int) -> bytes:
    """Interleave four sequential VGA planes into ordinary scanline pixels."""
    if width <= 0 or height <= 0:
        raise ValueError(f"Invalid picture dimensions: {width}x{height}")
    if width % 4:
        raise ValueError(f"Planar picture width must be divisible by four: {width}")
    expected_size = width * height
    if len(planar) != expected_size:
        raise ValueError(
            f"Planar picture data is {len(planar)} bytes; expected {expected_size} "
            f"for {width}x{height}"
        )

    plane_width = width // 4
    plane_size = plane_width * height
    row_major = bytearray(expected_size)
    for y in range(height):
        row_start = y * width
        plane_row = y * plane_width
        for x in range(width):
            row_major[row_start + x] = planar[
                (x & 3) * plane_size + plane_row + (x >> 2)
            ]
    return bytes(row_major)
