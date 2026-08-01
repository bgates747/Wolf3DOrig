#!/usr/bin/env python3
"""Assemble and run the direct production positional-audio regression."""

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

PHASES = {1: "actor entry", 2: "tile entry"}
REASONS = {
    1: "request count",
    2: "sound id",
    3: "gain",
    4: "positioned flag",
    5: "relative Q8",
    6: "table row/column",
    7: "IX preservation",
}


def run(command: list[str], *, cwd: Path | None = None) -> None:
    print("+", " ".join(command))
    subprocess.run(command, check=True, cwd=cwd)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--timeout", type=float, default=60.0)
    args = parser.parse_args()

    dependencies = (STAGED_SRC, FAB, MOS, VDP)
    missing = [path for path in dependencies if not path.exists()]
    if missing:
        raise FileNotFoundError(
            "missing spatial regression dependency: " + ", ".join(map(str, missing))
        )

    # ez80asm retains DOS-era path-length constraints. Stage every production
    # include and the generated vector include in one disposable short path.
    work = Path(tempfile.mkdtemp(prefix="w"))
    atexit.register(shutil.rmtree, work, ignore_errors=True)
    for include in STAGED_SRC.glob("*.inc"):
        (work / include.name).symlink_to(include.resolve())
    (work / "spatial_vectors.inc").symlink_to(
        (HERE.parent / "src/spatial_vectors.inc").resolve()
    )

    entry = work / "w.asm"
    shutil.copyfile(HERE.parent / "src/spatial_regression.asm", entry)
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

    result = app / "spatial_result.bin"
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
                if len(payload) == RESULT_SIZE and payload[:4] == b"W3SP":
                    break
            time.sleep(0.05)
        else:
            observed = (
                f" ({len(payload)} bytes, prefix={payload[:4]!r})" if payload else ""
            )
            raise RuntimeError("timed out waiting for spatial emulator result" + observed)
    finally:
        process.terminate()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()

    if payload[22] != 1:
        raise RuntimeError(f"unsupported spatial mailbox schema {payload[22]}")
    checks = int.from_bytes(payload[4:6], "little")
    errors = int.from_bytes(payload[6:8], "little")
    phase, reason, expected, actual = payload[8:12]
    vector = int.from_bytes(payload[12:14], "little")
    phase_errors = payload[14:16]
    vector_count = int.from_bytes(payload[16:18], "little")
    actor_count = int.from_bytes(payload[18:20], "little")
    tile_count = int.from_bytes(payload[20:22], "little")

    if errors:
        buckets = [
            f"{PHASES.get(index + 1, index + 1)}={count}"
            for index, count in enumerate(phase_errors)
            if count
        ]
        print(
            f"FAIL: {errors} mismatches in {checks} direct-eZ80 checks; "
            f"phase={PHASES.get(phase, phase)} reason={REASONS.get(reason, reason)} "
            f"vector={vector} expected={expected:#04x} actual={actual:#04x}"
        )
        if buckets:
            print("Mismatches by phase: " + ", ".join(buckets))
        return 1

    print(
        f"PASS: {checks} direct production-spatial eZ80 checks across "
        f"{vector_count} vectors ({actor_count} actor, {tile_count} tile)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
