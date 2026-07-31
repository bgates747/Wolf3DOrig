#!/usr/bin/env python3
"""Assemble and run the direct production-awareness eZ80 regression."""

from __future__ import annotations

import argparse
import atexit
import hashlib
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
TIMING_ITERATIONS = 10_000

PHASES = {
    1: "RNG continuation/wrap",
    2: "class reaction delays",
    3: "area gates",
    4: "quiet visual paths",
    5: "noise bypass",
    6: "ambush paths",
    7: "2,2,3 countdown",
    8: "FirstSighting effects",
    9: "corrupt-state containment",
    10: "whole-pass noise lifetime",
    11: "quiet visual timing",
}

REASONS = {
    1: "scalar return",
    2: "RNG byte/index",
    3: "reaction temp2",
    4: "actor flags",
    5: "state/ticcount",
    6: "actor speed",
    7: "door-wait distance",
    8: "pose/active preservation",
    9: "fault containment",
    10: "noise lifetime/context",
    11: "2,2,3 clock",
    12: "actor record preservation",
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
            "missing awareness regression dependency: "
            + ", ".join(map(str, missing))
        )

    # ez80asm retains DOS-era path-length restrictions.  Keep the entry,
    # production include symlinks, and output in one disposable short path.
    work = Path(tempfile.mkdtemp(prefix="w"))
    atexit.register(shutil.rmtree, work, ignore_errors=True)
    for include in STAGED_SRC.glob("*.inc"):
        (work / include.name).symlink_to(include.resolve())

    entry = work / "w.asm"
    shutil.copyfile(HERE.parent / "src/awareness_regression.asm", entry)
    sdcard = work / "sdcard"
    app = sdcard / "w"
    app.mkdir(parents=True)
    binary = app / "w.bin"
    run(["ez80asm", str(entry), str(binary)], cwd=work)
    digest = hashlib.sha256(binary.read_bytes()).hexdigest()
    print(f"binary: {binary.stat().st_size} bytes, sha256={digest}")
    (sdcard / "autoexec.txt").write_bytes(
        b"SET KEYBOARD 1\r\n"
        b"cd w\r\n"
        b"load w.bin\r\n"
        b"run\r\n"
    )

    result = app / "aware_result.bin"
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
                if len(payload) == RESULT_SIZE and payload[:4] == b"W3AW":
                    break
            time.sleep(0.05)
        else:
            observed = f" ({len(payload)} bytes, prefix={payload[:4]!r})" if payload else ""
            raise RuntimeError(
                "timed out waiting for awareness emulator result" + observed
            )
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
    index = int.from_bytes(payload[13:15], "little")
    if errors:
        phase_errors = [
            f"{PHASES.get(i + 1, i + 1)}={count}"
            for i, count in enumerate(payload[16:27])
            if count
        ]
        print(
            f"FAIL: {errors} mismatches in {checks} direct-eZ80 checks; "
            f"phase={PHASES.get(phase, phase)} detail={detail} "
            f"reason={REASONS.get(reason, reason)} index={index} "
            f"expected={expected:#04x} actual={actual:#04x}"
        )
        if phase_errors:
            print("Mismatches by phase: " + ", ".join(phase_errors))
        return 1

    milliseconds = int.from_bytes(payload[27:30], "little")
    print(f"PASS: {checks} direct production-awareness eZ80 checks across 11 cases")
    if milliseconds:
        print(
            f"PRT1 timing: {TIMING_ITERATIONS:,} connected quiet visual "
            f"acquisitions in {milliseconds} ms "
            f"({milliseconds / TIMING_ITERATIONS:.4f} ms/call)"
        )
    else:
        print(
            f"PRT1 timing: {TIMING_ITERATIONS:,} connected quiet visual "
            "acquisitions below 1 ms resolution"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
