#!/usr/bin/env python3
"""Stage A: export every real Wolf3D wall, door, and sprite texture from a
shareware VSWAP.WL1 as an individual PNG, one file per VDP buffer asset.

Unlike this repo's separate src/toolchain project (which only decodes one
representative frame per enemy/boss type for Tiled map-authoring
placeholders -- a deliberate, documented simplification for that project's
different purpose), this script exports EVERY sprite chunk in the file
unconditionally. Per Author decision 2026-07-31 ("we need to build the
animation system from the jump so that we don't corner ourselves later"),
the Wolf3D game engine's asset pipeline must not repeat that single-frame
shortcut: whichever shapenum the eZ80 side's actor state machine resolves
at runtime, a real converted buffer must already exist for it.

Wall textures: each wall tile id (1..N) maps to a (horiz, vert) VSWAP chunk
pair (formats.vswap.wall_tile_to_chunks). Per Author decision 2026-07-31
("keep it simple, pick one and run with it, revisit if it doesn't look
right"), this script exports only the horizontal-facing chunk of each pair
-- real shareware wall art is conventionally identical between the two
anyway. Revisit if the tkinter viewer (Stage E) shows a wall that looks
wrong.

Door textures: grounded in WL_DRAW.C's DOORWALL constant (see
formats/vswap.py's door_kind_to_chunks docstring) -- only 4 distinct door
textures exist in the whole game (normal/jamb/elevator/locked), each its own
horiz/vert chunk pair, independent of the ordinary per-level wall tile ids.
This project assigns them fixed textureIds 121-124 (comfortably above every
real shareware wall id, which top out at 49) so they share the same
Wolf3dWallBufferId() formula/space as ordinary walls:

    121 = normal door face   122 = door jamb/frame
    123 = elevator door face 124 = locked door face (all 4 lock colors)

Output: one PNG per asset under <out>/walls/wall_<id>.png (or
door_<kind>.png) and <out>/sprites/sprite_<shapenum>.png, plus a
pre-conversion manifest (orig_assets.jsonl: kind, assetId, name, png,
width, height) that scripts/convert_assets.py consumes next.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from formats import vswap  # noqa: E402

DEFAULT_VSWAP = (
    Path(__file__).resolve().parents[4] / "orig" / "data" / "VSWAP.WL1"
)
TRANSPARENT_RGBA = (0, 0, 0, 0)


def export_wall(vs: vswap.VSwapFile, texture_id: int, out_dir: Path) -> dict | None:
    horiz_chunk, _vert_chunk = vswap.wall_tile_to_chunks(texture_id)
    chunk = vs.chunks[horiz_chunk]
    if not chunk:
        # Shareware WL1 reserves wall-id slots for the full retail texture
        # set but only ships episode 1's art; unused ids are zero-length.
        return None
    image = vswap.chunk_to_image(chunk)
    name = f"wall_{texture_id:03d}"
    png_path = out_dir / f"{name}.png"
    image.save(png_path, "PNG")
    return {
        "kind": "wall",
        "assetId": texture_id,
        "source": f"VSWAP.WL1 chunk {horiz_chunk}",
        "name": name,
        "png": png_path.name,
        "width": image.width,
        "height": image.height,
    }


def export_door(vs: vswap.VSwapFile, kind: str, texture_id: int, out_dir: Path) -> dict:
    horiz_chunk, _vert_chunk = vswap.door_kind_to_chunks(vs, kind)
    chunk = vs.chunks[horiz_chunk]
    image = vswap.chunk_to_image(chunk)
    name = f"door_{kind}"
    png_path = out_dir / f"{name}.png"
    image.save(png_path, "PNG")
    return {
        "kind": "wall",
        "assetId": texture_id,
        "source": f"VSWAP.WL1 chunk {horiz_chunk}",
        "name": name,
        "png": png_path.name,
        "width": image.width,
        "height": image.height,
    }


def export_sprite(vs: vswap.VSwapFile, chunk_index: int, out_dir: Path) -> dict | None:
    chunk = vs.chunks[chunk_index]
    if not chunk:
        return None
    shapenum = chunk_index - vs.spritestart
    image = vswap.sprite_chunk_to_image(chunk)
    name = f"sprite_{shapenum:04d}"
    png_path = out_dir / f"{name}.png"
    image.save(png_path, "PNG")
    return {
        "kind": "sprite",
        "assetId": shapenum,
        "source": f"VSWAP.WL1 chunk {chunk_index}",
        "name": name,
        "png": png_path.name,
        "width": image.width,
        "height": image.height,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vswap", type=Path, default=DEFAULT_VSWAP)
    parser.add_argument(
        "--out",
        type=Path,
        default=Path(__file__).resolve().parents[3]
        / "assets"
        / "generated"
        / "wolf3d"
        / "orig",
    )
    args = parser.parse_args()

    data = args.vswap.read_bytes()
    vs = vswap.read_vswap(data)

    walls_dir = args.out / "walls"
    sprites_dir = args.out / "sprites"
    walls_dir.mkdir(parents=True, exist_ok=True)
    sprites_dir.mkdir(parents=True, exist_ok=True)

    entries = []

    num_walls = vswap.num_wall_tiles(vs)
    exported_walls = 0
    for texture_id in range(1, num_walls + 1):
        entry = export_wall(vs, texture_id, walls_dir)
        if entry is not None:
            entries.append(entry)
            exported_walls += 1
    print(f"Exported {exported_walls}/{num_walls} wall textures")

    door_texture_ids = {
        vswap.DOOR_KIND_NORMAL: 121,
        vswap.DOOR_KIND_JAMB: 122,
        vswap.DOOR_KIND_ELEVATOR: 123,
        vswap.DOOR_KIND_LOCKED: 124,
    }
    for kind, texture_id in door_texture_ids.items():
        entries.append(export_door(vs, kind, texture_id, walls_dir))
        print(f"Exported door texture: {kind} (textureId {texture_id})")

    num_sprite_chunks = vs.soundstart - vs.spritestart
    exported_sprites = 0
    for offset in range(num_sprite_chunks):
        chunk_index = vs.spritestart + offset
        entry = export_sprite(vs, chunk_index, sprites_dir)
        if entry is not None:
            entries.append(entry)
            exported_sprites += 1
    print(f"Exported {exported_sprites}/{num_sprite_chunks} sprite frames")

    manifest_path = args.out / "orig_assets.jsonl"
    with manifest_path.open("w") as f:
        for entry in entries:
            f.write(json.dumps(entry) + "\n")
    print(f"Wrote {manifest_path} with {len(entries)} entries")


if __name__ == "__main__":
    main()
