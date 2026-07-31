"""MAPHEAD.WL1 / GAMEMAPS.WL1 codec.

Grounded in doc/map_toolchain_notes.md and cross-checked against
orig/src/WOLFSRC/WL_GAME.C, WL_MAIN.C and WL_DEF.H. Covers the v1.1+ format
used by the shareware data (RLEW compression, then Carmack compression, per
level plane).

The Carmack *encoder* here deliberately emits every word as a literal (with
escaping for words whose high byte collides with the 0xA7/0xA8 tag bytes)
rather than searching for back-references. This produces a larger-than-necessary
but always-valid Carmack stream -- floppy-disk space was id's reason for the
extra compression pass, which isn't a constraint for this project. The
*decoder* is a full, correct implementation (needed to read/validate the real
shareware data).

Forked 2026-07-31 from src/toolchain/formats/mapfile.py (verbatim at fork
time) into agonport/tools/wolf3d_assets/, per Author decision to vendor
canonical decoders rather than import across project boundaries. Only
read_maphead/read_level/read_level_header (decode side) are needed here --
the encode side (build_gamemaps/compress_plane/etc) is kept for parity with
the source but unused by this tree's scripts.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass, field

RLEW_TAG_DEFAULT = 0xABCD
CARMACK_NEAR = 0xA7
CARMACK_FAR = 0xA8

MAP_WIDTH = 64
MAP_HEIGHT = 64
NUM_MAP_SLOTS = 100
LEVEL_HEADER_SIZE = 38


# ---------------------------------------------------------------------------
# RLEW compression (id Software RLEW compression)
# ---------------------------------------------------------------------------

def rlew_decompress(data: bytes, tag: int = RLEW_TAG_DEFAULT) -> bytes:
    """Decode an RLEW stream. ``data`` starts with a u16LE expanded byte length."""
    expanded_len = struct.unpack_from("<H", data, 0)[0]
    out = bytearray()
    i = 2
    while len(out) < expanded_len:
        word = struct.unpack_from("<H", data, i)[0]
        i += 2
        if word == tag:
            count, value = struct.unpack_from("<HH", data, i)
            i += 4
            out += struct.pack("<H", value) * count
        else:
            out += struct.pack("<H", word)
    return bytes(out)


def rlew_compress(data: bytes, tag: int = RLEW_TAG_DEFAULT) -> bytes:
    """Minimal (correct, unoptimized) RLEW encoder: only escapes the tag word."""
    assert len(data) % 2 == 0
    words = struct.unpack(f"<{len(data)//2}H", data)
    out = bytearray(struct.pack("<H", len(data)))
    for word in words:
        if word == tag:
            out += struct.pack("<HHH", tag, 1, tag)
        else:
            out += struct.pack("<H", word)
    return bytes(out)


# ---------------------------------------------------------------------------
# Carmack compression
# ---------------------------------------------------------------------------

def carmack_decompress(data: bytes) -> bytes:
    """Decode a Carmack-compressed stream. ``data`` starts with a u16LE
    expanded byte length (the size of the RLEW-compressed data beneath it)."""
    expanded_len = struct.unpack_from("<H", data, 0)[0]
    out = bytearray()
    i = 2
    while len(out) < expanded_len:
        count = data[i]
        tag = data[i + 1]
        i += 2
        if tag in (CARMACK_NEAR, CARMACK_FAR) and count == 0:
            # Escape sequence: literal word with high byte == tag.
            low = data[i]
            i += 1
            out += bytes((low, tag))
        elif tag == CARMACK_NEAR:
            offset = data[i]
            i += 1
            start = len(out) - offset * 2
            out += bytes(out[start:start + count * 2])
        elif tag == CARMACK_FAR:
            offset = struct.unpack_from("<H", data, i)[0]
            i += 2
            start = offset * 2
            out += bytes(out[start:start + count * 2])
        else:
            out += bytes((count, tag))
    return bytes(out)


def carmack_compress(data: bytes) -> bytes:
    """Trivial (correct, unoptimized) Carmack encoder: literal words only,
    with escaping for words whose high byte collides with a tag byte."""
    assert len(data) % 2 == 0
    out = bytearray(struct.pack("<H", len(data)))
    for i in range(0, len(data), 2):
        low, high = data[i], data[i + 1]
        if high in (CARMACK_NEAR, CARMACK_FAR):
            out += bytes((0, high, low))
        else:
            out += bytes((low, high))
    return bytes(out)


def decompress_plane(raw: bytes, rlew_tag: int = RLEW_TAG_DEFAULT) -> bytes:
    """Full decode of a stored GAMEMAPS plane chunk: Carmack, then RLEW."""
    return rlew_decompress(carmack_decompress(raw), rlew_tag)


def compress_plane(tile_words: bytes, rlew_tag: int = RLEW_TAG_DEFAULT) -> bytes:
    """Full encode of a plane's raw tile words into a storable GAMEMAPS chunk:
    RLEW, then Carmack (matches the order the original engine expects)."""
    return carmack_compress(rlew_compress(tile_words, rlew_tag))


# ---------------------------------------------------------------------------
# MAPHEAD.WL1
# ---------------------------------------------------------------------------

@dataclass
class MapHead:
    magic: int
    level_offsets: list[int]  # 100 entries; <= 0 means "no level"


def read_maphead(data: bytes) -> MapHead:
    magic = struct.unpack_from("<H", data, 0)[0]
    offsets = list(struct.unpack_from(f"<{NUM_MAP_SLOTS}i", data, 2))
    return MapHead(magic=magic, level_offsets=offsets)


def write_maphead(maphead: MapHead) -> bytes:
    assert len(maphead.level_offsets) == NUM_MAP_SLOTS
    return struct.pack("<H", maphead.magic) + struct.pack(
        f"<{NUM_MAP_SLOTS}i", *maphead.level_offsets)


# ---------------------------------------------------------------------------
# GAMEMAPS.WL1
# ---------------------------------------------------------------------------

GAMEMAPS_SIGNATURE = b"TED5v1.0"


@dataclass
class LevelHeader:
    off_plane0: int
    off_plane1: int
    off_plane2: int
    len_plane0: int
    len_plane1: int
    len_plane2: int
    width: int
    height: int
    name: str


def read_level_header(data: bytes, offset: int) -> LevelHeader:
    (off0, off1, off2, len0, len1, len2, width, height) = struct.unpack_from(
        "<iiiHHHHH", data, offset)
    name_raw = data[offset + 22:offset + 22 + 16]
    name = name_raw.split(b"\x00", 1)[0].decode("ascii", errors="replace")
    return LevelHeader(off0, off1, off2, len0, len1, len2, width, height, name)


def write_level_header(h: LevelHeader) -> bytes:
    name_bytes = h.name.encode("ascii")[:15].ljust(16, b"\x00")
    return struct.pack("<iiiHHHHH", h.off_plane0, h.off_plane1, h.off_plane2,
                        h.len_plane0, h.len_plane1, h.len_plane2,
                        h.width, h.height) + name_bytes


@dataclass
class Level:
    header: LevelHeader
    plane0: list[list[int]] = field(default_factory=list)  # [y][x], walls/doors/floor
    plane1: list[list[int]] = field(default_factory=list)  # [y][x], markers/actors


def _words_to_grid(words: bytes, width: int, height: int) -> list[list[int]]:
    values = struct.unpack(f"<{width*height}H", words)
    return [list(values[y * width:(y + 1) * width]) for y in range(height)]


def _grid_to_words(grid: list[list[int]]) -> bytes:
    flat = [v for row in grid for v in row]
    return struct.pack(f"<{len(flat)}H", *flat)


def read_level(gamemaps: bytes, maphead: MapHead, index: int,
               rlew_tag: int = RLEW_TAG_DEFAULT) -> Level:
    offset = maphead.level_offsets[index]
    if offset <= 0:
        raise ValueError(f"level slot {index} is empty")
    header = read_level_header(gamemaps, offset)
    if header.width != MAP_WIDTH or header.height != MAP_HEIGHT:
        raise ValueError(f"level {index}: expected {MAP_WIDTH}x{MAP_HEIGHT}, "
                          f"got {header.width}x{header.height}")
    plane0_raw = gamemaps[header.off_plane0:header.off_plane0 + header.len_plane0]
    plane1_raw = gamemaps[header.off_plane1:header.off_plane1 + header.len_plane1]
    plane0 = _words_to_grid(decompress_plane(plane0_raw, rlew_tag), MAP_WIDTH, MAP_HEIGHT)
    plane1 = _words_to_grid(decompress_plane(plane1_raw, rlew_tag), MAP_WIDTH, MAP_HEIGHT)
    return Level(header=header, plane0=plane0, plane1=plane1)


def build_gamemaps(levels: dict[int, Level], rlew_tag: int = RLEW_TAG_DEFAULT
                    ) -> tuple[bytes, MapHead]:
    """Pack a set of {slot_index: Level} into a fresh GAMEMAPS.WL1 body plus
    the matching MAPHEAD. Levels not present in ``levels`` are left empty."""
    body = bytearray(GAMEMAPS_SIGNATURE)
    offsets = [0] * NUM_MAP_SLOTS
    for index in sorted(levels):
        level = levels[index]
        plane0_words = _grid_to_words(level.plane0)
        plane1_words = _grid_to_words(level.plane1)
        plane0_compressed = compress_plane(plane0_words, rlew_tag)
        plane1_compressed = compress_plane(plane1_words, rlew_tag)

        header_offset = len(body)
        # Header, then the cosmetic "!ID!" v1.1+ signature, then the planes.
        off_plane0 = header_offset + LEVEL_HEADER_SIZE + 4
        off_plane1 = off_plane0 + len(plane0_compressed)
        header = LevelHeader(
            off_plane0=off_plane0, off_plane1=off_plane1, off_plane2=0,
            len_plane0=len(plane0_compressed), len_plane1=len(plane1_compressed),
            len_plane2=0, width=MAP_WIDTH, height=MAP_HEIGHT,
            name=level.header.name or f"Level {index}")
        body += write_level_header(header)
        body += b"!ID!"  # cosmetic v1.1+ signature, matches real shareware files
        body += plane0_compressed
        body += plane1_compressed
        offsets[index] = header_offset

    maphead = MapHead(magic=rlew_tag, level_offsets=offsets)
    return bytes(body), maphead
