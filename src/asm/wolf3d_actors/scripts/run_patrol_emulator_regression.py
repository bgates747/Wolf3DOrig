#!/usr/bin/env python3
"""Generate W3PV vectors and run the direct production-patrol eZ80 fixture."""

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
VECTOR_CASE_COUNT = 11
PHASE_COUNT = 6
RESULT_VECTOR_OFFSET = 16
RESULT_PHASE_OFFSET = RESULT_VECTOR_OFFSET + VECTOR_CASE_COUNT
RESULT_TIMING_OFFSET = RESULT_PHASE_OFFSET + PHASE_COUNT
RESULT_SIZE = RESULT_TIMING_OFFSET + 4

PHASES = {
    1: "eleven-case W3PV oracle corpus",
    2: "2,2,3 cadence",
    3: "TryWalk directed edges",
    4: "player-overlap rollback",
    5: "actor door obstruction",
    6: "invalid-state safety",
}

REASONS = {
    1: "vector header",
    2: "actor presence/list",
    3: "actor record",
    4: "door record",
    5: "actor dirty state",
    6: "door dirty state",
    7: "actor clock phase",
    8: "door clock phase",
    9: "actorat occupancy",
    10: "door timer",
    11: "scalar result",
    12: "cached tile",
    13: "leg distance",
    14: "physical pose",
    15: "door action",
    16: "fault containment",
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
            "missing patrol regression dependency: " + ", ".join(map(str, missing))
        )

    # ez80asm retains DOS-era path-length restrictions. Put the entry, every
    # production include symlink, generated oracle include, and output in one
    # disposable short directory and assemble there.
    work = Path(tempfile.mkdtemp(prefix="p"))
    atexit.register(shutil.rmtree, work, ignore_errors=True)
    for include in STAGED_SRC.glob("*.inc"):
        (work / include.name).symlink_to(include.resolve())

    vectors = work / "patrol_vectors.inc"
    run(
        [
            sys.executable,
            str(HERE / "generate_patrol_vectors.py"),
            "--fixture",
            str(STAGED_SRC / "wolf3d_fixture.inc"),
            "--out",
            str(vectors),
        ]
    )

    entry = work / "p.asm"
    shutil.copyfile(HERE.parent / "src/patrol_regression.asm", entry)
    sdcard = work / "sdcard"
    app = sdcard / "p"
    app.mkdir(parents=True)
    binary = app / "p.bin"
    run(["ez80asm", str(entry), str(binary)], cwd=work)
    (sdcard / "autoexec.txt").write_bytes(
        b"SET KEYBOARD 1\r\n"
        b"cd p\r\n"
        b"load p.bin\r\n"
        b"run\r\n"
    )

    result = app / "patrol_result.bin"
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
                if len(payload) == RESULT_SIZE and payload[:4] == b"W3P1":
                    break
            time.sleep(0.05)
        else:
            raise RuntimeError("timed out waiting for patrol emulator result")
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
        vector_errors = [
            f"case {index + 1}={count}"
            for index, count in enumerate(
                payload[RESULT_VECTOR_OFFSET:RESULT_PHASE_OFFSET]
            )
            if count
        ]
        print(
            f"FAIL: {errors} mismatches in {checks} direct-eZ80 checks; "
            f"phase={PHASES.get(phase, phase)} reason={REASONS.get(reason, reason)} "
            f"case/detail={detail} expected={expected:#04x} actual={actual:#04x}"
        )
        if vector_errors:
            print("W3PV mismatches by case: " + ", ".join(vector_errors))
        phase_errors = [
            f"{PHASES.get(index + 1, index + 1)}={count}"
            for index, count in enumerate(
                payload[RESULT_PHASE_OFFSET:RESULT_TIMING_OFFSET]
            )
            if count
        ]
        if phase_errors:
            print("Mismatches by phase: " + ", ".join(phase_errors))
        return 1
    milliseconds = int.from_bytes(
        payload[RESULT_TIMING_OFFSET:RESULT_TIMING_OFFSET + 3], "little"
    )
    print(f"PASS: {checks} direct production-patrol eZ80 checks")
    if milliseconds:
        print(
            "PRT1 timing: real E1L1 slot-11/door-8 route, "
            f"92 fixed frames in {milliseconds} ms "
            f"({milliseconds / 92:.3f} ms/frame)"
        )
    else:
        print("PRT1 timing: 92-frame E1L1 route below 1 ms resolution")
    return 0


if __name__ == "__main__":
    sys.exit(main())
