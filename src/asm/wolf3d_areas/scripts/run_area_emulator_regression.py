#!/usr/bin/env python3
"""Assemble and run the direct production-area eZ80 regression fixture."""

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
RESULT_SIZE = 32

CASES = {
    1: "initialization",
    2: "real E1L1 topology",
    3: "parallel-door thresholds",
    4: "partial close/reversal",
    5: "player-area transitions",
    6: "malformed-edge batching",
    7: "self-loop",
    8: "rebuild ABI",
}

REASONS = {
    1: "reachability byte",
    2: "player area",
    3: "topology dirty flag",
    4: "fault counter",
    5: "queue head/tail",
    6: "door action/position/dirty",
    7: "preserved register",
}


def run(command: list[str], *, cwd: Path | None = None) -> None:
    print("+", " ".join(command))
    subprocess.run(command, check=True, cwd=cwd)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--timeout", type=float, default=45.0)
    args = parser.parse_args()

    dependencies = (STAGED_SRC, FAB, MOS, VDP)
    missing = [path for path in dependencies if not path.exists()]
    if missing:
        raise FileNotFoundError(
            "missing area regression dependency: " + ", ".join(map(str, missing))
        )

    # ez80asm retains DOS-era path-length restrictions. Keep the entry, all
    # production include symlinks, and output in one disposable short path.
    work = Path(tempfile.mkdtemp(prefix="a"))
    atexit.register(shutil.rmtree, work, ignore_errors=True)
    for include in STAGED_SRC.glob("*.inc"):
        (work / include.name).symlink_to(include.resolve())

    entry = work / "a.asm"
    shutil.copyfile(HERE.parent / "src/area_regression.asm", entry)
    sdcard = work / "sdcard"
    app = sdcard / "a"
    app.mkdir(parents=True)
    binary = app / "a.bin"
    run(["ez80asm", str(entry), str(binary)], cwd=work)
    (sdcard / "autoexec.txt").write_bytes(
        b"SET KEYBOARD 1\r\n"
        b"cd a\r\n"
        b"load a.bin\r\n"
        b"run\r\n"
    )

    result = app / "area_result.bin"
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
            raise RuntimeError("timed out waiting for area emulator result")
    finally:
        process.terminate()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()

    checks = int.from_bytes(payload[4:6], "little")
    errors = int.from_bytes(payload[6:8], "little")
    case, checkpoint, reason, expected, actual = payload[8:13]
    index = int.from_bytes(payload[13:15], "little")
    if errors:
        case_errors = [
            f"{CASES.get(i + 1, i + 1)}={count}"
            for i, count in enumerate(payload[16:24])
            if count
        ]
        print(
            f"FAIL: {errors} mismatches in {checks} direct-eZ80 checks; "
            f"case={CASES.get(case, case)} checkpoint={checkpoint} "
            f"reason={REASONS.get(reason, reason)} index={index} "
            f"expected={expected:#04x} actual={actual:#04x}"
        )
        if case_errors:
            print("Mismatches by case: " + ", ".join(case_errors))
        return 1

    print(f"PASS: {checks} direct production-area eZ80 checks across 8 cases")
    return 0


if __name__ == "__main__":
    sys.exit(main())
