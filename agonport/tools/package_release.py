#!/usr/bin/env python3
"""Build and verify a deterministic Wolf3DOrig application release archive.

The combined PingoWolf firmware is a mandatory part of the release contract.
The packager deliberately has no application-only mode: Wolf3DOrig cannot run
on an ordinary VDP, so omitting firmware would produce an incomplete release.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import tempfile
import zipfile
from pathlib import Path


HOME = Path.home()
REPO = Path(__file__).resolve().parents[2]
DEFAULT_SNAPSHOT = (
    HOME / "Agon/mystuff/agon-dev-env/emulators/wolf-pingo-v2.16/snapshots/wolf3d"
)
DEFAULT_FIRMWARE = (
    HOME / "Agon/mystuff/agon-vdp-wolf-pingo/.pio/build/esp32dev/firmware.bin"
)
DEFAULT_OUTPUT = REPO / "agonport/release/Wolf3DOrig-app-0.1.0-alpha.1.zip"
RELEASE_NOTES = REPO / "agonport/doc/releases/wolf3dorig-app-v0.1.0-alpha.1.md"
ROOT_NAME = "Wolf3DOrig-app-0.1.0-alpha.1"
APP_COMMIT = "3695b7dbfbecb63a635fee332fa4d9a937b9263b"
FIRMWARE_COMMIT = "3c07e754b00cc863b9cf04e0baf140d778553eed"
FIRMWARE_RELEASE = "pingowolf-v0.1.0-alpha.1"
EXPECTED = {
    "firmware.bin": "b6c529de07f46a6d9d75da0c87908b75dd81b3cbdee4f4aaa4a774522c2ed2ce",
    "wolf3d.bin": "2d845e2882ae22012f0c64c7705d47b7413dc6b6301bc07bcdfdfadbe635f1c7",
    "tiles.agnb": "9990d79e3ae47d0c940e072f70f821d505d9e39ce21f713b38f5d8c7237502c8",
    "sprites.agnb": "7bf0f04a6fad56d5a83b26b30f5c0ea3bbafb4c8727a3c5f9d266c30c0e058f9",
    "hud.agnb": "1848900559fe9f684dbfc8ae80b0416132db5414bc1ab41f9dad47a5ab26a74d",
    "sfx.agnb": "f294c1152bedca56e726e115ce1d1dc2f5aa6191e340a96a79b1e845296f1cd4",
}
ZIP_TIME = (2026, 8, 1, 0, 0, 0)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def qualified_copy(source: Path, destination: Path, expected: str) -> None:
    if not source.is_file():
        raise RuntimeError(f"required release input is missing: {source}")
    actual = sha256(source)
    if actual != expected:
        raise RuntimeError(f"unexpected SHA-256 for {source}: {actual}; expected {expected}")
    shutil.copyfile(source, destination)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT)
    parser.add_argument("--firmware", type=Path, default=DEFAULT_FIRMWARE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="wolf3dorig-release-") as temporary:
        root = Path(temporary) / ROOT_NAME
        app = root / "wolf3dorig"
        app.mkdir(parents=True)

        # firmware.bin is intentionally mandatory and lives at archive root so
        # it can be copied directly to an Agon SD card and flashed from MOS.
        qualified_copy(args.firmware, root / "firmware.bin", EXPECTED["firmware.bin"])
        for name in ("wolf3d.bin", "tiles.agnb", "sprites.agnb", "hud.agnb", "sfx.agnb"):
            qualified_copy(args.snapshot / name, app / name, EXPECTED[name])

        shutil.copyfile(RELEASE_NOTES, root / "RELEASE-NOTES.md")
        shutil.copyfile(REPO / "README.md", root / "NOTICE.md")
        (root / "autoexec.wolf3dorig.txt").write_bytes(
            b"set keyboard 1\r\ncd /wolf3dorig\r\nload wolf3d.bin\r\nrem run\r\n"
        )

        files = []
        for path in sorted(root.rglob("*")):
            if path.is_file() and path.name not in {"manifest.json", "SHA256SUMS"}:
                files.append(
                    {
                        "path": path.relative_to(root).as_posix(),
                        "size": path.stat().st_size,
                        "sha256": sha256(path),
                    }
                )
        manifest = {
            "product": "Wolf3DOrig App",
            "version": "0.1.0 Alpha 1",
            "tag": "wolf3dorig-app-v0.1.0-alpha.1",
            "application_commit": APP_COMMIT,
            "wire_abi": "1.0",
            "compatible_firmware_release": FIRMWARE_RELEASE,
            "firmware_commit": FIRMWARE_COMMIT,
            "files": files,
        }
        (root / "manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        sums = [f"{record['sha256']}  {record['path']}\n" for record in files]
        sums.append(f"{sha256(root / 'manifest.json')}  manifest.json\n")
        (root / "SHA256SUMS").write_text("".join(sums), encoding="utf-8")

        if args.output.exists():
            args.output.unlink()
        with zipfile.ZipFile(args.output, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for path in sorted(root.rglob("*")):
                if path.is_file():
                    info = zipfile.ZipInfo(path.relative_to(root.parent).as_posix(), ZIP_TIME)
                    info.compress_type = zipfile.ZIP_DEFLATED
                    info.external_attr = 0o100644 << 16
                    archive.writestr(info, path.read_bytes(), compresslevel=9)

    with tempfile.TemporaryDirectory(prefix="wolf3dorig-verify-") as temporary:
        with zipfile.ZipFile(args.output) as archive:
            failed = archive.testzip()
            if failed:
                raise RuntimeError(f"ZIP CRC failure: {failed}")
            archive.extractall(temporary)
        root = Path(temporary) / ROOT_NAME
        manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
        for record in manifest["files"]:
            path = root / record["path"]
            if path.stat().st_size != record["size"] or sha256(path) != record["sha256"]:
                raise RuntimeError(f"archive verification failed: {record['path']}")
        if sha256(root / "firmware.bin") != EXPECTED["firmware.bin"]:
            raise RuntimeError("archive firmware verification failed")

    print(f"{args.output} {args.output.stat().st_size} sha256 {sha256(args.output)}")


if __name__ == "__main__":
    main()
