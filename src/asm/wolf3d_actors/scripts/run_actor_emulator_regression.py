#!/usr/bin/env python3
"""Assemble and run the direct production-actor eZ80 regression."""

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


HERE = Path(__file__).resolve().parent
_root_override = os.environ.get("W3D_STAGED_ROOT")
_installed_root = Path(__file__).resolve().parents[4]
STAGED_ROOT = Path(_root_override) if _root_override else _installed_root
RUNTIME_ROOT = Path(os.environ.get("W3D_RUNTIME_ROOT", _installed_root))
STAGED_SRC = STAGED_ROOT / "src/asm/wolf3d/src"
FAB = RUNTIME_ROOT / "agonport/emulator/fab-agon-emulator"
MOS = RUNTIME_ROOT / "agonport/emulator/mos_console8.bin"
VDP = RUNTIME_ROOT / "agonport/emulator/vdp_stock.so"
RESULT_SIZE = 16

PHASES = {
    1: "generated E1L1 initialization",
    2: "pointer helpers",
    3: "allocation/lifetime",
    4: "pool exhaustion",
    5: "player/actor collision",
    6: "VDP actor command wire",
}

REASONS = {
    1: "scalar invariant",
    2: "authoritative memory",
    3: "live/free list",
    4: "free-record bytes",
    5: "actorat occupancy",
    6: "dirty lifecycle",
    7: "pointer/state lookup",
    8: "allocator carry",
    9: "collision result",
    10: "wire command prefix",
    11: "wire payload",
    12: "wire command length",
}


def run(command: list[str], *, cwd: Path | None = None) -> None:
    print("+", " ".join(command))
    subprocess.run(command, check=True, cwd=cwd)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--timeout", type=float, default=30.0)
    args = parser.parse_args()

    missing = [path for path in (STAGED_SRC, FAB, MOS, VDP) if not path.exists()]
    if missing:
        raise FileNotFoundError("missing actor regression dependency: " + ", ".join(map(str, missing)))

    # ez80asm retains short DOS-era source/output path restrictions.
    work = Path(tempfile.mkdtemp(prefix="a"))
    atexit.register(shutil.rmtree, work, ignore_errors=True)
    sdcard = work / "sdcard"
    app = sdcard / "a"
    app.mkdir(parents=True)

    entry = work / "a.asm"
    shutil.copyfile(HERE.parent / "src/actor_regression.asm", entry)
    binary = app / "a.bin"
    run(["ez80asm", str(entry), str(binary)], cwd=STAGED_SRC)
    (sdcard / "autoexec.txt").write_bytes(
        b"SET KEYBOARD 1\r\n"
        b"cd a\r\n"
        b"load a.bin\r\n"
        b"run\r\n"
    )

    result = app / "actor_result.bin"
    environment = os.environ.copy()
    environment["SDL_VIDEODRIVER"] = "dummy"
    environment["SDL_AUDIODRIVER"] = "dummy"
    local_lib = str(Path.home() / ".local/lib")
    environment["LD_LIBRARY_PATH"] = local_lib + (
        ":" + environment["LD_LIBRARY_PATH"]
        if environment.get("LD_LIBRARY_PATH")
        else ""
    )
    emulator = [
        str(FAB.resolve()),
        "--renderer", "sw",
        "--firmware", "console8",
        "--mos", str(MOS.resolve()),
        "--vdp", str(VDP.resolve()),
        "--sdcard", str(sdcard),
        "--zero",
    ]
    print("+", " ".join(emulator))
    process = subprocess.Popen(
        emulator,
        cwd=work,
        env=environment,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        deadline = time.monotonic() + args.timeout
        payload = b""
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError(f"emulator exited with {process.returncode}")
            if result.exists():
                payload = result.read_bytes()
                if len(payload) == RESULT_SIZE and payload[:4] == b"W3A1":
                    break
            time.sleep(0.05)
        else:
            raise RuntimeError("timed out waiting for actor emulator result")
    finally:
        process.terminate()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()

    checks = int.from_bytes(payload[4:6], "little")
    errors = int.from_bytes(payload[6:8], "little")
    phase, reason, expected, actual, detail = payload[8:13]
    if errors:
        print(
            f"FAIL: {errors} mismatches in {checks} real-eZ80 checks; "
            f"phase={PHASES.get(phase, phase)} reason={REASONS.get(reason, reason)} "
            f"detail={detail} expected={expected:#04x} actual={actual:#04x}"
        )
        return 1
    print(f"PASS: {checks} direct production-actor eZ80 checks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
