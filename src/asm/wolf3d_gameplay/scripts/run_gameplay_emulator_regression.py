#!/usr/bin/env python3
"""Build and run the eZ80 gameplay regression in an isolated Fab profile."""

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
_installed_root = (
    Path(__file__).resolve().parents[4]
    if len(Path(__file__).resolve().parents) > 4
    else Path.cwd()
)
STAGED_ROOT = (
    Path(_root_override)
    if _root_override
    else _installed_root
)
RUNTIME_ROOT = Path(os.environ.get("W3D_RUNTIME_ROOT", _installed_root))
STAGED_SRC = STAGED_ROOT / "src/asm/wolf3d/src"
PYTHON = Path(sys.executable)
FAB = RUNTIME_ROOT / "agonport/emulator/fab-agon-emulator"
MOS = RUNTIME_ROOT / "agonport/emulator/mos_console8.bin"
VDP = RUNTIME_ROOT / "agonport/emulator/vdp_stock.so"
RESULT_SIZE = 32


def run(command: list[str], *, cwd: Path | None = None) -> None:
    print("+", " ".join(command))
    subprocess.run(command, check=True, cwd=cwd)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--random-cases", type=int, default=10_000)
    parser.add_argument("--timeout", type=float, default=90.0)
    parser.add_argument("--include-zero-delta", action="store_true")
    args = parser.parse_args()

    # ez80asm retains a short DOS-era output-filename limit.
    # Keep the complete output path below ez80asm's legacy filename limit.
    work = Path(tempfile.mkdtemp(prefix="g"))
    atexit.register(shutil.rmtree, work, ignore_errors=True)
    sdcard = work / "sdcard"
    app = sdcard / "g"
    app.mkdir(parents=True)

    vectors = app / "clip_vectors.bin"
    command = [
        str(PYTHON),
        str(HERE / "generate_clip_vectors.py"),
        "--random-cases",
        str(args.random_cases),
        "--output",
        str(vectors),
    ]
    if args.include_zero_delta:
        command.append("--include-zero-delta")
    run(command)

    # ez80asm also applies its legacy limit to the source pathname. Stage the
    # durable entry file under a short name; its includes still resolve from
    # STAGED_SRC, which remains the assembler working directory.
    entry = work / "g.asm"
    shutil.copyfile(
        STAGED_ROOT / "src/asm/wolf3d_gameplay/src/gameplay_regression.asm",
        entry,
    )
    binary = app / "g.bin"
    run(
        ["ez80asm", str(entry), str(binary)],
        cwd=STAGED_SRC,
    )
    (sdcard / "autoexec.txt").write_bytes(
        b"SET KEYBOARD 1\r\n"
        b"cd g\r\n"
        b"load g.bin\r\n"
        b"run\r\n"
    )

    result = app / "gameplay_result.bin"
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
    try:
        deadline = time.monotonic() + args.timeout
        payload = b""
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError(f"emulator exited with {process.returncode}")
            if result.exists():
                payload = result.read_bytes()
                if len(payload) == RESULT_SIZE and payload[:4] == b"W3G1":
                    break
            time.sleep(0.05)
        else:
            raise RuntimeError("timed out waiting for emulator result")
    finally:
        process.terminate()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()

    records = int.from_bytes(payload[4:7], "little")
    errors = int.from_bytes(payload[7:10], "little")
    first_index = int.from_bytes(payload[10:13], "little")
    reason = payload[13]
    expected_a, actual_a = payload[14:16]
    sequence = int.from_bytes(payload[16:20], "little")
    actual_x = int.from_bytes(payload[20:24], "little", signed=True)
    actual_y = int.from_bytes(payload[24:28], "little", signed=True)
    if errors:
        reasons = {1: "A result", 2: "dirty flag", 3: "pose"}
        print(
            f"FAIL: {errors} errors in {records} records; first index={first_index} "
            f"sequence={sequence} reason={reasons.get(reason, reason)} "
            f"expectedA={expected_a} actualA={actual_a} "
            f"actualPose=({actual_x:#x},{actual_y:#x})"
        )
        return 1
    print(f"PASS: {records} eZ80 ClipMove records in isolated emulator")
    return 0


if __name__ == "__main__":
    sys.exit(main())
