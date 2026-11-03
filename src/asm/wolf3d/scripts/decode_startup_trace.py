#!/usr/bin/env python3
"""Decode Wolf3D hardware-startup breadcrumbs from VDP USB serial logs."""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys


BUFFER_RE = re.compile(r"vdu_sys_buffered: buffer (\d+), \d+ streams stored")
STAGES = {
    0x01: "application entry",
    0x02: "original video mode captured",
    0x03: "music initialized",
    0x04: "audio initialized",
    0x05: "configuration initialized",
    0x06: "application body returned",
    0x07: "configuration saved",
    0x08: "audio shutdown complete",
    0x09: "music shutdown complete",
    0x10: "application body entered",
    0x11: "shell asset load beginning",
    0x12: "shell asset load complete",
    0x20: "SFX asset load beginning",
    0x21: "SFX asset load complete",
    0x22: "buffered SFX command installation beginning",
    0x23: "buffered SFX command installation complete",
    0x24: "application shell beginning",
    0x25: "application shell returned",
    0x30: "shell entered",
    0x31: "shell video setup complete",
    0x32: "sign-on visible; waiting for input",
    0x33: "sign-on acknowledged",
    0x34: "intro music started",
    0x35: "PG13 screen visible",
    0x36: "PG13 wait complete",
    0x39: "startup splash sequence complete",
    0x40: "title screen stage entered",
    0x41: "title screen wait complete",
    0x42: "credits screen visible",
    0x43: "credits screen wait complete",
    0x44: "high-score screen visible",
    0x45: "high-score screen wait complete",
    0x46: "attract demo prepared",
    0x50: "main menu entered",
    0x51: "episode menu entered",
    0x52: "difficulty menu entered",
    0x53: "new game accepted",
    0x60: "gameplay session entered",
    0x61: "level package load beginning",
    0x62: "level package load complete",
    0x63: "wall texture load beginning",
    0x64: "wall texture load complete",
    0x65: "sprite load beginning",
    0x66: "sprite load complete",
    0x67: "HUD load beginning",
    0x68: "HUD load complete",
    0x69: "gameplay display setup beginning",
    0x6A: "gameplay mode fence complete",
    0x6B: "renderer backend open beginning",
    0x6C: "renderer backend open complete",
    0x6D: "initial renderer reset submitted",
    0x70: "gameplay shutdown beginning",
    0xF1: "shell asset load failed",
    0xF2: "SFX asset load failed",
    0xF3: "buffered SFX command installation failed",
    0xF4: "gameplay startup failed before renderer ownership",
    0xF5: "gameplay failed during renderer ownership",
    0xF6: "renderer backend close failed",
}


def parse_sound_names(path: Path) -> dict[int, str]:
    names: dict[int, str] = {}
    pattern = re.compile(r"^W3D_AUDIO_SOUND_([A-Z0-9_]+):\s+equ\s+(\d+)")
    for line in path.read_text().splitlines():
        match = pattern.match(line)
        if match:
            names[int(match.group(2))] = match.group(1)
    return names


def decode(lines: list[str], sound_names: dict[int, str]) -> list[str]:
    decoded: list[str] = []
    for line_number, line in enumerate(lines, 1):
        match = BUFFER_RE.search(line)
        if not match:
            continue
        buffer_id = int(match.group(1))
        family = buffer_id & 0xFF00
        value = buffer_id & 0xFF
        if family == 0xD000:
            label = STAGES.get(value, "unknown stage")
            decoded.append(f"{line_number:6d}  D0{value:02X}  {label}")
        elif family == 0xD100:
            label = sound_names.get(value, "unknown sound")
            decoded.append(f"{line_number:6d}  D1{value:02X}  SFX {value:02d} {label}")
    return decoded


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("logs", nargs="*", type=Path, help="serial logs; stdin if omitted")
    args = parser.parse_args()
    source = Path(__file__).resolve().parents[1] / "src/wolf3d_audio_assets.inc"
    sound_names = parse_sound_names(source)
    if args.logs:
        lines: list[str] = []
        for path in args.logs:
            lines.extend(path.read_text(errors="replace").splitlines())
    else:
        lines = sys.stdin.read().splitlines()
    for item in decode(lines, sound_names):
        print(item)


if __name__ == "__main__":
    main()
