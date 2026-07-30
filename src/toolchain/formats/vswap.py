"""VSWAP.WL1 codec (wall/door textures; sprites and sounds are out of scope
for this phase -- see doc/map_toolchain_notes.md).

Grounded in orig/src/WOLFSRC/ID_PM.C (chunk table layout) and WL_MAIN.C's
``SetupWalls()`` (tile-value -> chunk-index mapping).
"""
from __future__ import annotations

import struct
from dataclasses import dataclass

from PIL import Image

from .palette import WOLF3D_PALETTE_RGB888

TEXTURE_SIZE = 64  # wall/door textures are always 64x64, 8bpp indexed


@dataclass
class VSwapFile:
    numchunks: int
    spritestart: int
    soundstart: int
    chunks: list[bytes]  # raw bytes per chunk, empty bytes b"" for zero-length chunks


def read_vswap(data: bytes) -> VSwapFile:
    numchunks, spritestart, soundstart = struct.unpack_from("<HHH", data, 0)
    offsets = struct.unpack_from(f"<{numchunks}I", data, 6)
    lengths = struct.unpack_from(f"<{numchunks}H", data, 6 + numchunks * 4)
    chunks = []
    for i in range(numchunks):
        off = offsets[i]
        length = lengths[i]
        chunks.append(data[off:off + length] if length else b"")
    return VSwapFile(numchunks=numchunks, spritestart=spritestart,
                      soundstart=soundstart, chunks=chunks)


def write_vswap(vswap: VSwapFile) -> bytes:
    numchunks = vswap.numchunks
    header_size = 6 + numchunks * 4 + numchunks * 2
    offsets = []
    lengths = []
    body = bytearray()
    pos = header_size
    for chunk in vswap.chunks:
        offsets.append(pos if chunk else 0)
        lengths.append(len(chunk))
        body += chunk
        pos += len(chunk)

    out = bytearray(struct.pack("<HHH", vswap.numchunks, vswap.spritestart, vswap.soundstart))
    out += struct.pack(f"<{numchunks}I", *offsets)
    out += struct.pack(f"<{numchunks}H", *lengths)
    out += body
    return bytes(out)


def wall_tile_to_chunks(tile_value: int) -> tuple[int, int]:
    """Wall tile value (1..63) -> (horiz_chunk, vert_chunk) VSWAP chunk indices.

    Matches WL_MAIN.C ``SetupWalls()``: horizwall[i]=(i-1)*2, vertwall[i]=(i-1)*2+1.
    """
    return (tile_value - 1) * 2, (tile_value - 1) * 2 + 1


def chunk_to_image(chunk: bytes) -> Image.Image:
    """Decode a raw 64x64 column-major 8bpp VSWAP texture chunk to an RGB image."""
    assert len(chunk) == TEXTURE_SIZE * TEXTURE_SIZE
    img = Image.new("P", (TEXTURE_SIZE, TEXTURE_SIZE))
    img.putpalette([c for rgb in WOLF3D_PALETTE_RGB888 for c in rgb])
    pixels = bytearray(TEXTURE_SIZE * TEXTURE_SIZE)
    for x in range(TEXTURE_SIZE):
        column = chunk[x * TEXTURE_SIZE:(x + 1) * TEXTURE_SIZE]
        for y in range(TEXTURE_SIZE):
            pixels[y * TEXTURE_SIZE + x] = column[y]
    img.putdata(bytes(pixels))
    return img.convert("RGB")


def image_to_chunk(img: Image.Image) -> bytes:
    """Encode an RGB(A) image back into a raw 64x64 column-major 8bpp chunk,
    matching each pixel to the nearest Wolf3D palette entry."""
    assert img.size == (TEXTURE_SIZE, TEXTURE_SIZE), \
        f"wall textures must be {TEXTURE_SIZE}x{TEXTURE_SIZE}, got {img.size}"
    rgb = img.convert("RGB")
    pixels = rgb.load()
    out = bytearray(TEXTURE_SIZE * TEXTURE_SIZE)
    for x in range(TEXTURE_SIZE):
        for y in range(TEXTURE_SIZE):
            out[x * TEXTURE_SIZE + y] = _nearest_palette_index(pixels[x, y])
    return bytes(out)


def _nearest_palette_index(rgb: tuple[int, int, int]) -> int:
    r, g, b = rgb
    best_index = 0
    best_dist = None
    for i, (pr, pg, pb) in enumerate(WOLF3D_PALETTE_RGB888):
        dist = (r - pr) ** 2 + (g - pg) ** 2 + (b - pb) ** 2
        if best_dist is None or dist < best_dist:
            best_dist = dist
            best_index = i
    return best_index
