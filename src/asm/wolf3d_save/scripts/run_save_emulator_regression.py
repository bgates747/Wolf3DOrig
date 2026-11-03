#!/usr/bin/env python3
"""Assemble and run the direct production save-image eZ80 regression."""

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
FIXTURE = STAGED_ROOT / "src/asm/wolf3d_save/src/save_regression.asm"
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
ASSEMBLER = os.environ.get("W3D_ASSEMBLER") or shutil.which("ez80asm") or str(
    STAGED_ROOT / "src/asm/wolf3d/tgt/.tools/ez80asm"
)
RESULT_SIZE = 16
SAVE_CASE_COUNT = 10

REASONS = {
    1: "validation result",
    2: "health round trip",
    3: "score round trip",
    4: "tilemap round trip",
    5: "area-map round trip",
    6: "runtime pointer rebuild",
    7: "actorat rebuild",
    8: "transactional rejection",
    9: "slot file I/O",
    10: "slot metadata",
    11: "level-entry score checkpoint",
}


def run(command: list[str], *, cwd: Path | None = None) -> None:
    print("+", " ".join(command))
    subprocess.run(command, check=True, cwd=cwd)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timeout", type=float, default=30.0)
    args = parser.parse_args()

    for dependency in (PRODUCTION_SRC, FIXTURE, FAB, MOS, VDP, Path(ASSEMBLER)):
        if not dependency.exists():
            raise FileNotFoundError(
                f"missing save-image regression dependency: {dependency}"
            )

    work = Path(tempfile.mkdtemp(prefix="ws"))
    atexit.register(shutil.rmtree, work, ignore_errors=True)
    build_src = work / "src"
    shutil.copytree(PRODUCTION_SRC, build_src)
    entry = build_src / "s.asm"
    shutil.copyfile(FIXTURE, entry)

    sdcard = work / "sd"
    app = sdcard / "s"
    app.mkdir(parents=True)
    binary = app / "s.bin"
    run([ASSEMBLER, entry.name, str(binary)], cwd=build_src)
    (sdcard / "autoexec.txt").write_bytes(
        b"SET KEYBOARD 1\r\ncd s\r\nload s.bin\r\nrun\r\n"
    )

    result = app / "save_result.bin"
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
        if environment.get("LD_LIBRARY_PATH")
        else ""
    )
    emulator = [
        str(FAB.resolve()),
        "--renderer",
        "sw",
        "--firmware",
        FIRMWARE,
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
                if (
                    len(payload) == RESULT_SIZE
                    and payload[:4] == b"W3S1"
                    and payload[10] == 1
                ):
                    break
            time.sleep(0.05)
        else:
            detail = ""
            if len(payload) == RESULT_SIZE and payload[:4] == b"W3S1":
                detail = (
                    f"; completed {payload[4]}/{SAVE_CASE_COUNT} cases"
                    f", progress marker {payload[11]}"
                )
            raise RuntimeError(f"timed out waiting for save-image result{detail}")
    finally:
        process.terminate()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()

    cases, errors, first_case, reason, expected, actual = payload[4:10]
    if errors:
        print(
            f"FAIL: {errors} failures across {cases} save cases; "
            f"first case={first_case} reason={REASONS.get(reason, reason)} "
            f"expected={expected:#04x} actual={actual:#04x}"
        )
        return 1
    print(f"PASS: {cases}/{cases} transactional save-image cases")
    return 0


if __name__ == "__main__":
    sys.exit(main())
