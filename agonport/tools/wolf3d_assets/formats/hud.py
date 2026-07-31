"""Stable chunk and VDP buffer contracts for the original WL1 HUD art."""

from __future__ import annotations

HUD_CHUNK_BUFFER_BASE = 0x4000
STATUSBAR_CHUNK = 98
HUD_WIDGET_CHUNKS = tuple(range(103, 145))
HUD_CHUNKS = (STATUSBAR_CHUNK, *HUD_WIDGET_CHUNKS)

HUD_EXPECTED_DIMENSIONS = {
    STATUSBAR_CHUNK: (320, 40),
    **{chunk_id: (48, 24) for chunk_id in range(103, 107)},
    **{chunk_id: (8, 16) for chunk_id in range(107, 121)},
    **{chunk_id: (24, 32) for chunk_id in range(121, 145)},
}


def chunk_buffer_id(chunk_id: int) -> int:
    if chunk_id not in HUD_CHUNKS:
        raise ValueError(f"Chunk {chunk_id} is not in the staged HUD set")
    return HUD_CHUNK_BUFFER_BASE + chunk_id


# The sequence is grounded in the original graphics-enum ordering and the
# dimensions in this exact VGA archive.  The container and VDP contract still
# keys assets by chunk id; these names exist for readable generated output.
HUD_CHUNK_NAMES = {
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
