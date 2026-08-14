#!/usr/bin/env python3
"""Extract, compose, convert, and pack the WL1 application-shell art."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

import agonutils as au
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agnb.container import BufferRecord, build_container  # noqa: E402
from formats.palette import WOLF3D_PALETTE_RGB888  # noqa: E402
from formats.shell import (  # noqa: E402
    BKGDCOLOR,
    BORD2COLOR,
    BORDCOLOR,
    COMPOSED_DEACTIVE_RGB,
    DEACTIVE,
    DIFFICULTY_LABELS,
    DIFFICULTY_NAMES,
    EPISODE_LABELS,
    EPISODE_UNAVAILABLE_MESSAGE,
    HIGHLIGHT,
    MAIN_LABELS,
    ORDER_HIGHLIGHT,
    ORDER_NORMAL,
    READHCOLOR,
    SHELL_CHUNKS,
    SHELL_CHUNK_BUFFER_BASE,
    SHELL_CHUNK_NAMES,
    SHELL_COMPOSITE_BUFFER_BASE,
    SHELL_COMPOSITE_BUFFER_IDS,
    SHELL_EXPECTED_DIMENSIONS,
    STRIPE,
    TEXTCOLOR,
    WolfFont,
    chunk_buffer_id,
    decode_wolf_font,
)
from formats.vgagraph import read_vgagraph  # noqa: E402

SCRIPT_FILE = Path(__file__).resolve()
TOOLS_ROOT = SCRIPT_FILE.parents[1]
PROJECT_ROOT = SCRIPT_FILE.parents[4]
DEFAULT_DATA_DIR = PROJECT_ROOT / "orig/data"
DEFAULT_OUT_DIR = PROJECT_ROOT / "agonport/assets/generated/wolf3d/shell"
DEFAULT_OVERRIDE_DIR = PROJECT_ROOT / "agonport/assets/overrides/wolf3d/shell"
DEFAULT_PALETTE_FILE = TOOLS_ROOT / "palettes/Agon64.gpl"
IMAGE_FORMAT_RGBA2222 = 1
SCREEN_SIZE = (320, 200)


@dataclass(frozen=True)
class ShellManifestEntry:
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


def _color(
    value: int | tuple[int, int, int]
) -> tuple[int, int, int]:
    if isinstance(value, tuple):
        return value
    return WOLF3D_PALETTE_RGB888[value]


def _draw_hline(
    draw: ImageDraw.ImageDraw, x1: int, x2: int, y: int, color: int
) -> None:
    draw.line((x1, y, x2, y), fill=_color(color))


def _draw_vline(
    draw: ImageDraw.ImageDraw, y1: int, y2: int, x: int, color: int
) -> None:
    draw.line((x, y1, x, y2), fill=_color(color))


def _draw_outline(
    image: Image.Image,
    x: int,
    y: int,
    width: int,
    height: int,
    color1: int,
    color2: int,
) -> None:
    """Reproduce ``DrawOutline``'s inclusive right and bottom edges."""

    draw = ImageDraw.Draw(image)
    _draw_hline(draw, x, x + width, y, color2)
    _draw_vline(draw, y, y + height, x, color2)
    _draw_hline(draw, x, x + width, y + height, color1)
    _draw_vline(draw, y, y + height, x + width, color1)


def _draw_window(
    image: Image.Image, x: int, y: int, width: int, height: int, color: int
) -> None:
    """Reproduce the original ``VWB_Bar`` plus ``DrawWindow`` outline."""

    ImageDraw.Draw(image).rectangle(
        (x, y, x + width - 1, y + height - 1), fill=_color(color)
    )
    _draw_outline(image, x, y, width, height, BORD2COLOR, DEACTIVE)


def _draw_stripes(image: Image.Image, y: int = 10) -> None:
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, y, 319, y + 23), fill=_color(0))
    _draw_hline(draw, 0, 319, y + 22, STRIPE)


def _draw_text(
    image: Image.Image,
    font: WolfFont,
    xy: tuple[int, int],
    text: str,
    color: int | tuple[int, int, int],
) -> None:
    """Reproduce ``VW_DrawPropString``'s foreground-only glyph plotting."""

    start_x, y = xy
    x = start_x
    pixels = image.load()
    rgb = _color(color)
    for character in text:
        if character == "\n":
            x = start_x
            y += font.height
            continue
        width, height, mask = font.glyph_mask(character)
        for glyph_y in range(height):
            row = glyph_y * width
            for glyph_x in range(width):
                if mask[row + glyph_x]:
                    pixels[x + glyph_x, y + glyph_y] = rgb
        x += width


def _draw_centered(
    image: Image.Image, font: WolfFont, y: int, text: str, color: int
) -> None:
    width = font.measure_line(text)
    _draw_text(image, font, ((SCREEN_SIZE[0] - width) // 2, y), text, color)


def _text_overlay(font: WolfFont, text: str, color: int) -> Image.Image:
    width, height = font.measure(text)
    image = Image.new("RGB", (width, height), _color(BKGDCOLOR))
    _draw_text(image, font, (0, 0), text, color)
    return image


def _compose_main(raw: dict[str, Image.Image], font: WolfFont) -> Image.Image:
    image = Image.new("RGB", SCREEN_SIZE, _color(BORDCOLOR))
    # Preserve the source order: the bottom of this bitmap is deliberately
    # covered by the main window, as it was by DrawMainMenu.
    image.paste(raw["mouse_back"], (112, 184))
    _draw_stripes(image)
    image.paste(raw["options_heading"], (84, 0))
    _draw_window(image, 68, 52, 178, 136, BKGDCOLOR)
    for index, label in enumerate(MAIN_LABELS):
        # Only these two commands are live in the first shell implementation.
        color = TEXTCOLOR if index in (0, 9) else COMPOSED_DEACTIVE_RGB
        _draw_text(image, font, (100, 55 + index * 13), label, color)
    return image


def _compose_episode(raw: dict[str, Image.Image], font: WolfFont) -> Image.Image:
    image = Image.new("RGB", SCREEN_SIZE, _color(BORDCOLOR))
    image.paste(raw["mouse_back"], (112, 184))
    _draw_window(image, 6, 19, 308, 162, BKGDCOLOR)
    _draw_centered(image, font, 2, "Which episode to play?", READHCOLOR)
    for index, label in enumerate(EPISODE_LABELS):
        y = 23 + index * 26
        _draw_text(
            image,
            font,
            (98, y),
            label,
            TEXTCOLOR if index == 0 else ORDER_NORMAL,
        )
        image.paste(raw[f"episode_{index + 1}"], (42, y))
    return image


def _compose_difficulty(raw: dict[str, Image.Image], font: WolfFont) -> Image.Image:
    image = Image.new("RGB", SCREEN_SIZE, _color(BORDCOLOR))
    image.paste(raw["mouse_back"], (112, 184))
    _draw_text(image, font, (70, 68), "How tough are you?", READHCOLOR)
    _draw_window(image, 45, 90, 225, 67, BKGDCOLOR)
    for index, label in enumerate(DIFFICULTY_LABELS):
        _draw_text(image, font, (74, 100 + index * 13), label, TEXTCOLOR)
    return image


def _compose_unavailable_notice(font: WolfFont) -> Image.Image:
    text_width, text_height = font.measure(EPISODE_UNAVAILABLE_MESSAGE)
    if (text_width, text_height) != (240, 52):
        raise ValueError(
            "Unexpected WL1 message metrics: "
            f"{text_width}x{text_height}, expected 240x52"
        )

    # Message() chooses mw=240 and draws a nominal 250x62 window.  Its line
    # primitives include the right/bottom coordinate, producing 251x63 pixels.
    image = Image.new("RGB", (251, 63), _color(TEXTCOLOR))
    _draw_window(image, 0, 0, 250, 62, TEXTCOLOR)
    _draw_outline(image, 0, 0, 250, 62, 0, HIGHLIGHT)
    _draw_text(image, font, (5, 5), EPISODE_UNAVAILABLE_MESSAGE, 0)
    return image


def _compose_images(
    raw: dict[str, Image.Image], font: WolfFont
) -> dict[str, ComposedImage]:
    images: dict[str, ComposedImage] = {
        "main_base": ComposedImage(_compose_main(raw, font), 0, 0),
        "episode_base": ComposedImage(_compose_episode(raw, font), 0, 0),
        "difficulty_base": ComposedImage(_compose_difficulty(raw, font), 0, 0),
        "episode_unavailable_notice": ComposedImage(
            _compose_unavailable_notice(font), 35, 69
        ),
        "main_new_game_selected": ComposedImage(
            _text_overlay(font, MAIN_LABELS[0], HIGHLIGHT), 100, 55
        ),
        "main_quit_selected": ComposedImage(
            _text_overlay(font, MAIN_LABELS[9], HIGHLIGHT), 100, 172
        ),
    }
    for index, label in enumerate(EPISODE_LABELS, start=1):
        images[f"episode_{index}_selected"] = ComposedImage(
            _text_overlay(
                font, label, HIGHLIGHT if index == 1 else ORDER_HIGHLIGHT
            ),
            98,
            23 + (index - 1) * 26,
        )
    for index, (name, label) in enumerate(
        zip(DIFFICULTY_NAMES, DIFFICULTY_LABELS)
    ):
        images[f"difficulty_{name}_selected"] = ComposedImage(
            _text_overlay(font, label, HIGHLIGHT), 74, 100 + index * 13
        )
    if set(images) != set(SHELL_COMPOSITE_BUFFER_IDS):
        raise AssertionError("Composed shell image set disagrees with buffer contract")
    return images


def _convert(source: Path, processed: Path, rgba2: Path, palette: Path) -> None:
    shutil.copy2(source, processed)
    au.convert_to_palette(str(processed), str(processed), str(palette), "rgb", None)
    au.img_to_rgba2(str(processed), str(rgba2), str(palette), "rgb", None)


def _write_constants(path: Path, entries: list[ShellManifestEntry]) -> None:
    lines = [
        "; Generated by build_shell_assets.py -- do not edit.\n",
        f"W3D_SHELL_CHUNK_BUFFER_BASE: equ ${SHELL_CHUNK_BUFFER_BASE:04X}\n",
        f"W3D_SHELL_COMPOSITE_BUFFER_BASE: equ ${SHELL_COMPOSITE_BUFFER_BASE:04X}\n\n",
    ]
    for entry in entries:
        origin = (
            f"WL1 v1.4 chunk {entry.chunkId}"
            if entry.chunkId is not None
            else "composed from WL1 v1.4 resources"
        )
        prefix = f"W3D_SHELL_{entry.name.upper()}"
        lines.extend(
            (
                f"{prefix}_BUFFER: equ ${entry.bufferId:04X} ; {origin}\n",
                f"{prefix}_WIDTH: equ {entry.width}\n",
                f"{prefix}_HEIGHT: equ {entry.height}\n",
                f"{prefix}_X: equ {entry.plotX}\n",
                f"{prefix}_Y: equ {entry.plotY}\n",
            )
        )
    path.write_text("".join(lines))


def _stage_image(
    *,
    name: str,
    image: Image.Image,
    source: str,
    chunk_id: int | None,
    buffer_id: int,
    plot_x: int,
    plot_y: int,
    original_dir: Path,
    processed_dir: Path,
    palette_file: Path,
) -> tuple[ShellManifestEntry, BufferRecord]:
    source_png = original_dir / f"{name}.png"
    processed_png = processed_dir / f"{name}.png"
    rgba2_file = processed_dir / f"{name}.rgba2"
    image.convert("RGB").save(source_png, "PNG")
    _convert(source_png, processed_png, rgba2_file, palette_file)
    pixels = rgba2_file.read_bytes()
    width, height = image.size
    if len(pixels) != width * height:
        raise ValueError(f"Converted shell asset {name} has invalid byte count")
    entry = ShellManifestEntry(
        name=name,
        source=source,
        chunkId=chunk_id,
        bufferId=buffer_id,
        width=width,
        height=height,
        plotX=plot_x,
        plotY=plot_y,
        format=IMAGE_FORMAT_RGBA2222,
        png=f"processed/{name}.png",
        rgba2=f"processed/{name}.rgba2",
        dataSize=len(pixels),
    )
    return entry, BufferRecord(
        name=name,
        bufferId=buffer_id,
        width=width,
        height=height,
        rgba2File=rgba2_file,
        dataSize=len(pixels),
    )


def build_shell_assets(
    data_dir: Path,
    out_dir: Path,
    palette_file: Path,
    override_dir: Path | None = DEFAULT_OVERRIDE_DIR,
) -> list[ShellManifestEntry]:
    archive = read_vgagraph(
        data_dir / "VGADICT.WL1",
        data_dir / "VGAHEAD.WL1",
        data_dir / "VGAGRAPH.WL1",
    )
    font = decode_wolf_font(archive)
    original_dir = out_dir / "orig"
    processed_dir = out_dir / "processed"
    for generated_dir in (original_dir, processed_dir):
        if generated_dir.exists():
            shutil.rmtree(generated_dir)
        generated_dir.mkdir(parents=True)

    raw_images: dict[str, Image.Image] = {}
    raw_sources: dict[str, str] = {}
    for chunk_id in SHELL_CHUNKS:
        name = SHELL_CHUNK_NAMES[chunk_id]
        expected = SHELL_EXPECTED_DIMENSIONS[chunk_id]
        image = archive.decode_picture(chunk_id).convert("RGB")
        if image.size != expected:
            raise ValueError(
                f"WL1 shell chunk {chunk_id} is {image.size}, expected {expected}"
            )
        source = f"VGAGRAPH.WL1 chunk {chunk_id}"
        override = override_dir / f"{name}.png" if override_dir else None
        if override and override.is_file():
            with Image.open(override) as value:
                replacement = value.convert("RGB")
            if replacement.size != expected:
                raise ValueError(
                    f"Shell override {override} is {replacement.size}, "
                    f"expected {expected}"
                )
            image = replacement
            source = f"hand-edited override: {override}"
        raw_images[name] = image
        raw_sources[name] = source

    entries: list[ShellManifestEntry] = []
    records: list[BufferRecord] = []
    for chunk_id in SHELL_CHUNKS:
        name = SHELL_CHUNK_NAMES[chunk_id]
        entry, record = _stage_image(
            name=name,
            image=raw_images[name],
            source=raw_sources[name],
            chunk_id=chunk_id,
            buffer_id=chunk_buffer_id(chunk_id),
            plot_x=0,
            plot_y=0,
            original_dir=original_dir,
            processed_dir=processed_dir,
            palette_file=palette_file,
        )
        entries.append(entry)
        records.append(record)

    for name, composed in _compose_images(raw_images, font).items():
        entry, record = _stage_image(
            name=name,
            image=composed.image,
            source="composed from original WL1 v1.4 control-panel resources",
            chunk_id=None,
            buffer_id=SHELL_COMPOSITE_BUFFER_IDS[name],
            plot_x=composed.plot_x,
            plot_y=composed.plot_y,
            original_dir=original_dir,
            processed_dir=processed_dir,
            palette_file=palette_file,
        )
        entries.append(entry)
        records.append(record)

    (out_dir / "shell_assets.jsonl").write_text(
        "".join(json.dumps(asdict(entry), sort_keys=True) + "\n" for entry in entries)
    )
    (out_dir / "shell.agnb").write_bytes(build_container(records))
    _write_constants(out_dir / "wolf3d_shell_assets.inc", entries)
    return entries


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--palette", type=Path, default=DEFAULT_PALETTE_FILE)
    parser.add_argument("--override-dir", type=Path, default=DEFAULT_OVERRIDE_DIR)
    args = parser.parse_args()
    entries = build_shell_assets(
        args.data_dir, args.out_dir, args.palette, args.override_dir
    )
    originals = sum(entry.chunkId is not None for entry in entries)
    composites = len(entries) - originals
    print(
        f"Wrote {args.out_dir / 'shell.agnb'}: {originals} original and "
        f"{composites} composed shell images, "
        f"{sum(entry.dataSize for entry in entries)} RGBA2222 bytes"
    )


if __name__ == "__main__":
    main()
