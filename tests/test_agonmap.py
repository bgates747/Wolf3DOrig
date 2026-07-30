"""Tests for the AgonWolf3D .map/tiles.txt reader, validated against real
sample files from the sibling AgonWolf3D repo (external to this repo;
skipped if that path isn't present locally)."""
import os

import pytest

from toolchain.formats import agonmap

AGON_REPO = os.path.expanduser("~/Agon/mystuff/AgonWolf3D")
ROOM_00_0 = os.path.join(AGON_REPO, "src/mapmaker/00_0.map")
TILES_TXT = os.path.join(AGON_REPO, "src/mapmaker/tiles.txt")

requires_agon_repo = pytest.mark.skipif(
    not os.path.exists(ROOM_00_0), reason="AgonWolf3D sibling repo not present locally")


@requires_agon_repo
def test_agon_map_header_and_first_row():
    m = agonmap.read_agon_map(ROOM_00_0)
    assert (m.max_x, m.max_y, m.standard_banks, m.custom_banks) == (14, 14, 5, 0)
    assert len(m.grid) == 15 and all(len(row) == 15 for row in m.grid)
    # Verified directly against a raw hex dump of the file.
    assert m.grid[0][0:4] == [41, 45, 52, 14]


@requires_agon_repo
def test_agon_tile_catalog_known_entries():
    catalog = agonmap.read_tile_catalog(TILES_TXT)
    wall = catalog[10]
    assert wall.name == "LIGHT GREY WALL"
    assert wall.is_wall and wall.special == "outer"
    door = catalog[57]
    assert door.name == "REGULAR DOOR"
    assert door.is_door and not door.is_wall
