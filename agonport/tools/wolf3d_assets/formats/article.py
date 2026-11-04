"""Render original WL1 ``ShowArticle`` markup into indexed pages.

This is a deliberately literal offline translation of ``WL_TEXT.C``.  The
Agon client can therefore display the complete shareware HELP and ENDART1
articles with a single bitmap plot per page instead of reimplementing
proportional layout in the eZ80 menu loop.
"""

from __future__ import annotations

from dataclasses import dataclass

from PIL import Image, ImageDraw

from .palette import WOLF3D_PALETTE_RGB888
from .shell import WolfFont
from .vgagraph import VgaGraph


HELP_ARTICLE_CHUNK = 150
HELP_ARTICLE_PAGE_COUNT = 41
HELP_ARTICLE_BUFFER_BASE = 0x4600
END_ARTICLE_CHUNK = 155
END_ARTICLE_PAGE_COUNT = 2
END_ARTICLE_BUFFER_BASE = 0x4629

# Backward-compatible names retained for the existing HELP callers.
ARTICLE_CHUNK = HELP_ARTICLE_CHUNK
ARTICLE_PAGE_COUNT = HELP_ARTICLE_PAGE_COUNT
ARTICLE_BUFFER_BASE = HELP_ARTICLE_BUFFER_BASE
BACKCOLOR = 0x11
FONTHEIGHT = 10
TOPMARGIN = 16
BOTTOMMARGIN = 32
LEFTMARGIN = 16
RIGHTMARGIN = 16
PICMARGIN = 8
TEXTROWS = (200 - TOPMARGIN - BOTTOMMARGIN) // FONTHEIGHT
SPACEWIDTH = 7
SCREENPIXWIDTH = 320
SCREENMID = SCREENPIXWIDTH // 2
FRAME_PICTURES = ((17, 0, 0), (18, 0, 8), (19, 312, 8), (20, 8, 176))


@dataclass
class _Layout:
    page: Image.Image
    text: str
    position: int
    font: WolfFont
    archive: VgaGraph
    color: int = 0
    x: int = LEFTMARGIN
    y: int = TOPMARGIN
    row: int = 0
    overflowed: bool = False

    def __post_init__(self) -> None:
        self.left = [LEFTMARGIN] * TEXTROWS
        self.right = [SCREENPIXWIDTH - RIGHTMARGIN] * TEXTROWS

    def newline(self) -> None:
        self.row += 1
        if self.row >= TEXTROWS:
            while self.position < len(self.text):
                if (
                    self.text[self.position] == "^"
                    and self.text[self.position + 1].upper() in ("P", "E")
                ):
                    self.overflowed = True
                    return
                self.position += 1
            raise ValueError("article overflow lacks a following page break")
        self.x = self.left[self.row]
        self.y += FONTHEIGHT

    def draw_text(self, value: str, x: int | None = None, y: int | None = None,
                  color: int | None = None) -> None:
        px = self.x if x is None else x
        py = self.y if y is None else y
        ink = self.color if color is None else color
        pixels = self.page.load()
        for character in value:
            width, height, mask = self.font.glyph_mask(character)
            for glyph_y in range(height):
                offset = glyph_y * width
                for glyph_x in range(width):
                    if mask[offset + glyph_x]:
                        pixels[px + glyph_x, py + glyph_y] = ink
            px += width

    def word(self) -> None:
        start = self.position
        self.position += 1
        while self.position < len(self.text) and ord(self.text[self.position]) > 32:
            self.position += 1
        value = self.text[start:self.position]
        width = self.font.measure_line(value)
        while self.x + width > self.right[self.row]:
            self.newline()
            if self.overflowed:
                return
        self.draw_text(value)
        self.x += width
        while self.position < len(self.text) and self.text[self.position] == " ":
            self.x += SPACEWIDTH
            self.position += 1

    def number(self) -> int:
        while self.position < len(self.text) and not self.text[self.position].isdigit():
            self.position += 1
        start = self.position
        while self.position < len(self.text) and self.text[self.position].isdigit():
            self.position += 1
        if start == self.position:
            raise ValueError("article command lacks a number")
        return int(self.text[start:self.position])

    def end_of_line(self) -> None:
        newline = self.text.find("\n", self.position)
        if newline < 0:
            raise ValueError("unterminated article command")
        self.position = newline + 1

    def command(self) -> bool:
        self.position += 1
        command = self.text[self.position].upper()
        self.position += 1
        if command in ("P", "E"):
            self.position -= 2
            return True
        if command == ";":
            self.end_of_line()
        elif command == "C":
            self.color = int(self.text[self.position:self.position + 2], 16)
            self.position += 2
        elif command == ">":
            self.x = SCREENMID
        elif command == "L":
            source_y = self.number()
            self.row = (source_y - TOPMARGIN) // FONTHEIGHT
            self.y = TOPMARGIN + self.row * FONTHEIGHT
            self.x = self.number()
            self.end_of_line()
        elif command == "B":
            y = self.number()
            x = self.number()
            width = self.number()
            height = self.number()
            ImageDraw.Draw(self.page).rectangle(
                (x, y, x + width - 1, y + height - 1), fill=BACKCOLOR
            )
            self.end_of_line()
        elif command in ("G", "T"):
            y = self.number()
            x = self.number()
            picture = self.number()
            if command == "T":
                self.number()  # source delay; irrelevant to a precomposed page
            self.end_of_line()
            image = self.archive.decode_picture(picture)
            self.page.paste(image, (x & ~7, y))
            width, height = image.size
            middle = x + width // 2
            margin = x - PICMARGIN if middle > SCREENMID else x + width + PICMARGIN
            top = max(0, (y - TOPMARGIN) // FONTHEIGHT)
            bottom = min(TEXTROWS - 1, (y + height - TOPMARGIN) // FONTHEIGHT)
            for row in range(top, bottom + 1):
                if middle > SCREENMID:
                    self.right[row] = margin
                else:
                    self.left[row] = margin
            if self.x < self.left[self.row]:
                self.x = self.left[self.row]
        else:
            raise ValueError(f"unsupported article command ^{command}")
        return False


def _new_page(archive: VgaGraph) -> Image.Image:
    page = Image.new("P", (320, 200), BACKCOLOR)
    page.putpalette(
        [channel for color in WOLF3D_PALETTE_RGB888 for channel in color]
    )
    for chunk, x, y in FRAME_PICTURES:
        page.paste(archive.decode_picture(chunk), (x, y))
    return page


def render_article(
    archive: VgaGraph,
    font: WolfFont,
    *,
    chunk: int,
    page_count: int,
) -> tuple[Image.Image, ...]:
    """Render one source article and require its canonical page count."""

    text = archive.expand_chunk(chunk).decode("ascii")
    position = 0
    pages: list[Image.Image] = []
    while True:
        while position < len(text) and ord(text[position]) <= 32:
            position += 1
        if text[position:position + 2].upper() == "^E":
            break
        if text[position:position + 2].upper() != "^P":
            raise ValueError(f"article chunk {chunk} page does not begin with ^P")
        newline = text.find("\n", position)
        if newline < 0:
            raise ValueError("unterminated article page header")
        layout = _Layout(_new_page(archive), text, newline + 1, font, archive)
        done = False
        while not done:
            character = text[layout.position]
            if character == "^":
                done = layout.command()
            elif character == "\t":
                layout.x = (layout.x + 8) & ~7
                layout.position += 1
            elif ord(character) <= 32:
                layout.position += 1
                if character == "\n":
                    layout.newline()
            else:
                layout.word()
            if layout.overflowed:
                done = True
        pages.append(layout.page)
        position = layout.position

    if len(pages) != page_count:
        raise ValueError(
            f"article chunk {chunk} contains {len(pages)} pages, "
            f"expected {page_count}"
        )
    for index, page in enumerate(pages, 1):
        label = f"pg {index} of {len(pages)}"
        layout = _Layout(page, "", 0, font, archive)
        layout.draw_text(label, 213, 183, 0x4F)
    return tuple(pages)


def render_help_article(archive: VgaGraph, font: WolfFont) -> tuple[Image.Image, ...]:
    return render_article(
        archive,
        font,
        chunk=HELP_ARTICLE_CHUNK,
        page_count=HELP_ARTICLE_PAGE_COUNT,
    )


def render_end_article(archive: VgaGraph, font: WolfFont) -> tuple[Image.Image, ...]:
    return render_article(
        archive,
        font,
        chunk=END_ARTICLE_CHUNK,
        page_count=END_ARTICLE_PAGE_COUNT,
    )
