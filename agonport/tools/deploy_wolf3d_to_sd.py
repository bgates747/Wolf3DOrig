#!/usr/bin/env python3
"""Deploy the Wolf3DOrig hardware fixture to one explicitly mounted Agon SD card."""

from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import shutil
import subprocess


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MOUNT = Path("/media/smith/AGON")
APP_DIRECTORY = "wolf3dorig"
AUTOEXEC_KEYBOARD = "SET KEYBOARD 1"
AUTOEXEC_DIRECTORY = "cd /wolf3dorig"
AUTOEXEC_LOAD = "load wolf3d.bin"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def mounted_filesystem(mount: Path) -> tuple[str, str, str]:
    result = subprocess.run(
        [
            "findmnt",
            "--noheadings",
            "--output",
            "FSTYPE,LABEL,SOURCE",
            "--target",
            str(mount),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    fields = result.stdout.split()
    if len(fields) != 3:
        raise RuntimeError(f"Unexpected findmnt result for {mount}: {result.stdout!r}")
    return fields[0], fields[1], fields[2]


def replace_file(source: Path, destination: Path) -> None:
    temporary = destination.with_name(f".{destination.name}.deploying")
    if temporary.exists():
        temporary.unlink()
    try:
        shutil.copyfile(source, temporary)
        os.replace(temporary, destination)
    finally:
        if temporary.exists():
            temporary.unlink()


def build_autoexec(existing: bytes, *, run: bool) -> bytes:
    """Comment every old directive and select only this application."""

    retained: list[str] = []
    for raw_line in existing.decode("ascii").replace("\r\n", "\n").split("\n"):
        line = raw_line.strip()
        if not line or line.upper() == AUTOEXEC_KEYBOARD:
            continue
        retained.append(line if line.startswith("#") else f"# {line}")

    selected = [AUTOEXEC_KEYBOARD, *retained, AUTOEXEC_DIRECTORY, AUTOEXEC_LOAD]
    selected.append("run" if run else "# run")
    return ("\r\n".join(selected) + "\r\n").encode("ascii")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mount", type=Path, default=DEFAULT_MOUNT)
    parser.add_argument(
        "--write-autoexec",
        action="store_true",
        help="select Wolf3DOrig in autoexec.txt (load-only unless --run is set)",
    )
    parser.add_argument(
        "--run",
        action="store_true",
        help="with --write-autoexec, automatically run Wolf3DOrig at boot",
    )
    args = parser.parse_args()
    if args.run and not args.write_autoexec:
        parser.error("--run requires --write-autoexec")

    mount = args.mount.resolve(strict=True)
    if not mount.is_dir() or not os.path.ismount(mount):
        raise RuntimeError(f"Not a mounted filesystem root: {mount}")
    fstype, label, source_device = mounted_filesystem(mount)
    if fstype.lower() not in {"vfat", "fat", "fat32"}:
        raise RuntimeError(f"Refusing non-FAT destination {mount}: {fstype}")
    if label != "AGON":
        raise RuntimeError(f"Refusing unexpected SD label at {mount}: {label!r}")

    sources = {
        "wolf3d.bin": PROJECT_ROOT / "src/asm/wolf3d/tgt/wolf3d.bin",
        "tiles.agnb": PROJECT_ROOT
        / "agonport/assets/generated/wolf3d/levels/level_00/tiles.agnb",
        "sprites.agnb": PROJECT_ROOT
        / "agonport/assets/generated/wolf3d/levels/level_00/sprites.agnb",
        "hud.agnb": PROJECT_ROOT
        / "agonport/assets/generated/wolf3d/hud/hud.agnb",
        "sfx.agnb": PROJECT_ROOT
        / "agonport/assets/generated/wolf3d/audio/sfx.agnb",
    }
    for source in sources.values():
        if not source.is_file() or source.stat().st_size == 0:
            raise RuntimeError(f"Missing or empty deployment source: {source}")

    destination = mount / APP_DIRECTORY
    if destination.is_symlink():
        raise RuntimeError(f"Refusing symlinked application destination: {destination}")
    destination.mkdir(exist_ok=True)
    for filename, source in sources.items():
        target = destination / filename
        replace_file(source, target)
        print(
            f"Deployed {target} ({target.stat().st_size} bytes, "
            f"sha256 {sha256(source)})"
        )

    if args.write_autoexec:
        autoexec_source = destination / ".autoexec.deploying"
        autoexec_target = mount / "autoexec.txt"
        existing_autoexec = autoexec_target.read_bytes() if autoexec_target.exists() else b""
        autoexec_source.write_bytes(build_autoexec(existing_autoexec, run=args.run))
        try:
            replace_file(autoexec_source, autoexec_target)
        finally:
            if autoexec_source.exists():
                autoexec_source.unlink()
        action = "run" if args.run else "load"
        print(f"Updated autoexec.txt to {action} /wolf3dorig/wolf3d.bin at boot")

    os.sync()
    print(f"Deployment synced to {source_device} ({fstype}, label {label})")


if __name__ == "__main__":
    main()
