"""Stable v1.4 WL1 application-shell picture and buffer contract."""

from __future__ import annotations

SHELL_CHUNK_BUFFER_BASE = 0x4200

# Grounded in the bundled v1.4 archive's STRUCTPIC table and visual audit.
SHELL_CHUNK_NAMES = {
    21: "menu_backdrop",
    22: "options_heading",
    23: "cursor_1",
    24: "cursor_2",
    30: "mouse_back",
    31: "difficulty_baby",
    32: "difficulty_easy",
    33: "difficulty_normal",
    34: "difficulty_hard",
    42: "episode_1",
    43: "episode_2",
    44: "episode_3",
    45: "episode_4",
    46: "episode_5",
    47: "episode_6",
    99: "title",
}

SHELL_EXPECTED_DIMENSIONS = {
    21: (256, 144),
    22: (152, 48),
    23: (24, 16),
    24: (24, 16),
    30: (104, 16),
    **{chunk_id: (24, 32) for chunk_id in range(31, 35)},
    **{chunk_id: (48, 24) for chunk_id in range(42, 48)},
    99: (320, 200),
}

SHELL_CHUNKS = tuple(SHELL_CHUNK_NAMES)


def chunk_buffer_id(chunk_id: int) -> int:
    if chunk_id not in SHELL_CHUNK_NAMES:
        raise ValueError(f"Chunk {chunk_id} is not in the staged shell set")
    return SHELL_CHUNK_BUFFER_BASE + chunk_id


assert set(SHELL_CHUNK_NAMES) == set(SHELL_EXPECTED_DIMENSIONS)
