#!/usr/bin/env python3
"""Stage D: pack each level's scoped tiles.jsonl/sprites.jsonl (Stage C) into
two separate AGNB 0.1 RIFF containers -- tiles.agnb and sprites.agnb -- per
Author decision 2026-07-31 ("one .agnb for tile assets, one for sprites.
split by episode and level to keep as much sram free on the esp32 as
possible").

Buffer ids inside each container are exactly the wire-protocol ids the VDP
renderer already expects (video/wolf3d/wolf3d_world.h's
Wolf3dWallBufferId()/Wolf3dSpriteBufferId(), mirrored in agnb/manifest.py's
buffer_id_for()) -- no remapping happens at load time, matching agnb_api.
inc's "explicit IDs only" contract.
"""

import argparse
import json
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agnb.container import BufferRecord, build_container  # noqa: E402
from agnb.manifest import ImageManifestEntry  # noqa: E402

GENERATED_DIR = Path(__file__).resolve().parents[3] / "assets" / "generated" / "wolf3d"


def _load_entries(path: Path) -> list[ImageManifestEntry]:
    return [
        ImageManifestEntry(**json.loads(line))
        for line in path.read_text().splitlines()
        if line.strip()
    ]


def pack_one(entries: list[ImageManifestEntry], asset_dir: Path, out_file: Path) -> None:
    records = [
        BufferRecord(
            name=entry.name,
            bufferId=entry.bufferId,
            width=entry.width,
            height=entry.height,
            rgba2File=asset_dir / entry.rgba2,
            dataSize=entry.dataSize,
        )
        for entry in entries
    ]
    container = build_container(records)
    out_file.write_bytes(container)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--levels-dir", type=Path, default=GENERATED_DIR / "levels")
    parser.add_argument("--asset-dir", type=Path, default=GENERATED_DIR / "processed")
    args = parser.parse_args()

    level_dirs = sorted(p for p in args.levels_dir.iterdir() if p.is_dir())
    if not level_dirs:
        raise RuntimeError(f"No level directories in {args.levels_dir}; run build_level_manifest.py first")

    for level_dir in level_dirs:
        tiles = _load_entries(level_dir / "tiles.jsonl")
        sprites = _load_entries(level_dir / "sprites.jsonl")

        tiles_file = level_dir / "tiles.agnb"
        sprites_file = level_dir / "sprites.agnb"
        pack_one(tiles, args.asset_dir, tiles_file)
        pack_one(sprites, args.asset_dir, sprites_file)
        print(
            f"{level_dir.name}: {tiles_file.name} ({tiles_file.stat().st_size} bytes, "
            f"{len(tiles)} images), {sprites_file.name} "
            f"({sprites_file.stat().st_size} bytes, {len(sprites)} images)"
        )


if __name__ == "__main__":
    main()
