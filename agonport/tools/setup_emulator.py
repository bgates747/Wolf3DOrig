#!/usr/bin/env python3
"""Create the Agon port's isolated stock-VDP Fab profile."""

from __future__ import annotations

import os
from pathlib import Path


AGON_ROOT = Path.home() / "Agon"
FAB_ROOT = AGON_ROOT / "fab-agon-emulator"
PORT_ROOT = Path(__file__).resolve().parent.parent
PROFILE = PORT_ROOT / "emulator"


def replace_symlink(link: Path, target: Path) -> None:
    if link.is_symlink():
        link.unlink()
    elif link.exists():
        raise SystemExit(f"Refusing to replace non-symlink path: {link}")
    link.parent.mkdir(parents=True, exist_ok=True)
    link.symlink_to(os.path.relpath(target, link.parent))


def main() -> None:
    artifacts = {
        PROFILE / "fab-agon-emulator": FAB_ROOT / "fab-agon-emulator",
        PROFILE / "vdp_stock.so": FAB_ROOT / "firmware/vdp_console8.so",
        PROFILE / "mos_console8.bin": FAB_ROOT / "firmware/mos_console8.bin",
        PROFILE / "sdcard/bin": FAB_ROOT / "sdcard/bin",
        PROFILE / "sdcard/mos": FAB_ROOT / "sdcard/mos",
        PROFILE / "sdcard/firmware.bin": FAB_ROOT / "sdcard/firmware.bin",
        PROFILE / "sdcard/MOS.bin": FAB_ROOT / "sdcard/MOS.bin",
    }
    missing = [target for target in artifacts.values() if not target.exists()]
    if missing:
        raise SystemExit(
            "Required stock Fab artifacts are missing:\n"
            + "\n".join(f"  {path}" for path in missing)
        )

    for link, target in artifacts.items():
        replace_symlink(link, target)

    autoexec = PROFILE / "sdcard/autoexec.txt"
    if not autoexec.exists():
        autoexec.write_bytes(b"SET KEYBOARD 1\r\n")

    print(f"Emulator profile: {PROFILE}")
    print(f"Stock VDP:        {PROFILE / 'vdp_stock.so'}")
    print(f"Autoexec:         {autoexec}")


if __name__ == "__main__":
    main()