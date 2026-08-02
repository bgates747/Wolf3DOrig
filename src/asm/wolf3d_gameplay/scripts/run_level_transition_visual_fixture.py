#!/usr/bin/env python3
"""Launch E1L1 beside an elevator for a quick visual transition check."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile


PROJECT_ROOT = Path(__file__).resolve().parents[4]
GENERATED = PROJECT_ROOT / "agonport/assets/generated/wolf3d"
PROFILE = PROJECT_ROOT / "agonport/emulator"


def require_file(path: Path) -> Path:
    if not path.is_file() or path.stat().st_size == 0:
        raise RuntimeError(f"missing or empty fixture artifact: {path}")
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--route", choices=("normal", "secret"), default="normal")
    args = parser.parse_args()

    if args.route == "normal":
        player_x, player_y, player_angle, target_level = 25, 47, 0, 1
    else:
        player_x, player_y, player_angle, target_level = 10, 51, 180, 9

    with tempfile.TemporaryDirectory(prefix="w3v") as temporary:
        run_root = Path(temporary)
        sdcard = run_root / "sdcard"
        app = sdcard / "wolf3d"
        app.mkdir(parents=True)
        shutil.copyfile(
            require_file(PROJECT_ROOT / "src/asm/wolf3d/tgt/wolf3d.bin"),
            app / "wolf3d.bin",
        )
        for filename, source in (
            ("hud.agnb", GENERATED / "hud/hud.agnb"),
            ("sfx.agnb", GENERATED / "audio/sfx.agnb"),
        ):
            shutil.copyfile(require_file(source), app / filename)
        for index in sorted({0, target_level}):
            source = GENERATED / "levels" / f"level_{index:02d}"
            shutil.copytree(source, app / source.name)

        state_path = app / "level_00/state_medium.w3l"
        state = bytearray(state_path.read_bytes())
        fixed_x = (player_x << 16) + 0x8000
        fixed_y = (player_y << 16) + 0x8000
        struct.pack_into("<iiH", state, 16, fixed_x, fixed_y, player_angle)
        state_path.write_bytes(state)
        (sdcard / "autoexec.txt").write_bytes(
            b"SET KEYBOARD 1\r\ncd wolf3d\r\nload wolf3d.bin\r\nrun\r\n"
        )

        environment = os.environ.copy()
        environment["SDL_VIDEODRIVER"] = "wayland"
        local_lib = str(Path.home() / ".local/lib")
        environment["LD_LIBRARY_PATH"] = local_lib + (
            ":" + environment["LD_LIBRARY_PATH"]
            if environment.get("LD_LIBRARY_PATH")
            else ""
        )
        emulator = [
            str(require_file(PROFILE / "fab-agon-emulator").resolve()),
            "--renderer",
            "sw",
            "--firmware",
            "console8",
            "--mos",
            str(require_file(PROFILE / "mos_console8.bin").resolve()),
            "--vdp",
            str(require_file(PROFILE / "vdp_wolf3d.so").resolve()),
            "--sdcard",
            str(sdcard),
            "--zero",
        ]
        print(
            f"Starting beside the {args.route} E1L1 elevator at "
            f"({player_x},{player_y}); press Up Arrow to enter level {target_level}."
        )
        print("Escape exits the fixture.")
        subprocess.run(emulator, check=True, cwd=run_root, env=environment)


if __name__ == "__main__":
    main()
