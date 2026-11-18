"""Prepare an isolated marked E1L1 pushwall fixture from the accepted payload."""
import argparse
from dataclasses import replace
import json
from pathlib import Path
import shutil
import struct
import sys
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[4]
sys.path[:0] = [str(ROOT / folder) for folder in (
    "tools", "src/asm/wolf3d_acceptance/scripts", "agonport/tools/wolf3d_assets",
)]
from agnb.container import BufferRecord, make_buffer_record
from agnb.manifest import KIND_WALL, WALL_BUFFER_BASE, buffer_id_for
from formats.level_package import build_package, parse_package
from prepare import SCENARIOS, patch_state
from wolf_firmware import DEFAULT_PAYLOAD, PRODUCTION_MODULE_SHA, sha, verify_payload

WALL = (10, 13)
MARKER = 0xFD
FONT = {
    "P": ("1110", "1001", "1110", "1000", "1000"),
    "U": ("1001", "1001", "1001", "1001", "0110"),
    "S": ("0111", "1000", "0110", "0001", "1110"),
    "H": ("1001", "1001", "1111", "1001", "1001"),
    "M": ("10001", "11011", "10101", "10001", "10001"),
    "E": ("1111", "1000", "1110", "1000", "1111"),
}


def wall_art():
    """Draw a row-major 64x64 RGBA2222 wooden panel and stencil."""
    plank = (0xC6, 0xC7, 0xC6, 0xC2)
    pixels = bytearray(plank[(x // 16 + (1 if y % 11 == 0 else 0)) % 4]
                       for y in range(64) for x in range(64))
    for y in range(14, 50):
        for x in range(7, 57):
            pixels[y * 64 + x] = 0xC2 if 9 <= x < 55 and 16 <= y < 48 else 0xC1
    for word, top in (("PUSH", 20), ("ME", 34)):
        width = 2 * (sum(len(FONT[c][0]) + 1 for c in word) - 1)
        left = (64 - width) // 2
        for letter in word:
            for y, line in enumerate(FONT[letter]):
                for x, bit in enumerate(line):
                    if bit == "1":
                        for dy in range(2):
                            at = (top + y * 2 + dy) * 64 + left + x * 2
                            pixels[at:at + 2] = bytes((0xDF, 0xDF))
            left += 2 * (len(FONT[letter][0]) + 1)
    return bytes(pixels)


def add_art(container, scratch, tilemap):
    if container[:4] != b"RIFF" or container[8:12] != b"AGNB":
        raise ValueError("Unexpected tiles container")
    used = set(tilemap)
    offset = 12
    while offset < len(container):
        tag, length = struct.unpack_from("<4sI", container, offset)
        body = offset + 8
        if tag == b"LIST" and container[body:body+8] == b"BUFRBHDR":
            used.add(struct.unpack_from("<H", container, body + 12)[0] - WALL_BUFFER_BASE)
        offset = body + (length + 3) // 4 * 4
    if offset != len(container):
        raise ValueError("Invalid tiles container length")
    texture = next(value for value in range(63, 0, -1) if value not in used)
    art = scratch / "push-me.rgba2"
    art.write_bytes(wall_art())
    record = make_buffer_record(BufferRecord(
        "push-me", buffer_id_for(KIND_WALL, texture), 64, 64, art, 4096,
    ))
    body = container[8:] + record
    return texture, b"RIFF" + struct.pack("<I", len(body)) + body


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--base-payload", type=Path, default=DEFAULT_PAYLOAD)
    args = parser.parse_args()
    base = args.base_payload
    stock = verify_payload(base)
    if stock["module"]["sha256"] != PRODUCTION_MODULE_SHA:
        raise ValueError("Payload is not the accepted production module")
    scenario = next(item for item in SCENARIOS if item.name == "pushwall")
    locations = {}
    for level in range(10):
        state = base / f"level_{level:02d}/state_medium.w3l"
        paths = parse_package(state.read_bytes()).sections["paths"]
        locations[str(level + 1)] = [(i % 64, i // 64) for i, p in enumerate(paths) if p == MARKER]
    if args.output.exists():
        raise FileExistsError(args.output)
    with TemporaryDirectory(dir=args.output.parent) as work:
        scratch = Path(work)
        payload = scratch / "payload"
        shutil.copytree(base, payload)
        level = payload / "level_00"
        index = WALL[1] * 64 + WALL[0]
        tiles = level / "tiles.agnb"
        packages = sorted(level.glob("state_*.w3l"))
        if len(packages) != 4:
            raise ValueError("Expected all four E1L1 difficulty packages")
        medium = parse_package((level / "state_medium.w3l").read_bytes())
        texture, container = add_art(tiles.read_bytes(), scratch, medium.sections["tilemap"])
        tiles.write_bytes(container)
        for path in packages:
            package = parse_package(patch_state(path.read_bytes(), scenario))
            sections = dict(package.sections)
            tilemap = bytearray(sections["tilemap"])
            if sections["paths"][index] != MARKER or tilemap[index] != 4 or texture in tilemap:
                raise ValueError("Fixture wall identity or texture reservation changed")
            tilemap[index] = texture
            sections["tilemap"] = bytes(tilemap)
            sections["actors"] = b""
            path.write_bytes(build_package(replace(package, actor_count=0, sections=sections)))

        # On first entry the accepted app uploads this embedded E1L1 map
        # before motion initialization publishes the loaded W3L tilemap.
        app = payload / "wolf3d.bin"
        executable = app.read_bytes()
        embedded_map = medium.sections["tilemap"]
        if executable.count(embedded_map) != 1:
            raise ValueError("Expected a unique embedded stock E1L1 tilemap")
        tile_offset = executable.index(embedded_map) + index
        app.write_bytes(executable[:tile_offset] + bytes((texture,)) + executable[tile_offset + 1:])

        changed = [app, tiles, *packages]
        manifest = json.loads((payload / "payload.json").read_text())
        for path in changed:
            manifest["files"][str(path.relative_to(payload))] = {
                "bytes": path.stat().st_size, "sha256": sha(path),
            }
        manifest["fixture"] = {
            "task": "WOLF-SECRET-001", "stock_payload_sha256": sha(base / "payload.json"),
            "wall": WALL, "spawn": scenario.player_tile, "heading_degrees": scenario.angle,
            "texture": texture, "secret_locations_by_floor": locations,
            "embedded_tile_offset": tile_offset, "actors_removed_for_fixture": True,
            "stock_application_sha256": stock["files"]["wolf3d.bin"]["sha256"],
        }
        (payload / "payload.json").write_text(json.dumps(manifest, indent=2) + "\n")
        verify_payload(payload)
        verify_payload(base)
        payload.rename(args.output)
    print(json.dumps(manifest["fixture"], indent=2))


if __name__ == "__main__":
    main()
