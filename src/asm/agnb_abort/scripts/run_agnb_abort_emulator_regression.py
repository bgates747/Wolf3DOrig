#!/usr/bin/env python3
"""Assemble and run the production-AGNB abort callback regression."""

from __future__ import annotations

import argparse
import atexit
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import time

_root_override = os.environ.get("W3D_STAGED_ROOT")
_installed_root = Path(__file__).resolve().parents[4]
STAGED_ROOT = Path(_root_override) if _root_override else _installed_root
RUNTIME_ROOT = Path(os.environ.get("W3D_RUNTIME_ROOT", _installed_root))
PRODUCTION_SRC = STAGED_ROOT / "src/asm/wolf3d/src"
FIXTURE = STAGED_ROOT / "src/asm/agnb_abort/src/agnb_abort_regression.asm"
FAB = RUNTIME_ROOT / "agonport/emulator/fab-agon-emulator"
MOS = RUNTIME_ROOT / "agonport/emulator/mos_console8.bin"
VDP = RUNTIME_ROOT / "agonport/emulator/vdp_stock.so"
RESULT_SIZE = 16

REASONS = {
    1: "loader result", 2: "callback count", 3: "finalized-record count",
    4: "FIL open state", 5: "agnb_last_error", 6: "early reader offset",
}


def riff_chunk(identifier: bytes, payload: bytes) -> bytes:
    padding = bytes((-len(payload)) & 3)
    return identifier + struct.pack("<I", len(payload)) + payload + padding


def agnb_container(version_minor: int, records: list[bytes]) -> bytes:
    contents = b"AGNB" + riff_chunk(b"VERS", bytes((0, version_minor)))
    contents += b"".join(riff_chunk(b"LIST", b"BUFR" + r) for r in records)
    return b"RIFF" + struct.pack("<I", len(contents)) + contents


def image_container() -> bytes:
    records = []
    for index, pixel in enumerate((0x03, 0x1C, 0xE0)):
        records.append(
            riff_chunk(b"BHDR", struct.pack("<H", 0x7000 + index))
            + riff_chunk(b"IMAG", struct.pack("<HHB", 1, 1, 1))
            + riff_chunk(b"DATA", bytes((pixel,)))
        )
    return agnb_container(1, records)


def audio_container() -> bytes:
    records = []
    for index, sample in enumerate((0x20, 0x80, 0xE0)):
        records.append(
            riff_chunk(b"BHDR", struct.pack("<H", 0x7100 + index))
            + riff_chunk(b"AUDI", struct.pack("<BH", 0x09, 7000))
            + riff_chunk(b"DATA", bytes((sample,)))
        )
    return agnb_container(2, records)


def run(command: list[str], *, cwd: Path | None = None) -> None:
    print("+", " ".join(command))
    subprocess.run(command, check=True, cwd=cwd)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timeout", type=float, default=30.0)
    args = parser.parse_args()
    for dependency in (PRODUCTION_SRC, FIXTURE, FAB, MOS, VDP):
        if not dependency.exists():
            raise FileNotFoundError(f"missing AGNB abort dependency: {dependency}")

    work = Path(tempfile.mkdtemp(prefix="wa"))
    atexit.register(shutil.rmtree, work, ignore_errors=True)
    build_src = work / "src"
    shutil.copytree(PRODUCTION_SRC, build_src)
    entry = build_src / "a.asm"
    shutil.copyfile(FIXTURE, entry)
    sdcard = work / "sd"
    app = sdcard / "a"
    app.mkdir(parents=True)
    binary = app / "a.bin"
    run(["ez80asm", entry.name, str(binary)], cwd=build_src)
    (app / "image.agnb").write_bytes(image_container())
    (app / "audio.agnb").write_bytes(audio_container())
    (sdcard / "autoexec.txt").write_bytes(
        b"SET KEYBOARD 1\r\ncd a\r\nload a.bin\r\nrun\r\n"
    )

    result = app / "agnb_abort_result.bin"
    environment = os.environ.copy()
    environment["SDL_VIDEODRIVER"] = "dummy"
    environment["SDL_AUDIODRIVER"] = "dummy"
    local_lib = str(Path.home() / ".local/lib")
    environment["LD_LIBRARY_PATH"] = local_lib + (
        ":" + environment["LD_LIBRARY_PATH"]
        if environment.get("LD_LIBRARY_PATH") else ""
    )
    emulator = [
        str(FAB.resolve()), "--renderer", "sw", "--firmware", "console8",
        "--mos", str(MOS.resolve()), "--vdp", str(VDP.resolve()),
        "--sdcard", str(sdcard), "--zero",
    ]
    print("+", " ".join(emulator))
    process = subprocess.Popen(
        emulator, cwd=work, env=environment,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    payload = b""
    try:
        deadline = time.monotonic() + args.timeout
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError(f"emulator exited with {process.returncode}")
            if result.exists():
                payload = result.read_bytes()
                if len(payload) == RESULT_SIZE and payload[:4] == b"AGA1":
                    break
            time.sleep(0.05)
        else:
            raise RuntimeError("timed out waiting for AGNB abort result")
    finally:
        process.terminate()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()

    checks, errors, first_case, reason, expected, actual = payload[4:10]
    if errors:
        print(
            f"FAIL: {errors} failures in {checks} checks; case={first_case} "
            f"reason={REASONS.get(reason, reason)} expected={expected:#04x} "
            f"actual={actual:#04x}"
        )
        return 1
    print(f"PASS: {checks}/{checks} production-AGNB abort checks (image/audio)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
