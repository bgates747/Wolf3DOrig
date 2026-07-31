#!/usr/bin/env python3
"""Stage B: palette-reduce Stage A's exported PNGs to the Agon64 (RGB222)
palette and pack them to on-disk RGBA2222, using the installed agonutils
extension -- writes agonport/assets/generated/wolf3d/processed/ plus the
final images.jsonl manifest (agnb/manifest.py's schema) that scripts/
pack_agnb.py and scripts/build_level_manifest.py consume next.

Opaque wall and door textures default to Floyd-Steinberg dithering. Sprites
default to nearest-colour RGB with no dithering, which preserves cleaner
silhouettes. Use --method to override both groups for an A/B comparison, or
the kind-specific options to change one group.
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
DEFAULT_OVERRIDE_DIR = Path(__file__).resolve().parents[3] / "assets" / "overrides" / "wolf3d"
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


def use_palettized_override(
    override_png: Path, source_png: Path, destination: Path, transparent: bool
) -> None:
    """Copy a durable hand edit and encode it without applying dithering again."""
    with Image.open(source_png) as source, Image.open(override_png) as override:
        if override.size != source.size:
            raise ValueError(
                f"Override {override_png} is {override.size}, expected {source.size}"
            )
    shutil.copy2(override_png, destination)
    transparent_color = TRANSPARENT_RGBA if transparent else None
    au.img_to_rgba2(
        str(destination),
        str(destination.with_suffix(".rgba2")),
        str(PALETTE_FILE),
        "rgb",
        transparent_color,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--in-dir", type=Path, default=GENERATED_DIR / "orig")
    parser.add_argument("--out-dir", type=Path, default=GENERATED_DIR / "processed")
    parser.add_argument(
        "--override-dir",
        type=Path,
        default=DEFAULT_OVERRIDE_DIR,
        help="tracked palettized PNG overrides (default: %(default)s)",
    )
    parser.add_argument(
        "--method",
        default=None,
        choices=["rgb", "hsv", "bayer", "floyd", "atkinson"],
        help="override the conversion method for every image kind",
    )
    parser.add_argument(
        "--wall-method",
        default="floyd",
        choices=["rgb", "hsv", "bayer", "floyd", "atkinson"],
        help="wall/door conversion method (default: floyd)",
    )
    parser.add_argument(
        "--sprite-method",
        default="rgb",
        choices=["rgb", "hsv", "bayer", "floyd", "atkinson"],
        help="sprite conversion method (default: rgb/no dithering)",
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
        method = args.method or (
            args.wall_method if raw["kind"] == "wall" else args.sprite_method
        )
        source_png = args.in_dir / ("walls" if raw["kind"] == "wall" else "sprites") / raw["png"]
        destination = args.out_dir / raw["png"]
        override_png = args.override_dir / (
            "walls" if raw["kind"] == "wall" else "sprites"
        ) / raw["png"]
        # Sprites are camera-facing billboards with real transparent
        # background pixels (see formats/vswap.py's sprite_chunk_to_image);
        # walls/doors are fully opaque 64x64 tiles.
        if override_png.is_file():
            use_palettized_override(
                override_png,
                source_png,
                destination,
                transparent=raw["kind"] == "sprite",
            )
            selected_source = f"hand-edited override: {override_png}"
            print(f"Used override {raw['name']} (already palettized)")
        else:
            convert_one(
                source_png,
                destination,
                method,
                transparent=raw["kind"] == "sprite",
            )
            selected_source = raw["source"]
            print(f"Converted {raw['name']} ({method})")

        rgba2_file = destination.with_suffix(".rgba2")
        with Image.open(destination) as image:
            width, height = image.size
        entries.append(
            ImageManifestEntry(
                include=True,
                kind=raw["kind"],
                assetId=raw["assetId"],
                source=selected_source,
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
    manifest_out = args.out_dir / "images.jsonl"
    write_manifest(manifest_out, entries)
    print(f"Wrote {manifest_out} with {len(entries)} entries")


if __name__ == "__main__":
    main()
