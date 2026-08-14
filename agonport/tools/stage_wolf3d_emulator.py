#!/usr/bin/env python3
"""Stage the current Wolf3DOrig application into its ignored emulator SD tree."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROFILE = PROJECT_ROOT / "agonport/emulator"
APP = PROFILE / "sdcard/wolf3d"
GENERATED = PROJECT_ROOT / "agonport/assets/generated/wolf3d"


def replace_symlink(link: Path, target: Path) -> None:
    if link.is_symlink():
        link.unlink()
    elif link.exists():
        raise RuntimeError(f"Refusing to replace non-symlink path: {link}")
    link.symlink_to(os.path.relpath(target, link.parent))


def require_file(path: Path) -> Path:
    if not path.is_file() or path.stat().st_size == 0:
        raise RuntimeError(f"Missing or empty emulator artifact: {path}")
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--write-autoexec",
        action="store_true",
        help="select and run the staged application on emulator boot",
    )
    args = parser.parse_args()

    if not (PROFILE / "sdcard").is_dir():
        raise RuntimeError("Emulator profile is absent; run setup_emulator.py first")
    APP.mkdir(exist_ok=True)

    binary = require_file(PROJECT_ROOT / "src/asm/wolf3d/tgt/wolf3d.bin")
    shutil.copyfile(binary, APP / "wolf3d.bin")

    shared = {
        "hud.agnb": GENERATED / "hud/hud.agnb",
        "sfx.agnb": GENERATED / "audio/sfx.agnb",
        "shell.agnb": GENERATED / "shell/shell.agnb",
    }
    for name, source in shared.items():
        replace_symlink(APP / name, require_file(source))

    levels = GENERATED / "levels"
    for index in range(10):
        source = levels / f"level_{index:02d}"
        for filename in (
            "tiles.agnb",
            "sprites.agnb",
            "state_baby.w3l",
            "state_easy.w3l",
            "state_medium.w3l",
            "state_hard.w3l",
        ):
            require_file(source / filename)
        replace_symlink(APP / source.name, source)

    if args.write_autoexec:
        (PROFILE / "sdcard/autoexec.txt").write_bytes(
            b"SET KEYBOARD 1\r\n"
            b"cd wolf3d\r\n"
            b"load wolf3d.bin\r\n"
            b"run\r\n"
        )

    print(f"Staged {binary.stat().st_size} byte application at {APP}")
    print("Linked 10 runtime level directories plus shell/HUD/SFX shared assets")


if __name__ == "__main__":
    main()
