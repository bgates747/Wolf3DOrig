"""Stable WL1 v1.4 application-shell picture, font, and buffer contract.

The bundled shareware archive does not contain a complete control-panel
backdrop.  Wolfenstein builds those screens from palette-indexed fills,
outlines, its proportional font, and a handful of pictures.  In particular,
chunk 21 is a help-page collage, not menu art, and must never be staged as a
backdrop.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass

from .vgagraph import VgaGraph


SHELL_CHUNK_BUFFER_BASE = 0x4200
SHELL_COMPOSITE_BUFFER_BASE = 0x4300
SHELL_FONT_CHUNK = 2
SHELL_SIGNON_BUFFER_ID = 0x428A
SHELL_SIGNON_SIZE = (320, 200)

# Grounded in the bundled v1.4 archive's STRUCTPIC table and visual audit.
# Chunk 21 is intentionally absent: it is H_GALACTIXPIC/help art in this data.
SHELL_CHUNK_NAMES = {
    22: "options_heading",
    23: "cursor_1",
    24: "cursor_2",
    30: "mouse_back",
    31: "difficulty_baby",
    32: "difficulty_easy",
    33: "difficulty_normal",
    34: "difficulty_hard",
    39: "load_game_heading",
    40: "save_game_heading",
    42: "episode_1",
    43: "episode_2",
    44: "episode_3",
    45: "episode_4",
    46: "episode_5",
    47: "episode_6",
    99: "title",
    100: "pg13",
    101: "credits",
    102: "high_scores_heading",
    137: "paused",
}

SHELL_EXPECTED_DIMENSIONS = {
    22: (152, 48),
    23: (24, 16),
    24: (24, 16),
    30: (104, 16),
    **{chunk_id: (24, 32) for chunk_id in range(31, 35)},
    39: (152, 48),
    40: (216, 48),
    **{chunk_id: (48, 24) for chunk_id in range(42, 48)},
    99: (320, 200),
    100: (88, 64),
    101: (320, 200),
    102: (224, 56),
    137: (24, 32),
}

SHELL_CHUNKS = tuple(SHELL_CHUNK_NAMES)

# Raw pictures default to their caller-selected position. PG13PIC is the one
# startup picture whose original anchor is part of the durable shell contract.
SHELL_CHUNK_POSITIONS = {
    100: (216, 110),
}

# New images generated from the original control-panel drawing contract.
# Deliberate gaps keep related selection overlays contiguous and auditable.
SHELL_COMPOSITE_BUFFER_IDS = {
    "main_base": 0x4300,
    "episode_base": 0x4301,
    "difficulty_base": 0x4302,
    "episode_unavailable_notice": 0x4303,
    "high_scores_base": 0x4304,
    "main_ingame_tail": 0x4305,
    "end_game_notice": 0x4306,
    "main_save_game_active": 0x4307,
    "main_new_game_selected": 0x4310,
    "main_quit_selected": 0x4311,
    "main_view_scores_selected": 0x4312,
    "main_end_game_selected": 0x4313,
    "main_back_to_game_selected": 0x4314,
    "main_load_game_selected": 0x4315,
    "main_save_game_selected": 0x4316,
    "main_sound_selected": 0x4317,
    "main_control_selected": 0x4318,
    "main_change_view_selected": 0x4319,
    "main_read_this_selected": 0x431A,
    "main_back_to_demo_selected": 0x431B,
    **{f"episode_{index}_selected": 0x431F + index for index in range(1, 7)},
    "difficulty_baby_selected": 0x4330,
    "difficulty_easy_selected": 0x4331,
    "difficulty_normal_selected": 0x4332,
    "difficulty_hard_selected": 0x4333,
    "sound_on_page": 0x4340,
    "sound_off_page": 0x4341,
    "control_page": 0x4342,
    "change_view_page": 0x4343,
    "read_this_page": 0x4344,
    "sound_on_music_off_page": 0x4345,
    "sound_off_music_off_page": 0x4346,
    **{f"quit_notice_{index}": 0x4350 + index for index in range(9)},
    "current_game_notice": 0x4359,
    "saving_notice": 0x435A,
    "quick_load_notice": 0x435B,
    "cheater_notice": 0x435C,
    "keen_notice": 0x435D,
}

# Original WL_MENU.H palette indices.
BORDCOLOR = 0x29
BORD2COLOR = 0x23
DEACTIVE = 0x2B
BKGDCOLOR = 0x2D
STRIPE = 0x2C
READCOLOR = 0x4A
READHCOLOR = 0x47
TEXTCOLOR = 0x17
HIGHLIGHT = 0x13
ORDER_NORMAL = 0x6B
ORDER_HIGHLIGHT = 0x67

# DEACTIVE (VGA index $2B) and BKGDCOLOR ($2D) both quantize to Agon64's
# 85-red level.  Composed disabled labels deliberately use the next Agon64
# red level so their original semantic contrast survives conversion.  Raw
# archive pictures remain unmodified.
COMPOSED_DEACTIVE_RGB = (170, 0, 0)

MAIN_LABELS = (
    "New Game",
    "Sound",
    "Control",
    "Load Game",
    "Save Game",
    "Change View",
    "Read This!",
    "View Scores",
    "Back to Demo",
    "Quit",
)

EPISODE_LABELS = (
    "Episode 1\nEscape from Wolfenstein",
    "Episode 2\nOperation: Eisenfaust",
    "Episode 3\nDie, Fuhrer, Die!",
    "Episode 4\nA Dark Secret",
    "Episode 5\nTrail of the Madman",
    "Episode 6\nConfrontation",
)

DIFFICULTY_NAMES = ("baby", "easy", "normal", "hard")
DIFFICULTY_LABELS = (
    "Can I play, Daddy?",
    "Don't hurt me.",
    "Bring 'em on!",
    "I am Death incarnate!",
)

EPISODE_UNAVAILABLE_MESSAGE = (
    'Please select "Read This!"\n'
    "from the Options menu to\n"
    "find out how to order this\n"
    "episode from Apogee."
)

END_GAME_MESSAGE = (
    "Are you sure you want\n"
    "to end the game you\n"
    "are playing? (Y or N):"
)

CURRENT_GAME_MESSAGE = (
    "You are currently in\n"
    "a game. Continuing will\n"
    "erase old game. Ok?"
)

SAVING_MESSAGE = "Saving..."

CHEATER_MESSAGE = (
    "You now have 100% Health,\n"
    "99 Ammo and both Keys!\n\n"
    "Note that you have basically\n"
    "eliminated your chances of\n"
    "getting a high score!"
)

KEEN_MESSAGE = (
    "Commander Keen is also\n"
    "available from Apogee, but\n"
    "then, you already know\n"
    "that - right, Cheatmeister?!"
)

QUIT_MESSAGES = (
    "Dost thou wish to\nleave with such hasty\nabandon?",
    "Chickening out...\nalready?",
    "Press N for more carnage.\nPress Y to be a weenie.",
    "So, you think you can\nquit this easily, huh?",
    "Press N to save the world.\nPress Y to abandon it in\nits hour of need.",
    "Press N if you are brave.\nPress Y to cower in shame.",
    "Heroes, press N.\nWimps, press Y.",
    "You are at an intersection.\nA sign says, 'Press Y to quit.'\n>",
    "For guns and glory, press N.\nFor work and worry, press Y.",
)

CONTROL_PAGE_LINES = (
    "Move forward/back: W / S",
    "Strafe left/right: A / D",
    "Turn: Left / Right arrows",
    "Use or open: Up arrow",
    "Fire: Space",
    "Weapons: 1  2  3  4",
    "Control panel: Escape",
    "Mouse/joystick: unavailable",
)

CHANGE_VIEW_PAGE_LINES = (
    "View size: 256 x 160",
    "Dynamic view sizing is not",
    "available in this port.",
    "",
    "The original aspect ratio is",
    "preserved in the fixed view.",
)

READ_THIS_PAGE_LINES = (
    "W/S move; A/D strafe.",
    "Left/Right arrows turn.",
    "Up arrow opens and uses.",
    "Space fires your weapon.",
    "Keys 1-4 select weapons.",
    "Escape opens this panel.",
    "",
    "Find the exit elevators.",
    "Search for secrets!",
)


def chunk_buffer_id(chunk_id: int) -> int:
    if chunk_id not in SHELL_CHUNK_NAMES:
        raise ValueError(f"Chunk {chunk_id} is not in the staged shell set")
    return SHELL_CHUNK_BUFFER_BASE + chunk_id


@dataclass(frozen=True)
class WolfFont:
    """One decoded ``fontstruct`` from VGAGRAPH.

    Glyph bytes are row-major masks at absolute offsets within ``raw``.  This
    matches ``VWB_DrawPropString``: each nonzero byte receives the caller's
    current VGA palette index.
    """

    chunk_id: int
    height: int
    locations: tuple[int, ...]
    widths: tuple[int, ...]
    raw: bytes

    def glyph_width(self, character: str) -> int:
        code = ord(character)
        if not 0 <= code < 256:
            raise ValueError(f"WL1 font cannot encode {character!r}")
        return self.widths[code]

    def measure_line(self, text: str) -> int:
        if "\n" in text:
            raise ValueError("measure_line does not accept newlines")
        return sum(self.glyph_width(character) for character in text)

    def measure(self, text: str) -> tuple[int, int]:
        lines = text.split("\n")
        return max((self.measure_line(line) for line in lines), default=0), (
            len(lines) * self.height
        )

    def glyph_mask(self, character: str) -> tuple[int, int, bytes]:
        code = ord(character)
        width = self.glyph_width(character)
        location = self.locations[code]
        end = location + width * self.height
        return width, self.height, self.raw[location:end]


def decode_wolf_font(archive: VgaGraph, chunk_id: int = SHELL_FONT_CHUNK) -> WolfFont:
    """Decode and strictly validate one original ``fontstruct`` chunk."""

    raw = archive.expand_chunk(chunk_id)
    header_size = 2 + 256 * 2 + 256
    if len(raw) < header_size:
        raise ValueError(f"WL1 font chunk {chunk_id} is shorter than its header")
    height = struct.unpack_from("<H", raw, 0)[0]
    if not height:
        raise ValueError(f"WL1 font chunk {chunk_id} has zero height")
    locations = tuple(struct.unpack_from("<256H", raw, 2))
    widths = tuple(raw[2 + 256 * 2 : header_size])
    for code, (location, width) in enumerate(zip(locations, widths)):
        if not width:
            continue
        end = location + width * height
        if location < header_size or end > len(raw):
            raise ValueError(
                f"WL1 font chunk {chunk_id} glyph {code} escapes its data: "
                f"{location}..{end} of {len(raw)}"
            )
    return WolfFont(chunk_id, height, locations, widths, raw)


assert set(SHELL_CHUNK_NAMES) == set(SHELL_EXPECTED_DIMENSIONS)
assert len(set(SHELL_COMPOSITE_BUFFER_IDS.values())) == len(SHELL_COMPOSITE_BUFFER_IDS)
assert all(
    value >= SHELL_COMPOSITE_BUFFER_BASE
    for value in SHELL_COMPOSITE_BUFFER_IDS.values()
)
