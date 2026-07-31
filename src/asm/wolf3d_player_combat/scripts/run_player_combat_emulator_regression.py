#!/usr/bin/env python3
"""Assemble and run the direct production player-combat eZ80 regression."""

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

PHASES = {
    1: "pain/death state table",
    2: "pistol attack timeline",
    3: "target boundaries",
    4: "damage/death/drops",
    5: "weapon selection/input",
}

REASONS = {
    1: "scalar return",
    2: "state/ticcount",
    3: "RNG index",
    4: "target selection",
    5: "inventory/HUD",
    6: "runtime drop",
    7: "state-table bytes",
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
            "missing player-combat regression dependency: "
            + ", ".join(map(str, missing))
        )

    # ez80asm retains DOS-era path-length restrictions.  Keep every include
    # and output in one disposable short directory.
    work = Path(tempfile.mkdtemp(prefix="w"))
    atexit.register(shutil.rmtree, work, ignore_errors=True)
    for include in STAGED_SRC.glob("*.inc"):
        (work / include.name).symlink_to(include.resolve())

    entry = work / "w.asm"
    shutil.copyfile(HERE.parent / "src/player_combat_regression.asm", entry)
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

    result = app / "player_combat_result.bin"
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
                if len(payload) == RESULT_SIZE and payload[:4] == b"W3PC":
                    break
            time.sleep(0.05)
        else:
            observed = (
                f" ({len(payload)} bytes, prefix={payload[:4]!r})" if payload else ""
            )
            raise RuntimeError(
                "timed out waiting for player-combat emulator result" + observed
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
    phase, reason, expected, actual, schema = payload[8:13]
    if schema != 1:
        raise RuntimeError(f"unsupported player-combat mailbox schema {schema}")
    if errors:
        print(
            f"FAIL: {errors} mismatches in {checks} direct-eZ80 checks; "
            f"phase={PHASES.get(phase, phase)} "
            f"reason={REASONS.get(reason, reason)} "
            f"expected={expected:#04x} actual={actual:#04x}"
        )
        return 1

    print(
        f"PASS: {checks} direct production player-combat eZ80 checks "
        f"across {len(PHASES)} phases"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
