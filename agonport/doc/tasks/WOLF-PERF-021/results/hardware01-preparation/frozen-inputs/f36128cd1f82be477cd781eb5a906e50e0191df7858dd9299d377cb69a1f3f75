#!/usr/bin/env python3
"""Generate the shared Wolf3D production VDPlet wire constants.

The eZ80 assembly and freestanding C++ module must never hand-maintain parallel
numeric contracts. This file is the single source; use --check in regressions
and omit it only when intentionally refreshing both generated consumers.
"""

from __future__ import annotations

import argparse
from pathlib import Path


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
C_HEADER = HERE / "wolf3d_production_contract.h"
ASM_INCLUDE = REPO / "src/asm/wolf3d/src/wolf3d_vdplet_contract.inc"


CONSTANTS: tuple[tuple[str, int, str], ...] = (
    ("W3P_ARGUMENT_MAGIC", 0x41503357, '"W3PA" little-endian'),
    ("W3P_BATCH_MAGIC", 0x55443357, '"W3DU" little-endian'),
    ("W3P_MODULE_ID", 0x31503357, '"W3P1" production renderer identity'),
    ("W3P_MODULE_RELEASE", 0x00010200, "module release 1.2.0"),
    ("W3P_SCHEMA_VERSION", 2, "wire schema, independent of module release"),
    ("W3P_REQUIRED_CAPABILITIES", 0x0101, "buffers plus direct colour rows"),

    ("W3P_ENTRY_CONFIG", 0, "validate resource descriptor"),
    ("W3P_ENTRY_APPLY_AND_RENDER", 1, "atomically update and render"),
    ("W3P_ENTRY_FIZZLE_BEGIN", 2, "begin app-paced fizzle"),
    ("W3P_ENTRY_FIZZLE_STEP", 3, "advance app-paced fizzle"),
    ("W3P_ENTRY_RESET", 4, "discard configured mirror"),
    ("W3P_ENTRY_SELFTEST", 5, "optional deterministic self-test"),

    ("W3P_ARGUMENT_BYTES", 24, "exact CONFIG and RUN descriptor size"),
    ("W3P_ARG_MAGIC", 0, "u32"),
    ("W3P_ARG_SCHEMA", 4, "u8"),
    ("W3P_ARG_BYTES", 5, "u8"),
    ("W3P_ARG_FLAGS", 6, "u16"),
    ("W3P_ARG_WORKSPACE", 8, "u16 buffer id"),
    ("W3P_ARG_UPDATE", 10, "u16 buffer id"),
    ("W3P_ARG_TILEMAP", 12, "u16 initial tilemap buffer id"),
    ("W3P_ARG_WALL_BASE", 14, "u16 wall texture base"),
    ("W3P_ARG_SPRITE_BASE", 16, "u16 sprite texture base"),
    ("W3P_ARG_HUD_BASE", 18, "u16 HUD chunk base"),
    ("W3P_ARG_GENERATION_SEED", 20, "u16; first batch is seed+1"),
    ("W3P_ARG_RESERVED", 22, "u16 zero"),
    ("W3P_ARG_FLAG_COPIED_PIXELS", 0x0001, "RGB222 workspace publication"),
    ("W3P_ARG_FLAG_DIRECT_ROWS", 0x0002, "native hidden-framebuffer rows"),
    ("W3P_ARG_KNOWN_FLAGS", 0x0003, "all schema-2 descriptor flags"),

    ("W3P_DEFAULT_WALL_BASE", 0x1000, "resident wall texture buffers"),
    ("W3P_DEFAULT_SPRITE_BASE", 0x2000, "resident sprite texture buffers"),
    ("W3P_DEFAULT_HUD_BASE", 0x4000, "resident HUD chunk buffers"),
    ("W3P_SCREEN_WIDTH", 320, "RGB222 frame width"),
    ("W3P_SCREEN_HEIGHT", 240, "RGB222 frame height"),
    ("W3P_VIEW_X", 32, "physical viewport left"),
    ("W3P_VIEW_Y", 20, "physical viewport top"),
    ("W3P_VIEW_WIDTH", 256, "death-fizzle viewport width"),
    ("W3P_VIEW_HEIGHT", 160, "death-fizzle viewport height"),
    ("W3P_FIZZLE_DISPLAY_FRAMES", 60,
     "one second of app-paced 60 Hz presentation"),
    ("W3P_FIZZLE_RED", 2, "RGB222(2,0,0), Wolf palette index 4"),
    ("W3P_FRAME_BYTES", 76800, "320*240"),
    ("W3P_WALL_HEIGHT_OFFSET", 76800, "256 signed 32-bit heights"),
    ("W3P_WALL_HEIGHT_BYTES", 1024, "wall-height scratch"),
    ("W3P_WALL_TILE_OFFSET", 77824, "256 wall ids"),
    ("W3P_WALL_TEXU_OFFSET", 78080, "256 texture columns"),
    ("W3P_WALL_SIDE_OFFSET", 78336, "256 side flags"),
    ("W3P_SPRITE_ARENA_OFFSET", 78592, "sprite sort/scale scratch"),
    ("W3P_SPRITE_ARENA_BYTES", 8800, "bounded sprite scratch"),
    ("W3P_WORKSPACE_BYTES", 92160, "first copied-pixel production target"),
    ("W3P_DIRECT_TARGET_WORKSPACE_BYTES", 11552,
     "32-bit target row pointers plus render scratch"),

    ("W3P_BATCH_HEADER_BYTES", 16, "exact update header size"),
    ("W3P_BATCH_MAGIC_OFFSET", 0, "u32"),
    ("W3P_BATCH_SCHEMA_OFFSET", 4, "u8"),
    ("W3P_BATCH_HEADER_OFFSET", 5, "u8"),
    ("W3P_BATCH_FLAGS_OFFSET", 6, "u16"),
    ("W3P_BATCH_TOTAL_OFFSET", 8, "u16 exact consolidated bytes"),
    ("W3P_BATCH_RECORDS_OFFSET", 10, "u16"),
    ("W3P_BATCH_GENERATION_OFFSET", 12, "u16 nonzero monotonic"),
    ("W3P_BATCH_RESERVED_OFFSET", 14, "u16 zero"),
    ("W3P_BATCH_FLAG_FULL", 0x0001, "complete level snapshot"),
    ("W3P_BATCH_KNOWN_FLAGS", 0x0001, "all schema-2 batch flags"),
    ("W3P_BATCH_MAX_BYTES", 7168, "worst full snapshot plus headroom"),
    ("W3P_BATCH_MAX_RECORDS", 618,
     "1 level + player + pushwall + maxima + HUD/weapon"),
    ("W3P_RECORD_HEADER_BYTES", 2, "type:u8,payload_bytes:u8"),

    ("W3P_RECORD_LEVEL", 1, "full snapshot level binding"),
    ("W3P_RECORD_PLAYER", 2, "player pose"),
    ("W3P_RECORD_DOOR", 3, "door slot"),
    ("W3P_RECORD_ACTOR_SET", 4, "actor slot value"),
    ("W3P_RECORD_ACTOR_REMOVE", 5, "actor slot removal"),
    ("W3P_RECORD_STATIC", 6, "static slot value/removal"),
    ("W3P_RECORD_HUD", 7, "complete persistent HUD state"),
    ("W3P_RECORD_VIEW_WEAPON", 8, "first-person overlay shape"),
    ("W3P_RECORD_PUSHWALL", 9, "complete live/completed pushwall state"),

    ("W3P_LEVEL_BYTES", 6, "tilemap:u16,doors:u8,statics:u16,reserved:u8"),
    ("W3P_PLAYER_BYTES", 10, "x:i32,y:i32,angle:u16"),
    ("W3P_DOOR_BYTES", 9, "id:u8 plus existing 8-byte door wire"),
    ("W3P_ACTOR_SET_BYTES", 15, "existing actor wire record"),
    ("W3P_ACTOR_REMOVE_BYTES", 2, "actor id:u16"),
    ("W3P_STATIC_BYTES", 7, "id:u16 plus existing 5-byte static wire"),
    ("W3P_HUD_BYTES", 12, "complete HUD value record"),
    ("W3P_HUD_FACE_OFFSET", 9, "ordinary 0..2 or GOTGATLINGPIC sentinel 3"),
    ("W3P_HUD_PALETTE_OFFSET", 11, "transient palette-shift wire byte"),
    ("W3P_HUD_PALETTE_WHITE_FLAG", 0x80, "white bonus-shift selector"),
    ("W3P_HUD_PALETTE_RED_MAX", 6, "original NUMREDSHIFTS"),
    ("W3P_HUD_PALETTE_WHITE_MAX", 3, "original NUMWHITESHIFTS"),
    ("W3P_VIEW_WEAPON_BYTES", 2, "shape:i16"),
    ("W3P_PUSHWALL_BYTES", 89, "live:8,count:u8,16 completed entries"),
    ("W3P_PUSHWALL_STATUS", 0, "live status byte"),
    ("W3P_PUSHWALL_ORIGIN_X", 1, "live origin x"),
    ("W3P_PUSHWALL_ORIGIN_Y", 2, "live origin y"),
    ("W3P_PUSHWALL_CURRENT_X", 3, "live current x"),
    ("W3P_PUSHWALL_CURRENT_Y", 4, "live current y"),
    ("W3P_PUSHWALL_DIRECTION", 5, "live cardinal direction"),
    ("W3P_PUSHWALL_POSITION", 6, "live fractional position 0..63"),
    ("W3P_PUSHWALL_TEXTURE", 7, "live wall texture 1..63"),
    ("W3P_PUSHWALL_COMPLETED_COUNT", 8, "completed overlay count"),
    ("W3P_PUSHWALL_COMPLETED_OFFSET", 9, "first completed overlay"),
    ("W3P_PUSHWALL_COMPLETED_BYTES", 5, "origin x/y,current x/y,texture"),
    ("W3P_MAX_PUSHWALLS", 16, "shareware per-level completion ceiling"),

    ("W3P_MAX_DOORS", 64, "render mirror slots"),
    ("W3P_MAX_ACTORS", 150, "slot zero remains player-owned"),
    ("W3P_MAX_STATICS", 400, "render mirror slots"),
    ("W3P_MAP_SIZE", 64, "64x64 tilemap"),
    ("W3P_MAX_SHAPE", 8191, "sprite buffer formula limit"),
    ("W3P_MAX_WALL_TEXTURE", 127, "one-byte wall id"),
    ("W3P_MIRROR_MAX_BYTES", 5500, "resident compact-mirror ceiling"),

    ("W3P_DETAIL_OK", 0, "accepted"),
    ("W3P_DETAIL_ARGUMENT", 1, "bad magic/version/flag/value"),
    ("W3P_DETAIL_BOUNDS", 2, "bad declared/record length"),
    ("W3P_DETAIL_GENERATION", 3, "stale, skipped, zero or wrapped"),
    ("W3P_DETAIL_DUPLICATE", 4, "duplicate singleton or slot record"),
    ("W3P_DETAIL_INCOMPLETE", 5, "missing full-snapshot coverage"),
    ("W3P_DETAIL_ORDER", 6, "level record not first/full-only"),
    ("W3P_DETAIL_RECORD", 7, "unknown record type"),
)


def c_value(value: int) -> str:
    if value >= 0x1000:
        return f"0x{value:08X}u" if value > 0xFFFF else f"0x{value:04X}u"
    return f"{value}u"


def asm_value(value: int) -> str:
    return f"0x{value:X}" if value >= 10 else str(value)


def render_c() -> str:
    lines = [
        "#ifndef WOLF3D_PRODUCTION_VDPLET_CONTRACT_H",
        "#define WOLF3D_PRODUCTION_VDPLET_CONTRACT_H",
        "",
        "// Generated by production/contract.py. Do not edit by hand.",
        "// Wire values are little-endian and all buffer IDs are uint16.",
        "",
    ]
    width = max(len(name) for name, _, _ in CONSTANTS)
    for name, value, comment in CONSTANTS:
        lines.append(f"#define {name:<{width}} {c_value(value):<12} // {comment}")
    lines.extend(("", "#endif", ""))
    return "\n".join(lines)


def render_asm() -> str:
    lines = [
        "; Generated by agonport/vdplet/production/contract.py.",
        "; Do not edit by hand. Wire values are little-endian.",
        "",
    ]
    width = max(len(name) for name, _, _ in CONSTANTS)
    for name, value, comment in CONSTANTS:
        label = name + ":"
        lines.append(f"{label:<{width + 1}} equ {asm_value(value):<12} ; {comment}")
    lines.append("")
    return "\n".join(lines)


def update(path: Path, expected: str, check: bool) -> bool:
    actual = path.read_text() if path.is_file() else None
    if actual == expected:
        return True
    if check:
        print(f"out of date: {path.relative_to(REPO)}")
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(expected)
    print(f"wrote {path.relative_to(REPO)}")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    okay = update(C_HEADER, render_c(), args.check)
    okay = update(ASM_INCLUDE, render_asm(), args.check) and okay
    if not okay:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
