"""Round-trip codec tests validated against the real shareware WL1 data
under orig/data/ (gitignored; present locally, per project setup docs)."""
import os
import struct

import pytest

from toolchain.formats import mapfile, vswap

ORIG_DATA = os.path.join(os.path.dirname(__file__), "..", "orig", "data")
MAPHEAD_PATH = os.path.join(ORIG_DATA, "MAPHEAD.WL1")
GAMEMAPS_PATH = os.path.join(ORIG_DATA, "GAMEMAPS.WL1")
VSWAP_PATH = os.path.join(ORIG_DATA, "VSWAP.WL1")

requires_orig_data = pytest.mark.skipif(
    not os.path.exists(MAPHEAD_PATH), reason="orig/data/ not present locally")


@requires_orig_data
def test_maphead_parses_and_has_ten_shareware_levels():
    with open(MAPHEAD_PATH, "rb") as f:
        data = f.read()
    assert len(data) == 2 + 100 * 4
    maphead = mapfile.read_maphead(data)
    assert maphead.magic == mapfile.RLEW_TAG_DEFAULT
    populated = [i for i, off in enumerate(maphead.level_offsets) if off > 0]
    assert populated == list(range(10))  # shareware episode 1: slots 0-9


@requires_orig_data
def test_gamemaps_signature_and_all_levels_decode_to_64x64():
    with open(MAPHEAD_PATH, "rb") as f:
        maphead = mapfile.read_maphead(f.read())
    with open(GAMEMAPS_PATH, "rb") as f:
        gamemaps = f.read()
    assert gamemaps[:8] == mapfile.GAMEMAPS_SIGNATURE
    for i in range(10):
        level = mapfile.read_level(gamemaps, maphead, i)
        assert len(level.plane0) == 64
        assert all(len(row) == 64 for row in level.plane0)
        assert len(level.plane1) == 64
        assert all(len(row) == 64 for row in level.plane1)


@requires_orig_data
def test_gamemaps_level_zero_has_a_player_start_marker():
    with open(MAPHEAD_PATH, "rb") as f:
        maphead = mapfile.read_maphead(f.read())
    with open(GAMEMAPS_PATH, "rb") as f:
        gamemaps = f.read()
    level = mapfile.read_level(gamemaps, maphead, 0)
    starts = [v for row in level.plane1 for v in row if 19 <= v <= 22]
    assert len(starts) == 1  # exactly one player start on a real level


def test_rlew_round_trip():
    data = struct.pack("<8H", 1, 2, 2, 2, 2, 0xABCD, 5, 5)
    compressed = mapfile.rlew_compress(data)
    assert mapfile.rlew_decompress(compressed) == data


def test_carmack_round_trip_with_literal_words():
    data = struct.pack("<6H", 0x1234, 0xA700 | 0x12, 0xA855, 0, 1, 2)
    compressed = mapfile.carmack_compress(data)
    assert mapfile.carmack_decompress(compressed) == data


def test_compress_plane_round_trip():
    tile_words = struct.pack("<4096H", *([1] * 4096))
    compressed = mapfile.compress_plane(tile_words)
    assert mapfile.decompress_plane(compressed) == tile_words


def test_wall_tile_to_chunks_mapping():
    assert vswap.wall_tile_to_chunks(1) == (0, 1)
    assert vswap.wall_tile_to_chunks(2) == (2, 3)


@requires_orig_data
def test_vswap_parses_and_wall_chunk_round_trips_through_image():
    with open(VSWAP_PATH, "rb") as f:
        data = f.read()
    vs = vswap.read_vswap(data)
    assert vs.spritestart > 0
    assert vs.soundstart > vs.spritestart
    horiz, _vert = vswap.wall_tile_to_chunks(1)
    chunk = vs.chunks[horiz]
    assert len(chunk) == vswap.TEXTURE_SIZE * vswap.TEXTURE_SIZE
    img = vswap.chunk_to_image(chunk)
    assert img.size == (64, 64)
    rebuilt = vswap.image_to_chunk(img)
    # The palette has a few duplicate RGB entries (e.g. two (21,21,21) greys),
    # so index-for-index equality isn't guaranteed -- pixel colors must match.
    assert vswap.chunk_to_image(rebuilt).tobytes() == img.tobytes()
