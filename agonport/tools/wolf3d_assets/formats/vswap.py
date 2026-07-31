"""VSWAP.WL1 codec (wall/door textures; sprites and sounds are out of scope
for this phase -- see doc/map_toolchain_notes.md).

Grounded in orig/src/WOLFSRC/ID_PM.C (chunk table layout) and WL_MAIN.C's
``SetupWalls()`` (tile-value -> chunk-index mapping).

Forked 2026-07-31 from src/toolchain/formats/vswap.py (verbatim at fork
time) into agonport/tools/wolf3d_assets/, per Author decision: agonport's
asset toolchain vendors its own copies of canonical decoders rather than
importing across project boundaries, so upstream changes there never
silently affect this tree. Sprite export is no longer out of scope here --
see sprite_chunk_to_image below and the asset-toolchain plan doc.
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


def num_wall_tiles(vswap: VSwapFile) -> int:
    """Number of plain wall texture ids (1..N) encoded before the door
    textures. Door textures occupy the last 8 wall/door chunks (see
    DOORWALL below), so ordinary wall ids run 1..(DOORWALL_base/2)."""
    return door_wall_base(vswap) // 2


# Door textures, grounded in orig/src/WOLFSRC/WL_DRAW.C (read-only reference,
# names/structure preserved per project naming policy, not copied verbatim):
# ``#define DOORWALL (PMSpriteStart-8)``. The last 8 chunks before the sprite
# range are 4 horiz/vert pairs: DOORWALL+0/1 = normal door face, DOORWALL+2/3
# = door jamb/frame (used regardless of lock type), DOORWALL+4/5 = elevator
# door face, DOORWALL+6/7 = locked door face (all 4 lock colors render
# identically -- WL_DRAW.C's ``switch(doorobjlist[doornum].lock)`` maps
# dr_lock1..dr_lock4 to the same DOORWALL+6 doorpage as dr_normal maps to
# DOORWALL+0 and dr_elevator maps to DOORWALL+4).
DOOR_CHUNK_COUNT = 8
DOOR_KIND_NORMAL = "normal"
DOOR_KIND_JAMB = "jamb"
DOOR_KIND_ELEVATOR = "elevator"
DOOR_KIND_LOCKED = "locked"
DOOR_KIND_CHUNK_OFFSET = {
    DOOR_KIND_NORMAL: 0,
    DOOR_KIND_JAMB: 2,
    DOOR_KIND_ELEVATOR: 4,
    DOOR_KIND_LOCKED: 6,
}


def door_wall_base(vswap: VSwapFile) -> int:
    """DOORWALL: chunk index of the first (normal-door) door-texture pair."""
    return vswap.spritestart - DOOR_CHUNK_COUNT


def door_kind_to_chunks(vswap: VSwapFile, kind: str) -> tuple[int, int]:
    """Door kind ("normal"/"jamb"/"elevator"/"locked") -> (horiz, vert)
    VSWAP chunk indices, mirroring wall_tile_to_chunks's pair shape."""
    base = door_wall_base(vswap) + DOOR_KIND_CHUNK_OFFSET[kind]
    return base, base + 1


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


def sprite_chunk_to_image(chunk: bytes) -> Image.Image:
    """Decode a raw VSWAP sprite chunk (chunks spritestart..soundstart-1) into
    an RGBA image, TEXTURE_SIZE x TEXTURE_SIZE, with fully transparent pixels
    wherever no post covers a column/row -- sprites are camera-facing
    billboards that rarely fill their whole 64x64 bounding box.

    Format (t_compshape in WL_DEF.H): UINT16LE leftpix, UINT16LE rightpix,
    then (rightpix-leftpix+1) UINT16LE column offsets (byte offsets from the
    start of this chunk), one per column in [leftpix, rightpix]. Each column
    offset points to a list of "posts" (vertical runs of opaque pixels):
    UINT16LE endrow*2 (0 terminates the column's post list), INT16LE
    pixelbase (signed -- see below), UINT16LE startrow*2. For row y in
    [startrow, endrow), the pixel's palette index is
    chunk[pixelbase + y] (pixelbase is precomputed as the real pixel-data
    offset minus startrow, a trick to avoid an extra subtraction per pixel
    in the original assembly scaler; it's legitimately negative for posts
    whose pixel data sits earlier in the chunk than startrow would suggest,
    so it must be read as a signed 16-bit value).

    Grounded in WL_DEF.H's t_compshape struct and WL_SCALE.C/CONTIGSC.C's
    ScaleShape()/SimpleScaleShape() column/post walk (id's own scaler code
    is deeply entangled with 16-bit segment/assembly-call scaling, so the
    post-triple layout was cross-checked against mozzwald/wolf4sdl's
    wl_draw.cpp, a maintained open-source SDL reimplementation, for the
    exact per-post field order).
    """
    leftpix, rightpix = struct.unpack_from("<HH", chunk, 0)
    img = Image.new("RGBA", (TEXTURE_SIZE, TEXTURE_SIZE), (0, 0, 0, 0))
    if rightpix < leftpix:
        return img
    num_cols = rightpix - leftpix + 1
    dataofs = struct.unpack_from(f"<{num_cols}H", chunk, 4)
    pixels = img.load()
    for col in range(num_cols):
        x = leftpix + col
        pos = dataofs[col]
        while True:
            endrow = struct.unpack_from("<H", chunk, pos)[0]
            if endrow == 0:
                break
            # pixelbase ("newstart" in the original source) is a signed
            # short -- it's precomputed as (pixel-data offset - startrow),
            # which is legitimately negative for posts near the top of a
            # tall pixel pool, so it must NOT be read as unsigned.
            pixelbase, startrow2 = struct.unpack_from("<hH", chunk, pos + 2)
            endrow >>= 1
            startrow = startrow2 >> 1
            pos += 6
            for y in range(startrow, endrow):
                r, g, b = WOLF3D_PALETTE_RGB888[chunk[pixelbase + y]]
                pixels[x, y] = (r, g, b, 255)
    return img
