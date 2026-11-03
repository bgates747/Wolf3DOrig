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
from formats.article import (  # noqa: E402
    ARTICLE_BUFFER_BASE,
    ARTICLE_CHUNK,
    ARTICLE_PAGE_COUNT,
    render_help_article,
)
from formats.palette import WOLF3D_PALETTE_RGB888  # noqa: E402
from formats.shell import (  # noqa: E402
    BKGDCOLOR,
    BORD2COLOR,
    BORDCOLOR,
    COMPOSED_DEACTIVE_RGB,
    CONTROL_PAGE_LINES,
    CURRENT_GAME_MESSAGE,
    CHANGE_VIEW_PAGE_LINES,
    DEACTIVE,
    DIFFICULTY_LABELS,
    DIFFICULTY_NAMES,
    END_GAME_MESSAGE,
    EPISODE_LABELS,
    EPISODE_UNAVAILABLE_MESSAGE,
    HIGHLIGHT,
    MAIN_LABELS,
    ORDER_HIGHLIGHT,
    ORDER_NORMAL,
    QUIT_MESSAGES,
    READHCOLOR,
    READ_THIS_PAGE_LINES,
    SAVING_MESSAGE,
    SHELL_CHUNKS,
    SHELL_CHUNK_BUFFER_BASE,
    SHELL_CHUNK_NAMES,
    SHELL_CHUNK_POSITIONS,
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
        # Save Game alone requires an active game. Back to Demo now returns
        # to the source-timed title/credits/high-score attract cycle.
        color = TEXTCOLOR if index != 4 else COMPOSED_DEACTIVE_RGB
        _draw_text(image, font, (100, 55 + index * 13), label, color)
    return image


def _compose_information_page(
    raw: dict[str, Image.Image],
    font: WolfFont,
    title: str,
    lines: tuple[str, ...],
) -> Image.Image:
    """Build one source-styled control-panel information page."""

    image = Image.new("RGB", SCREEN_SIZE, _color(BORDCOLOR))
    image.paste(raw["mouse_back"], (112, 184))
    _draw_stripes(image)
    _draw_centered(image, font, 15, title, READHCOLOR)
    _draw_window(image, 20, 45, 280, 133, BKGDCOLOR)
    y = 52
    for line in lines:
        if line:
            _draw_centered(image, font, y, line, TEXTCOLOR)
        y += font.height
    return image


def _compose_sound_page(
    raw: dict[str, Image.Image], font: WolfFont, sfx_enabled: bool,
    music_enabled: bool,
) -> Image.Image:
    sfx_state = "ON" if sfx_enabled else "OFF"
    music_state = "ON" if music_enabled else "OFF"
    return _compose_information_page(
        raw,
        font,
        "Sound",
        (
            f"Sound effects       {sfx_state}",
            "",
            f"Music               {music_state}",
            "",
            "Up/Down selects.",
            "Enter toggles.",
            "Escape returns.",
        ),
    )


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


def _compose_high_scores(
    raw: dict[str, Image.Image], font: WolfFont
) -> Image.Image:
    """Reproduce the invariant shareware ``DrawHighScores`` backdrop.

    The bundled UPLOAD archive retains HIGHSCORESPIC but omits the separate
    C_NAME/C_LEVEL/C_SCORE pictures used by registered builds.  Their visible
    labels are reconstructed with the same original proportional font.
    """

    image = Image.new("RGB", SCREEN_SIZE, _color(BORDCOLOR))
    _draw_stripes(image)
    image.paste(raw["high_scores_heading"], (48, 0))
    _draw_text(image, font, (4 * 8, 68), "Name", 15)
    _draw_text(image, font, (20 * 8, 68), "Level", 15)
    _draw_text(image, font, (28 * 8, 68), "Score", 15)
    return image


def _compose_ingame_tail(font: WolfFont) -> Image.Image:
    """Original in-game control-panel tail: End/Back to Game/Quit."""

    image = Image.new("RGB", (145, 44), _color(BKGDCOLOR))
    _draw_text(image, font, (4, 3), "End Game", TEXTCOLOR)
    _draw_text(image, font, (4, 16), "Back to Game", TEXTCOLOR)
    _draw_text(image, font, (4, 29), "Quit", TEXTCOLOR)
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


def _compose_end_game_notice(font: WolfFont) -> Image.Image:
    """Reproduce ``Message(ENDGAMESTR)`` from the shareware control panel."""

    text_width, text_height = font.measure(END_GAME_MESSAGE)
    if (text_width, text_height) != (204, 39):
        raise ValueError(
            "Unexpected ENDGAMESTR metrics: "
            f"{text_width}x{text_height}, expected 204x39"
        )

    # Message() centers mw=204 and h=39, then DrawWindow uses mw+10 by h+10.
    # DrawOutline's inclusive right/bottom edges make the stored crop 215x50.
    image = Image.new("RGB", (215, 50), _color(TEXTCOLOR))
    _draw_window(image, 0, 0, 214, 49, TEXTCOLOR)
    _draw_outline(image, 0, 0, 214, 49, 0, HIGHLIGHT)
    _draw_text(image, font, (5, 5), END_GAME_MESSAGE, 0)
    return image


def _compose_message_notice(font: WolfFont, text: str) -> ComposedImage:
    """Reproduce WL_MENU.C Message(), centered in its normal 320x200 window."""

    height = font.height
    width = 0
    message_width = 0
    for character in text:
        if character == "\n":
            message_width = max(message_width, width)
            width = 0
            height += font.height
        else:
            width += font.glyph_width(character)
    message_width = max(message_width, width + 10)

    # DrawWindow/DrawOutline include the right and bottom coordinates.
    image = Image.new(
        "RGB", (message_width + 11, height + 11), _color(TEXTCOLOR)
    )
    _draw_window(image, 0, 0, message_width + 10, height + 10, TEXTCOLOR)
    _draw_outline(image, 0, 0, message_width + 10, height + 10, 0, HIGHLIGHT)
    _draw_text(image, font, (5, 5), text, 0)
    return ComposedImage(
        image,
        160 - message_width // 2 - 5,
        100 - height // 2 - 5,
    )


def _compose_quick_load_notice() -> ComposedImage:
    """Blank source-style window for the runtime save-name confirmation."""

    # Save names are mutable, so the eZ80 prints the two source text lines
    # with the same honest text renderer used by the ten-slot panel. Keep the
    # surrounding Message()/DrawOutline treatment as a reusable bitmap.
    image = Image.new("RGB", (284, 37), _color(TEXTCOLOR))
    _draw_window(image, 0, 0, 283, 36, TEXTCOLOR)
    _draw_outline(image, 0, 0, 283, 36, 0, HIGHLIGHT)
    return ComposedImage(image, 19, 82)


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
        "high_scores_base": ComposedImage(_compose_high_scores(raw, font), 0, 0),
        "main_ingame_tail": ComposedImage(_compose_ingame_tail(font), 96, 143),
        "end_game_notice": ComposedImage(_compose_end_game_notice(font), 53, 76),
        "main_save_game_active": ComposedImage(
            _text_overlay(font, MAIN_LABELS[4], TEXTCOLOR), 100, 107
        ),
        "main_new_game_selected": ComposedImage(
            _text_overlay(font, MAIN_LABELS[0], HIGHLIGHT), 100, 55
        ),
        "main_quit_selected": ComposedImage(
            _text_overlay(font, MAIN_LABELS[9], HIGHLIGHT), 100, 172
        ),
        "main_view_scores_selected": ComposedImage(
            _text_overlay(font, MAIN_LABELS[7], HIGHLIGHT), 100, 146
        ),
        "main_end_game_selected": ComposedImage(
            _text_overlay(font, "End Game", HIGHLIGHT), 100, 146
        ),
        "main_back_to_game_selected": ComposedImage(
            _text_overlay(font, "Back to Game", HIGHLIGHT), 100, 159
        ),
        "main_load_game_selected": ComposedImage(
            _text_overlay(font, MAIN_LABELS[3], HIGHLIGHT), 100, 94
        ),
        "main_save_game_selected": ComposedImage(
            _text_overlay(font, MAIN_LABELS[4], HIGHLIGHT), 100, 107
        ),
        "main_sound_selected": ComposedImage(
            _text_overlay(font, MAIN_LABELS[1], HIGHLIGHT), 100, 68
        ),
        "main_control_selected": ComposedImage(
            _text_overlay(font, MAIN_LABELS[2], HIGHLIGHT), 100, 81
        ),
        "main_change_view_selected": ComposedImage(
            _text_overlay(font, MAIN_LABELS[5], HIGHLIGHT), 100, 120
        ),
        "main_read_this_selected": ComposedImage(
            _text_overlay(font, MAIN_LABELS[6], HIGHLIGHT), 100, 133
        ),
        "main_back_to_demo_selected": ComposedImage(
            _text_overlay(font, MAIN_LABELS[8], HIGHLIGHT), 100, 159
        ),
        "sound_on_page": ComposedImage(
            _compose_sound_page(raw, font, True, True), 0, 0
        ),
        "sound_off_page": ComposedImage(
            _compose_sound_page(raw, font, False, True), 0, 0
        ),
        "sound_on_music_off_page": ComposedImage(
            _compose_sound_page(raw, font, True, False), 0, 0
        ),
        "sound_off_music_off_page": ComposedImage(
            _compose_sound_page(raw, font, False, False), 0, 0
        ),
        "control_page": ComposedImage(
            _compose_information_page(raw, font, "Control", CONTROL_PAGE_LINES),
            0,
            0,
        ),
        "change_view_page": ComposedImage(
            _compose_information_page(
                raw, font, "Change View", CHANGE_VIEW_PAGE_LINES
            ),
            0,
            0,
        ),
        "read_this_page": ComposedImage(
            _compose_information_page(raw, font, "Read This!", READ_THIS_PAGE_LINES),
            0,
            0,
        ),
        **{
            f"quit_notice_{index}": _compose_message_notice(font, message)
            for index, message in enumerate(QUIT_MESSAGES)
        },
        "current_game_notice": _compose_message_notice(
            font, CURRENT_GAME_MESSAGE
        ),
        "saving_notice": _compose_message_notice(font, SAVING_MESSAGE),
        "quick_load_notice": _compose_quick_load_notice(),
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
        f"W3D_HELP_PAGE_BUFFER_BASE: equ ${ARTICLE_BUFFER_BASE:04X}\n",
        f"W3D_HELP_PAGE_COUNT: equ {ARTICLE_PAGE_COUNT}\n\n",
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
        plot_x, plot_y = SHELL_CHUNK_POSITIONS.get(chunk_id, (0, 0))
        entry, record = _stage_image(
            name=name,
            image=raw_images[name],
            source=raw_sources[name],
            chunk_id=chunk_id,
            buffer_id=chunk_buffer_id(chunk_id),
            plot_x=plot_x,
            plot_y=plot_y,
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

    article_font = decode_wolf_font(archive, 1)
    help_entries: list[ShellManifestEntry] = []
    help_records: list[BufferRecord] = []
    for index, image in enumerate(render_help_article(archive, article_font)):
        name = f"help_page_{index + 1:02d}"
        entry, record = _stage_image(
            name=name,
            image=image,
            source=f"rendered from VGAGRAPH.WL1 HELP article chunk {ARTICLE_CHUNK}",
            chunk_id=ARTICLE_CHUNK,
            buffer_id=ARTICLE_BUFFER_BASE + index,
            plot_x=0,
            plot_y=0,
            original_dir=original_dir,
            processed_dir=processed_dir,
            palette_file=palette_file,
        )
        help_entries.append(entry)
        help_records.append(record)

    (out_dir / "shell_assets.jsonl").write_text(
        "".join(json.dumps(asdict(entry), sort_keys=True) + "\n" for entry in entries)
    )
    (out_dir / "shell.agnb").write_bytes(build_container(records))
    (out_dir / "help_assets.jsonl").write_text(
        "".join(
            json.dumps(asdict(entry), sort_keys=True) + "\n"
            for entry in help_entries
        )
    )
    (out_dir / "help.agnb").write_bytes(build_container(help_records))
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
    print(
        f"Wrote {args.out_dir / 'help.agnb'}: {ARTICLE_PAGE_COUNT} original "
        f"HELP article pages, {ARTICLE_PAGE_COUNT * 320 * 200} RGBA2222 bytes"
    )


if __name__ == "__main__":
    main()
