#!/usr/bin/env python3
"""Generates the shared eZ80/VDP DDA smoke-test tilemap fixture.

Byte-identical contract, agreed in agonport/doc/handoff_ez80_ai_raycaster.md:
- 64x64 bytes, row-major (tiley*64+tilex).
- Mandatory solid outer ring (tile 0x01) around the whole 64x64 buffer.
- An 8x8 test room (diagram in the handoff doc) embedded with its local
  (1,1) at absolute (10,10): absolute = origin + local - 1, origin=(10,10).
- Tile encoding: 0x00 open, 0x01-0x7F wall (value = wall texture id),
  0x80-0xBF door (value & 0x7F = door index).

Run this script to (re)produce the canonical .bin; both agents should get
byte-identical output.
"""

import pathlib

MAPSIZE = 64
TILE_OPEN = 0x00
TILE_WALL = 0x01
TILE_DOOR_FLAG = 0x80

ROOM_ORIGIN = (10, 10)  # absolute tile coords for diagram local (1,1)

# Diagram from the handoff doc, local coords 1..8 in both x and y.
ROOM_ROWS = [
	"########",
	"#..#...#",
	"#..#...#",
	"#..D...#",
	"#..#...#",
	"#..#...#",
	"#......#",
	"########",
]


def build_map():
	tilemap = bytearray([TILE_OPEN] * (MAPSIZE * MAPSIZE))

	def set_tile(x, y, value):
		tilemap[y * MAPSIZE + x] = value

	# Mandatory solid outer ring.
	for i in range(MAPSIZE):
		set_tile(i, 0, TILE_WALL)
		set_tile(i, MAPSIZE - 1, TILE_WALL)
		set_tile(0, i, TILE_WALL)
		set_tile(MAPSIZE - 1, i, TILE_WALL)

	# Embedded test room.
	ox, oy = ROOM_ORIGIN
	for local_y, row in enumerate(ROOM_ROWS, start=1):
		for local_x, ch in enumerate(row, start=1):
			abs_x = ox + local_x - 1
			abs_y = oy + local_y - 1
			if ch == "#":
				set_tile(abs_x, abs_y, TILE_WALL)
			elif ch == "D":
				set_tile(abs_x, abs_y, TILE_DOOR_FLAG | 0)  # door slot 0
			# "." leaves TILE_OPEN (already the default)

	return bytes(tilemap)


def main():
	data = build_map()
	assert len(data) == MAPSIZE * MAPSIZE

	out_dir = pathlib.Path(__file__).resolve().parent.parent / "assets" / "generated"
	out_dir.mkdir(parents=True, exist_ok=True)
	out_path = out_dir / "dda_smoke_test_map.bin"
	out_path.write_bytes(data)

	door_index = ROOM_ORIGIN[0] + 4 - 1, ROOM_ORIGIN[1] + 4 - 1
	print(f"wrote {out_path} ({len(data)} bytes)")
	print(f"door tile at absolute {door_index}, byte 0x{data[door_index[1]*MAPSIZE+door_index[0]]:02x}")


if __name__ == "__main__":
	main()
