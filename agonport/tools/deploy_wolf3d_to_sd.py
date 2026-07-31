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
AUTOEXEC = (
    b"SET KEYBOARD 1\r\n"
    b"cd /wolf3dorig\r\n"
    b"load wolf3d.bin\r\n"
    b"# run\r\n"
)


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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mount", type=Path, default=DEFAULT_MOUNT)
    parser.add_argument(
        "--write-autoexec",
        action="store_true",
        help="select Wolf3DOrig at boot, loading but not automatically running it",
    )
    args = parser.parse_args()

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
        autoexec_source.write_bytes(AUTOEXEC)
        try:
            replace_file(autoexec_source, mount / "autoexec.txt")
        finally:
            if autoexec_source.exists():
                autoexec_source.unlink()
        print("Updated autoexec.txt to load /wolf3dorig/wolf3d.bin without running it")

    os.sync()
    print(f"Deployment synced to {source_device} ({fstype}, label {label})")


if __name__ == "__main__":
    main()
