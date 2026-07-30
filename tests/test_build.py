"""Round-trip test for the Tiled export/import pair: extract.py's Tiled
export -> build.py's compiler should reproduce the original decoded
plane0/plane1 grids exactly, against the real shareware WL1 data under
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
        assert rebuilt_level.header.name == orig_level.header.name

        # Only player-start markers round-trip through plane1 today -- other
        # actor/item/pushwall codes aren't part of the Tiled schema yet, so
        # compare just the player-start positions rather than full plane1 grids.
        orig_starts = [(x, y, v) for y, row in enumerate(orig_level.plane1)
                       for x, v in enumerate(row) if 19 <= v <= 22]
        rebuilt_starts = [(x, y, v) for y, row in enumerate(rebuilt_level.plane1)
                          for x, v in enumerate(row) if 19 <= v <= 22]
        assert rebuilt_starts == orig_starts
