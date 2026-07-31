#!/usr/bin/env python3
"""Stage B: palette-reduce Stage A's exported PNGs to the Agon64 (RGB222)
palette and pack them to on-disk RGBA2222, using the installed agonutils
extension -- writes agonport/assets/generated/wolf3d/processed/ plus the
final images.jsonl manifest (agnb/manifest.py's schema) that scripts/
pack_agnb.py and scripts/build_level_manifest.py consume next.

Default conversion method is "floyd" (Floyd-Steinberg dithering), per
Author decision 2026-07-31 ("floyd-steinberg approved", after A/B testing
against "rgb" no-dither and "bayer" ordered dithering). Pass --method to
try "rgb", "hsv", "bayer", or "atkinson" instead.
"""

import argparse
import json
import shutil
import sys
from pathlib import Path

import agonutils as au
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agnb.manifest import (  # noqa: E402
    ImageManifestEntry,
    buffer_id_for,
    write_manifest,
)

GENERATED_DIR = Path(__file__).resolve().parents[3] / "assets" / "generated" / "wolf3d"
PALETTE_FILE = Path(__file__).resolve().parents[1] / "palettes" / "Agon64.gpl"
TRANSPARENT_RGBA = (0, 0, 0, 0)


def convert_one(source_png: Path, destination: Path, method: str, transparent: bool) -> None:
    shutil.copy2(source_png, destination)
    transparent_color = TRANSPARENT_RGBA if transparent else None
    au.convert_to_palette(
        str(destination), str(destination), str(PALETTE_FILE), method, transparent_color
    )
    au.img_to_rgba2(
        str(destination),
        str(destination.with_suffix(".rgba2")),
        str(PALETTE_FILE),
        method,
        transparent_color,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--in-dir", type=Path, default=GENERATED_DIR / "orig")
    parser.add_argument("--out-dir", type=Path, default=GENERATED_DIR / "processed")
    parser.add_argument(
        "--method",
        default="floyd",
        choices=["rgb", "hsv", "bayer", "floyd", "atkinson"],
        help="agonutils palette_conversion_method (case-insensitive in the C "
        "extension; lowercased here for consistency).",
    )
    args = parser.parse_args()

    manifest_path = args.in_dir / "orig_assets.jsonl"
    raw_entries = [
        json.loads(line)
        for line in manifest_path.read_text().splitlines()
        if line.strip()
    ]
    if not raw_entries:
        raise RuntimeError(f"No entries in {manifest_path}; run export_vswap_art.py first")

    if args.out_dir.exists():
        shutil.rmtree(args.out_dir)
    args.out_dir.mkdir(parents=True)

    entries = []
    for raw in raw_entries:
        source_png = args.in_dir / ("walls" if raw["kind"] == "wall" else "sprites") / raw["png"]
        destination = args.out_dir / raw["png"]
        # Sprites are camera-facing billboards with real transparent
        # background pixels (see formats/vswap.py's sprite_chunk_to_image);
        # walls/doors are fully opaque 64x64 tiles.
        convert_one(source_png, destination, args.method, transparent=raw["kind"] == "sprite")

        rgba2_file = destination.with_suffix(".rgba2")
        with Image.open(destination) as image:
            width, height = image.size
        entries.append(
            ImageManifestEntry(
                include=True,
                kind=raw["kind"],
                assetId=raw["assetId"],
                source=raw["source"],
                name=raw["name"],
                bufferId=buffer_id_for(raw["kind"], raw["assetId"]),
                width=width,
                height=height,
                format=1,
                png=destination.name,
                rgba2=rgba2_file.name,
                dataSize=rgba2_file.stat().st_size,
            )
        )
        print(f"Converted {raw['name']} ({args.method})")

    manifest_out = args.out_dir / "images.jsonl"
    write_manifest(manifest_out, entries)
    print(f"Wrote {manifest_out} with {len(entries)} entries")


if __name__ == "__main__":
    main()
