#!/usr/bin/env python3
"""Extract and pack the original WL1 status-bar art for the Agon port.

Inputs are the bundled ``VGADICT.WL1``, ``VGAHEAD.WL1``, and
``VGAGRAPH.WL1`` files.  Outputs are source/converted PNGs, RGBA2222 payloads,
a JSONL audit manifest, a generated eZ80 constants include, and ``hud.agnb``.

Stable VDP contract:

* each original picture chunk uses buffer ``0x4000 + chunkId``;
* chunks 55..96 provide the original level-end portrait and picture font;
* chunk 98 is the original 320x40 ``STATUSBARPIC``;
* chunks 103..144 provide weapons, key icons, digits, and face frames;
* buffers 0x4100..0x4101 contain durable original-layout composites for an
  ordinary floor and the secret floor respectively.

The renderer draws chunk 98 directly; no synthetic status-panel extension is
generated or packed.  The level-end composites reproduce ``WL_INTER.C`` from
the actual archive pictures and palette.  Splash/title art is out of scope.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

import agonutils as au
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agnb.container import BufferRecord, build_container  # noqa: E402
from formats.hud import (  # noqa: E402
    HUD_CHUNKS,
    HUD_CHUNK_BUFFER_BASE,
    HUD_CHUNK_NAMES,
    HUD_COMPOSITE_BUFFER_BASE,
    HUD_COMPOSITE_BUFFER_IDS,
    HUD_EXPECTED_DIMENSIONS,
    STATUSBAR_CHUNK,
    chunk_buffer_id,
)
from formats.palette import WOLF3D_PALETTE_RGB888  # noqa: E402
from formats.vgagraph import read_vgagraph  # noqa: E402

SCRIPT_FILE = Path(__file__).resolve()
TOOLS_ROOT = SCRIPT_FILE.parents[1]
PROJECT_ROOT = next(
    (
        parent
        for parent in SCRIPT_FILE.parents
        if (parent / "orig" / "data" / "VGAGRAPH.WL1").is_file()
    ),
    Path.cwd(),
)
DEFAULT_DATA_DIR = PROJECT_ROOT / "orig" / "data"
DEFAULT_OUT_DIR = PROJECT_ROOT / "agonport" / "assets" / "generated" / "wolf3d" / "hud"
DEFAULT_OVERRIDE_DIR = (
    PROJECT_ROOT / "agonport" / "assets" / "overrides" / "wolf3d" / "hud"
)
DEFAULT_PALETTE_FILE = TOOLS_ROOT / "palettes" / "Agon64.gpl"
IMAGE_FORMAT_RGBA2222 = 1
SCREEN_SIZE = (320, 200)
LEVEL_END_BACKGROUND = 127


@dataclass(frozen=True)
class HudManifestEntry:
    name: str
    source: str
    chunkId: int | None
    bufferId: int
    width: int
    height: int
    plotX: int
    plotY: int
    format: int
    png: str
    rgba2: str
    dataSize: int


@dataclass(frozen=True)
class ComposedImage:
    image: Image.Image
    plot_x: int
    plot_y: int


def _level_end_glyph_name(character: str) -> str:
    if character == ":":
        return "level_end_colon"
    if character == "%":
        return "level_end_percent"
    if character == "!":
        return "level_end_exclamation"
    if character == "'":
        return "level_end_apostrophe"
    if character.isdigit():
        return f"level_end_digit_{character}"
    if character.isalpha() and len(character) == 1:
        return f"level_end_letter_{character.lower()}"
    raise ValueError(f"WL1 level-end picture font cannot encode {character!r}")


def _draw_level_end_text(
    image: Image.Image,
    pictures: dict[str, Image.Image],
    xy: tuple[int, int],
    text: str,
) -> None:
    """Reproduce ``WL_INTER.C::Write`` using bundled picture glyphs."""

    start_x, y = xy
    x = start_x
    for character in text:
        if character == "\n":
            x = start_x
            y += 16
            continue
        if character == " ":
            x += 16
            continue
        glyph = pictures[_level_end_glyph_name(character)]
        image.paste(glyph, (x, y))
        x += glyph.width


def _level_end_canvas(pictures: dict[str, Image.Image]) -> Image.Image:
    image = Image.new(
        "RGB", SCREEN_SIZE, WOLF3D_PALETTE_RGB888[LEVEL_END_BACKGROUND]
    )
    image.paste(pictures["level_end_guy_1"], (0, 16))
    return image


def _compose_floor_complete(
    pictures: dict[str, Image.Image],
) -> Image.Image:
    """Compose the invariant portion of an ordinary ``LevelCompleted``."""

    image = _level_end_canvas(pictures)
    _draw_level_end_text(image, pictures, (14 * 8, 2 * 8), "floor\ncompleted")
    _draw_level_end_text(image, pictures, (14 * 8, 7 * 8), "bonus     0")
    _draw_level_end_text(image, pictures, (16 * 8, 10 * 8), "time")
    _draw_level_end_text(image, pictures, (16 * 8, 12 * 8), " par")
    _draw_level_end_text(image, pictures, (9 * 8, 14 * 8), "kill ratio    %")
    _draw_level_end_text(image, pictures, (5 * 8, 16 * 8), "secret ratio    %")
    _draw_level_end_text(image, pictures, (1 * 8, 18 * 8), "treasure ratio    %")
    return image


def _compose_secret_floor_complete(
    pictures: dict[str, Image.Image],
) -> Image.Image:
    """Compose the original non-SPEAR secret-floor completion screen."""

    image = _level_end_canvas(pictures)
    _draw_level_end_text(
        image, pictures, (14 * 8, 4 * 8), "secret floor\n completed!"
    )
    _draw_level_end_text(image, pictures, (10 * 8, 16 * 8), "15000 bonus!")
    return image


def _compose_images(
    pictures: dict[str, Image.Image],
) -> dict[str, ComposedImage]:
    images = {
        "floor_complete_base": ComposedImage(
            _compose_floor_complete(pictures), 0, 0
        ),
        "secret_floor_complete_base": ComposedImage(
            _compose_secret_floor_complete(pictures), 0, 0
        ),
    }
    if set(images) != set(HUD_COMPOSITE_BUFFER_IDS):
        raise AssertionError("Composed HUD image set disagrees with buffer contract")
    return images


def convert_to_rgba2222(
    source_png: Path,
    processed_png: Path,
    rgba2_file: Path,
    palette_file: Path,
    method: str,
) -> None:
    """Apply the project's established agonutils/Agon64 conversion path."""
    shutil.copy2(source_png, processed_png)
    au.convert_to_palette(
        str(processed_png), str(processed_png), str(palette_file), method, None
    )
    au.img_to_rgba2(
        str(processed_png), str(rgba2_file), str(palette_file), method, None
    )


def _write_constants(path: Path, entries: list[HudManifestEntry]) -> None:
    lines = [
        "; Generated by scripts/build_hud_assets.py -- do not edit.\n",
        "; Original chunk assets: bufferId = $4000 + chunkId.\n",
        f"W3D_HUD_CHUNK_BUFFER_BASE equ ${HUD_CHUNK_BUFFER_BASE:04X}\n",
        f"W3D_HUD_COMPOSITE_BUFFER_BASE equ ${HUD_COMPOSITE_BUFFER_BASE:04X}\n",
        "\n",
    ]
    for entry in entries:
        symbol = f"W3D_HUD_{entry.name.upper()}_BUFFER"
        origin = (
            f"chunk {entry.chunkId}"
            if entry.chunkId is not None
            else "composed from WL1 v1.4 resources"
        )
        prefix = f"W3D_HUD_{entry.name.upper()}"
        lines.extend(
            (
                f"{symbol} equ ${entry.bufferId:04X} ; {origin}\n",
                f"{prefix}_WIDTH equ {entry.width}\n",
                f"{prefix}_HEIGHT equ {entry.height}\n",
                f"{prefix}_X equ {entry.plotX}\n",
                f"{prefix}_Y equ {entry.plotY}\n",
            )
        )
    path.write_text("".join(lines))


def build_hud_assets(
    data_dir: Path,
    out_dir: Path,
    palette_file: Path,
    method: str = "rgb",
    override_dir: Path | None = DEFAULT_OVERRIDE_DIR,
) -> list[HudManifestEntry]:
    """Build all staged HUD artifacts and return their manifest entries."""
    archive = read_vgagraph(
        data_dir / "VGADICT.WL1",
        data_dir / "VGAHEAD.WL1",
        data_dir / "VGAGRAPH.WL1",
    )
    original_dir = out_dir / "orig"
    processed_dir = out_dir / "processed"
    for generated_dir in (original_dir, processed_dir):
        if generated_dir.exists():
            shutil.rmtree(generated_dir)
        generated_dir.mkdir(parents=True)
    out_dir.mkdir(parents=True, exist_ok=True)

    source_images: list[tuple[str, str, int, int, Image.Image]] = []
    raw_images: dict[str, Image.Image] = {}
    for chunk_id in HUD_CHUNKS:
        image = archive.decode_picture(chunk_id)
        expected = HUD_EXPECTED_DIMENSIONS[chunk_id]
        if image.size != expected:
            raise ValueError(
                f"Chunk {chunk_id} dimensions changed: {image.size}, "
                f"expected {expected}"
            )
        name = HUD_CHUNK_NAMES[chunk_id]
        source = f"VGAGRAPH.WL1 chunk {chunk_id}"
        override_file = override_dir / f"{name}.png" if override_dir else None
        if override_file and override_file.is_file():
            with Image.open(override_file) as override:
                override_rgb = override.convert("RGB")
            if override_rgb.size != expected:
                raise ValueError(
                    f"HUD override {override_file} is {override_rgb.size}, "
                    f"expected {expected}"
                )
            image = override_rgb.quantize(palette=image)
            source = f"hand-edited override: {override_file}"
        source_images.append((name, source, chunk_id, chunk_buffer_id(chunk_id), image))
        raw_images[name] = image.convert("RGB")

    entries: list[HudManifestEntry] = []
    records: list[BufferRecord] = []
    for name, source, chunk_id, buffer_id, image in source_images:
        source_png = original_dir / f"{name}.png"
        processed_png = processed_dir / f"{name}.png"
        rgba2_file = processed_dir / f"{name}.rgba2"
        image.save(source_png, "PNG")
        convert_to_rgba2222(source_png, processed_png, rgba2_file, palette_file, method)

        width, height = image.size
        rgba2 = rgba2_file.read_bytes()
        if len(rgba2) != width * height:
            raise ValueError(
                f"RGBA2222 size for {name} is {len(rgba2)}, expected {width * height}"
            )
        entry = HudManifestEntry(
            name=name,
            source=source,
            chunkId=chunk_id,
            bufferId=buffer_id,
            width=width,
            height=height,
            plotX=0,
            plotY=0,
            format=IMAGE_FORMAT_RGBA2222,
            png=str(processed_png.relative_to(out_dir)),
            rgba2=str(rgba2_file.relative_to(out_dir)),
            dataSize=len(rgba2),
        )
        entries.append(entry)
        records.append(
            BufferRecord(
                name=name,
                bufferId=buffer_id,
                width=width,
                height=height,
                rgba2File=rgba2_file,
                dataSize=len(rgba2),
            )
        )

    for name, composed in _compose_images(raw_images).items():
        source_png = original_dir / f"{name}.png"
        processed_png = processed_dir / f"{name}.png"
        rgba2_file = processed_dir / f"{name}.rgba2"
        composed.image.save(source_png, "PNG")
        convert_to_rgba2222(
            source_png, processed_png, rgba2_file, palette_file, method
        )

        width, height = composed.image.size
        rgba2 = rgba2_file.read_bytes()
        if len(rgba2) != width * height:
            raise ValueError(
                f"RGBA2222 size for {name} is {len(rgba2)}, "
                f"expected {width * height}"
            )
        entry = HudManifestEntry(
            name=name,
            source="composed from original WL1 v1.4 level-end resources",
            chunkId=None,
            bufferId=HUD_COMPOSITE_BUFFER_IDS[name],
            width=width,
            height=height,
            plotX=composed.plot_x,
            plotY=composed.plot_y,
            format=IMAGE_FORMAT_RGBA2222,
            png=str(processed_png.relative_to(out_dir)),
            rgba2=str(rgba2_file.relative_to(out_dir)),
            dataSize=len(rgba2),
        )
        entries.append(entry)
        records.append(
            BufferRecord(
                name=name,
                bufferId=entry.bufferId,
                width=width,
                height=height,
                rgba2File=rgba2_file,
                dataSize=len(rgba2),
            )
        )

    manifest_path = out_dir / "hud_assets.jsonl"
    manifest_path.write_text(
        "".join(json.dumps(asdict(entry), sort_keys=True) + "\n" for entry in entries)
    )
    (out_dir / "hud.agnb").write_bytes(build_container(records))
    _write_constants(out_dir / "hud_buffers.inc", entries)
    return entries


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--palette", type=Path, default=DEFAULT_PALETTE_FILE)
    parser.add_argument(
        "--override-dir",
        type=Path,
        default=DEFAULT_OVERRIDE_DIR,
        help="tracked hand-edited PNG overrides (default: %(default)s)",
    )
    parser.add_argument(
        "--method",
        default="rgb",
        choices=("rgb", "hsv", "bayer", "floyd", "atkinson"),
        help="agonutils palette-conversion method (default: rgb/no dithering)",
    )
    args = parser.parse_args()

    entries = build_hud_assets(
        args.data_dir, args.out_dir, args.palette, args.method, args.override_dir
    )
    total_pixels = sum(entry.dataSize for entry in entries)
    originals = sum(entry.chunkId is not None for entry in entries)
    composites = len(entries) - originals
    print(
        f"Wrote {args.out_dir / 'hud.agnb'}: {originals} original and "
        f"{composites} composed images, {total_pixels} RGBA2222 bytes"
    )
    print(
        f"Original chunks: 55..96, {STATUSBAR_CHUNK}, 103..144 at "
        f"${HUD_CHUNK_BUFFER_BASE:04X}+chunk; composites at "
        f"${HUD_COMPOSITE_BUFFER_BASE:04X}.."
    )


if __name__ == "__main__":
    main()
