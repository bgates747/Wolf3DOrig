#!/usr/bin/env python3
"""Assemble and run the direct production-intermission eZ80 regression."""

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
PRODUCTION_SRC = STAGED_ROOT / "src/asm/wolf3d/src"
FIXTURE = (
    STAGED_ROOT
    / "src/asm/wolf3d_intermission/src/intermission_regression.asm"
)
FAB = RUNTIME_ROOT / "agonport/emulator/fab-agon-emulator"
MOS = RUNTIME_ROOT / "agonport/emulator/mos_console8.bin"
VDP = RUNTIME_ROOT / "agonport/emulator/vdp_stock.so"
RESULT_SIZE = 16 + 37 * 6

REASONS = {
    1: "level-time subticks",
    2: "level-time seconds",
    3: "level-time minutes",
    4: "derived total low byte",
    5: "derived total high byte",
    6: "percentage result",
    7: "shell setup count",
    8: "acknowledgment count",
    9: "plot count",
    10: "plot buffer",
    11: "plot x coordinate",
    12: "plot y coordinate",
    13: "par minutes",
    14: "par seconds",
    15: "public result",
    16: "public carry result",
    17: "input armed state",
    18: "acknowledgment latch",
    19: "animation divider",
    20: "portrait frame",
    21: "keyboard-read count",
    22: "Escape latch",
    23: "post-acknowledgment release latch",
    24: "application-exit query count",
    25: "ordered-ingress fence count",
    26: "ordered-ingress failure latch",
    27: "par time remaining",
    28: "32-bit bonus byte",
    29: "persistent level-ratio record",
    30: "single point-award call",
    31: "count-up sound count",
    32: "count-up logical sound id",
    33: "count-up stage",
}


def run(command: list[str], *, cwd: Path | None = None) -> None:
    print("+", " ".join(command))
    subprocess.run(command, check=True, cwd=cwd)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timeout", type=float, default=30.0)
    args = parser.parse_args()

    for dependency in (PRODUCTION_SRC, FIXTURE, FAB, MOS, VDP):
        if not dependency.exists():
            raise FileNotFoundError(
                f"missing intermission regression dependency: {dependency}"
            )

    # ez80asm retains DOS-era path limits. Build from an isolated short copy
    # of the production include directory so concurrent app builds are safe.
    work = Path(tempfile.mkdtemp(prefix="wi"))
    atexit.register(shutil.rmtree, work, ignore_errors=True)
    build_src = work / "src"
    shutil.copytree(PRODUCTION_SRC, build_src)
    entry = build_src / "i.asm"
    shutil.copyfile(FIXTURE, entry)

    sdcard = work / "sd"
    app = sdcard / "i"
    app.mkdir(parents=True)
    binary = app / "i.bin"
    run(["ez80asm", entry.name, str(binary)], cwd=build_src)
    (sdcard / "autoexec.txt").write_bytes(
        b"SET KEYBOARD 1\r\ncd i\r\nload i.bin\r\nrun\r\n"
    )

    result = app / "intermission_result.bin"
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
        "--renderer",
        "sw",
        "--firmware",
        "console8",
        "--mos",
        str(MOS.resolve()),
        "--vdp",
        str(VDP.resolve()),
        "--sdcard",
        str(sdcard),
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
    payload = b""
    try:
        deadline = time.monotonic() + args.timeout
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError(f"emulator exited with {process.returncode}")
            if result.exists():
                payload = result.read_bytes()
                if len(payload) == RESULT_SIZE and payload[:4] == b"W3I1":
                    break
            time.sleep(0.05)
        else:
            raise RuntimeError("timed out waiting for intermission result")
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
            f"FAIL: {errors} failures in {checks} intermission checks; "
            f"first case={first_case} reason={REASONS.get(reason, reason)} "
            f"expected={expected:#04x} actual={actual:#04x}"
        )
        for index in range(37):
            offset = 16 + index * 6
            buffer_id = int.from_bytes(payload[offset : offset + 2], "little")
            x = int.from_bytes(payload[offset + 2 : offset + 4], "little")
            y = int.from_bytes(payload[offset + 4 : offset + 6], "little")
            print(f"  plot {index:02d}: buffer={buffer_id:#06x} x={x} y={y}")
        return 1
    print(f"PASS: {checks}/{checks} direct production-intermission eZ80 checks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
