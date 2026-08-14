#!/usr/bin/env python3
"""Assemble and run directed production EXITTILE eZ80 checks."""

from __future__ import annotations

import argparse
import atexit
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time


_root_override = os.environ.get("W3D_STAGED_ROOT")
_installed_root = Path(__file__).resolve().parents[4]
STAGED_ROOT = Path(_root_override) if _root_override else _installed_root
RUNTIME_ROOT = Path(os.environ.get("W3D_RUNTIME_ROOT", _installed_root))
STAGED_SRC = STAGED_ROOT / "src/asm/wolf3d/src"
FAB = RUNTIME_ROOT / "agonport/emulator/fab-agon-emulator"
MOS = RUNTIME_ROOT / "agonport/emulator/mos_console8.bin"
VDP = RUNTIME_ROOT / "agonport/emulator/vdp_stock.so"
RESULT_SIZE = 16


def run(command: list[str], *, cwd: Path | None = None) -> None:
    print("+", " ".join(command))
    subprocess.run(command, check=True, cwd=cwd)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timeout", type=float, default=30.0)
    args = parser.parse_args()
    work = Path(tempfile.mkdtemp(prefix="v"))
    atexit.register(shutil.rmtree, work, ignore_errors=True)
    sdcard = work / "sdcard"
    app = sdcard / "v"
    app.mkdir(parents=True)
    entry = work / "v.asm"
    shutil.copyfile(
        STAGED_ROOT / "src/asm/wolf3d_gameplay/src/victory_regression.asm", entry
    )
    binary = app / "v.bin"
    run(["ez80asm", str(entry), str(binary)], cwd=STAGED_SRC)
    (sdcard / "autoexec.txt").write_bytes(
        b"SET KEYBOARD 1\r\ncd v\r\nload v.bin\r\nrun\r\n"
    )
    result = app / "victory_result.bin"
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
                if len(payload) == RESULT_SIZE and payload[:4] == b"W3V1":
                    break
            time.sleep(0.05)
        else:
            raise RuntimeError("timed out waiting for victory regression")
    finally:
        process.terminate()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
    records, errors, case, reason, expected, actual = payload[4:10]
    if errors:
        print(
            f"FAIL: {errors} failed victory checks in {records}; first "
            f"case={case} reason={reason} expected={expected:#04x} actual={actual:#04x}"
        )
        return 1
    print(f"PASS: {records}/{records} directed production EXITTILE eZ80 cases")
    return 0


if __name__ == "__main__":
    sys.exit(main())
