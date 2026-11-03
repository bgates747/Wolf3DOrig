"""Stable chunk and VDP buffer contracts for WL1 gameplay presentation.

The bundled v1.4 archive's level-complete screen is assembled from pictures;
it is not a whole-screen graphic.  The actual archive mapping below is
grounded in its STRUCTPIC table and decoded pixels rather than either of the
historical generated headers, whose chunk numbering does not match this data.
"""

from __future__ import annotations

HUD_CHUNK_BUFFER_BASE = 0x4000
HUD_COMPOSITE_BUFFER_BASE = 0x4100

LEVEL_END_CHUNKS = tuple(range(55, 98))
STATUSBAR_CHUNK = 98
HUD_WIDGET_CHUNKS = tuple(range(103, 145))
HUD_CHUNKS = (*LEVEL_END_CHUNKS, STATUSBAR_CHUNK, *HUD_WIDGET_CHUNKS)

LEVEL_END_CHUNK_NAMES = {
    55: "level_end_guy_1",
    56: "level_end_colon",
    **{57 + digit: f"level_end_digit_{digit}" for digit in range(10)},
    67: "level_end_percent",
    **{
        68 + index: f"level_end_letter_{character.lower()}"
        for index, character in enumerate("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    },
    94: "level_end_exclamation",
    95: "level_end_apostrophe",
    96: "level_end_guy_2",
    97: "level_end_bj_win",
}

HUD_COMPOSITE_BUFFER_IDS = {
    "floor_complete_base": 0x4100,
    "secret_floor_complete_base": 0x4101,
    "victory_base": 0x4102,
}

HUD_EXPECTED_DIMENSIONS = {
    55: (104, 88),
    56: (8, 16),
    **{chunk_id: (16, 16) for chunk_id in range(57, 94)},
    94: (8, 16),
    95: (8, 16),
    96: (104, 88),
    97: (88, 88),
    STATUSBAR_CHUNK: (320, 40),
    **{chunk_id: (48, 24) for chunk_id in range(103, 107)},
    **{chunk_id: (8, 16) for chunk_id in range(107, 121)},
    **{chunk_id: (24, 32) for chunk_id in range(121, 145)},
}


def chunk_buffer_id(chunk_id: int) -> int:
    if chunk_id not in HUD_CHUNKS:
        raise ValueError(f"Chunk {chunk_id} is not in the staged HUD set")
    return HUD_CHUNK_BUFFER_BASE + chunk_id


# The names and dimensions are grounded in this exact VGA archive.  The
# container and VDP contract still key original assets by chunk id; these
# names exist for readable generated output.
HUD_CHUNK_NAMES = {
    **LEVEL_END_CHUNK_NAMES,
    STATUSBAR_CHUNK: "statusbar",
    103: "weapon_knife",
    104: "weapon_pistol",
    105: "weapon_machinegun",
    106: "weapon_gatling",
    107: "key_none",
    108: "key_gold",
    109: "key_silver",
    110: "digit_blank",
    **{111 + digit: f"digit_{digit}" for digit in range(10)},
    **{
        121 + health_band * 3 + frame: f"face_{health_band + 1}_{'abc'[frame]}"
        for health_band in range(7)
        for frame in range(3)
    },
    142: "face_dead",
    143: "face_got_gatling",
    144: "face_mutant",
}

assert set(HUD_CHUNK_NAMES) == set(HUD_CHUNKS)
assert set(HUD_EXPECTED_DIMENSIONS) == set(HUD_CHUNKS)
assert len(set(HUD_COMPOSITE_BUFFER_IDS.values())) == len(
    HUD_COMPOSITE_BUFFER_IDS
)
assert max(chunk_buffer_id(chunk_id) for chunk_id in HUD_CHUNKS) < (
    HUD_COMPOSITE_BUFFER_BASE
)
assert min(HUD_COMPOSITE_BUFFER_IDS.values()) >= HUD_COMPOSITE_BUFFER_BASE
assert max(HUD_COMPOSITE_BUFFER_IDS.values()) < 0x4200
