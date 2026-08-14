#!/usr/bin/env python3
"""Assemble and run the direct production-shell eZ80 semantic regression."""

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
FIXTURE = STAGED_ROOT / "src/asm/wolf3d_shell/src/shell_regression.asm"
FAB = RUNTIME_ROOT / "agonport/emulator/fab-agon-emulator"
MOS = RUNTIME_ROOT / "agonport/emulator/mos_console8.bin"
VDP = RUNTIME_ROOT / "agonport/emulator/vdp_stock.so"
RESULT_SIZE = 16

REASONS = {
    1: "normalized input action",
    2: "shell result",
    3: "result flags",
    4: "selected row",
    5: "selected difficulty",
    6: "locked-episode notice",
    7: "visible version",
    8: "plot count",
    9: "plot buffer",
    10: "plot x coordinate",
    11: "plot y coordinate",
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
            raise FileNotFoundError(f"missing shell regression dependency: {dependency}")

    work = Path(tempfile.mkdtemp(prefix="ws"))
    atexit.register(shutil.rmtree, work, ignore_errors=True)
    sdcard = work / "sd"
    app = sdcard / "s"
    app.mkdir(parents=True)
    binary = app / "s.bin"
    # ez80asm retains DOS-era input and output path limits. Keep the entry
    # basename short while resolving production bare includes from an isolated
    # copy. This also keeps concurrent production assemblies race-free.
    build_src = work / "src"
    shutil.copytree(PRODUCTION_SRC, build_src)
    entry = build_src / "s.asm"
    shutil.copyfile(FIXTURE, entry)
    run(["ez80asm", entry.name, str(binary)], cwd=build_src)
    (sdcard / "autoexec.txt").write_bytes(
        b"SET KEYBOARD 1\r\ncd s\r\nload s.bin\r\nrun\r\n"
    )

    result = app / "shell_result.bin"
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
                if len(payload) == RESULT_SIZE and payload[:4] == b"W3S1":
                    break
            time.sleep(0.05)
        else:
            raise RuntimeError("timed out waiting for shell regression result")
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
            f"FAIL: {errors} failures in {checks} shell checks; "
            f"first case={first_case} reason={REASONS.get(reason, reason)} "
            f"expected={expected:#04x} actual={actual:#04x}"
        )
        return 1
    print(f"PASS: {checks}/{checks} direct production-shell eZ80 checks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
