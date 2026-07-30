"""Round-trip test for the Tiled export/import pair: extract.py's Tiled
export -> build.py's compiler should reproduce the original decoded
plane0/plane1 grids (including actors/items/pushwalls, not just the
player-start marker) exactly, against the real shareware WL1 data under
orig/data/ (gitignored; present locally, per project setup docs)."""
import os

import pytest

from toolchain.cli import build, extract
from toolchain.formats import mapfile

ORIG_DATA = os.path.join(os.path.dirname(__file__), "..", "orig", "data")
MAPHEAD_PATH = os.path.join(ORIG_DATA, "MAPHEAD.WL1")
GAMEMAPS_PATH = os.path.join(ORIG_DATA, "GAMEMAPS.WL1")
VSWAP_PATH = os.path.join(ORIG_DATA, "VSWAP.WL1")

requires_orig_data = pytest.mark.skipif(
    not os.path.exists(MAPHEAD_PATH), reason="orig/data/ not present locally")


@requires_orig_data
def test_extract_then_build_reproduces_original_level_grids(tmp_path):
    tiled_dir = tmp_path / "tiled"
    extract.extract_tiled_maps(MAPHEAD_PATH, GAMEMAPS_PATH, VSWAP_PATH, str(tiled_dir))

    wl1_dir = tmp_path / "wl1"
    maphead_path, gamemaps_path = build.build_wl1(str(tiled_dir), str(wl1_dir))

    with open(MAPHEAD_PATH, "rb") as f:
        orig_maphead = mapfile.read_maphead(f.read())
    with open(GAMEMAPS_PATH, "rb") as f:
        orig_gamemaps = f.read()

    with open(maphead_path, "rb") as f:
        rebuilt_maphead = mapfile.read_maphead(f.read())
    with open(gamemaps_path, "rb") as f:
        rebuilt_gamemaps = f.read()

    for index, offset in enumerate(orig_maphead.level_offsets):
        if offset <= 0:
            continue
        orig_level = mapfile.read_level(orig_gamemaps, orig_maphead, index)
        rebuilt_level = mapfile.read_level(rebuilt_gamemaps, rebuilt_maphead, index)
        assert rebuilt_level.plane0 == orig_level.plane0
        assert rebuilt_level.plane1 == orig_level.plane1
        assert rebuilt_level.header.name == orig_level.header.name


@requires_orig_data
def test_extract_then_build_reproduces_original_vswap_textures(tmp_path):
    """build_vswap should leave every chunk functionally unchanged when fed
    back its own unedited wall_textures.png. Not a raw-byte comparison: the
    real VSWAP.WL1 pads its offset table to a 4096-byte boundary (a page-
    alignment artifact write_vswap doesn't replicate -- offsets are stored
    explicitly, so this doesn't affect the game's ability to load it), and
    the Wolf3D palette has a few duplicate RGB entries so a repainted wall
    chunk's raw index bytes aren't guaranteed identical to the original,
    only its decoded pixels are (see test_formats.py's equivalent caveat)."""
    from toolchain.formats import vswap as vswap_mod

    extract.extract_tileset(VSWAP_PATH, str(tmp_path))
    textures_png = tmp_path / "wall_textures.png"

    out_path = build.build_vswap(str(textures_png), VSWAP_PATH, str(tmp_path / "VSWAP.WL1"))

    with open(VSWAP_PATH, "rb") as f:
        orig = vswap_mod.read_vswap(f.read())
    with open(out_path, "rb") as f:
        rebuilt = vswap_mod.read_vswap(f.read())

    assert rebuilt.numchunks == orig.numchunks
    assert rebuilt.spritestart == orig.spritestart
    assert rebuilt.soundstart == orig.soundstart
    for i in range(orig.spritestart):
        if not orig.chunks[i]:
            assert not rebuilt.chunks[i]
            continue
        assert vswap_mod.chunk_to_image(rebuilt.chunks[i]).tobytes() == \
            vswap_mod.chunk_to_image(orig.chunks[i]).tobytes()
    for i in range(orig.spritestart, orig.numchunks):
        assert rebuilt.chunks[i] == orig.chunks[i]
