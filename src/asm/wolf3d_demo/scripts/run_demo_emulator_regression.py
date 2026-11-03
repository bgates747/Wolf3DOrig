#!/usr/bin/env python3
"""Assemble and run the direct production recorded-demo eZ80 regression."""

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
FIXTURE = STAGED_ROOT / "src/asm/wolf3d_demo/src/demo_regression.asm"
FAB = Path(os.environ.get(
    "W3D_EMULATOR", RUNTIME_ROOT / "agonport/emulator/fab-agon-emulator"
))
MOS = Path(os.environ.get(
    "W3D_MOS", RUNTIME_ROOT / "agonport/emulator/mos_console8.bin"
))
VDP = Path(os.environ.get(
    "W3D_VDP", RUNTIME_ROOT / "agonport/emulator/vdp_stock.so"
))
FIRMWARE = os.environ.get("W3D_FIRMWARE", "platform")
ASSEMBLER = os.environ.get("W3D_ASSEMBLER", "ez80asm")
RESULT_SIZE = 16

REASONS = {
    1: "stream selection",
    2: "stream level",
    3: "demo difficulty",
    4: "demo active flag",
    5: "decoded controls",
    6: "rational cadence",
    7: "stream cursor",
    8: "finished flag",
    9: "application exit latch",
}

STAGES = {
    1: "canonical stream selection",
    2: "button/control decode",
    3: "70/120 rational cadence",
    4: "terminal and local abort",
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
            raise FileNotFoundError(f"missing demo regression dependency: {dependency}")

    work = Path(tempfile.mkdtemp(prefix="wd"))
    atexit.register(shutil.rmtree, work, ignore_errors=True)
    sdcard = work / "sd"
    app = sdcard / "d"
    app.mkdir(parents=True)
    binary = app / "d.bin"
    build_src = work / "src"
    shutil.copytree(PRODUCTION_SRC, build_src)
    entry = build_src / "d.asm"
    shutil.copyfile(FIXTURE, entry)
    run([ASSEMBLER, entry.name, str(binary)], cwd=build_src)
    (sdcard / "autoexec.txt").write_bytes(
        b"SET KEYBOARD 1\r\ncd d\r\nload d.bin\r\nrun\r\n"
    )

    result = app / "demo_result.bin"
    environment = os.environ.copy()
    artifacts = Path(
        environment.setdefault("AGON_FLEXE_ARTIFACTS", str(work / "flexe-artifacts"))
    )
    artifacts.mkdir(parents=True, exist_ok=True)
    environment["SDL_VIDEODRIVER"] = "dummy"
    environment["SDL_AUDIODRIVER"] = "dummy"
    local_lib = str(Path.home() / ".local/lib")
    environment["LD_LIBRARY_PATH"] = local_lib + (
        ":" + environment["LD_LIBRARY_PATH"]
        if environment.get("LD_LIBRARY_PATH") else ""
    )
    emulator = [
        str(FAB.resolve()), "--renderer", "sw", "--firmware", FIRMWARE,
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
                if (
                    len(payload) == RESULT_SIZE
                    and payload[:4] == b"W3D2"
                    and payload[11] == 1
                ):
                    break
            time.sleep(0.05)
        else:
            detail = ""
            if len(payload) == RESULT_SIZE and payload[:4] == b"W3D2":
                detail = f"; stalled in {STAGES.get(payload[10], payload[10])}"
            raise RuntimeError(f"timed out waiting for demo regression result{detail}")
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
            f"FAIL: {errors} failures in {checks} demo checks; "
            f"first case={first_case} reason={REASONS.get(reason, reason)} "
            f"expected={expected:#04x} actual={actual:#04x}"
        )
        return 1
    print(f"PASS: {checks}/{checks} direct production-demo eZ80 checks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
