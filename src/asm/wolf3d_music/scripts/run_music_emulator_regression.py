#!/usr/bin/env python3
"""Assemble and run the direct production IMF-music eZ80 regression."""

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


root_override = os.environ.get("W3D_STAGED_ROOT")
installed_root = Path(__file__).resolve().parents[4]
STAGED_ROOT = Path(root_override) if root_override else installed_root
RUNTIME_ROOT = Path(os.environ.get("W3D_RUNTIME_ROOT", installed_root))
PRODUCTION_SRC = STAGED_ROOT / "src/asm/wolf3d/src"
FIXTURE = STAGED_ROOT / "src/asm/wolf3d_music/src/music_regression.asm"
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
ASSEMBLER = Path(
    os.environ.get("W3D_ASSEMBLER")
    or shutil.which("ez80asm")
    or STAGED_ROOT / "src/asm/wolf3d/tgt/.tools/ez80asm"
)
RESULT_SIZE = 16

REASONS = {
    1: "scalar", 2: "OPL frequency", 3: "carrier volume",
    4: "waveform mapping", 5: "VDP wire bytes",
    6: "120 Hz scheduling", 7: "lifecycle",
}
STAGES = {
    1: "frequency/volume/waveform", 2: "voice-start wire",
    3: "scheduler loop", 4: "pause/resume continuity",
    5: "canonical lifecycle",
}


def run(command: list[str], *, cwd: Path | None = None) -> None:
    print("+", " ".join(command))
    subprocess.run(command, check=True, cwd=cwd)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument(
        "--prebuilt",
        type=Path,
        help="use an already assembled fixture (for a cross-architecture emulator host)",
    )
    args = parser.parse_args()
    dependencies = (FAB, MOS, VDP)
    if not args.prebuilt:
        dependencies = (PRODUCTION_SRC, FIXTURE, ASSEMBLER, *dependencies)
    for dependency in dependencies:
        if not dependency.exists():
            raise FileNotFoundError(f"missing music regression dependency: {dependency}")
    if args.prebuilt and not args.prebuilt.is_file():
        raise FileNotFoundError(f"missing prebuilt music fixture: {args.prebuilt}")

    work = Path(tempfile.mkdtemp(prefix="wm"))
    atexit.register(shutil.rmtree, work, ignore_errors=True)
    sdcard = work / "sd"
    app = sdcard / "m"
    app.mkdir(parents=True)
    binary = app / "m.bin"
    if args.prebuilt:
        shutil.copyfile(args.prebuilt, binary)
        print("+ prebuilt", args.prebuilt, "->", binary)
    else:
        build_src = work / "src"
        shutil.copytree(PRODUCTION_SRC, build_src)
        entry = build_src / "m.asm"
        shutil.copyfile(FIXTURE, entry)
        run([str(ASSEMBLER), entry.name, str(binary)], cwd=build_src)
    digest = hashlib.sha256(binary.read_bytes()).hexdigest()
    print(f"binary: {binary.stat().st_size} bytes, sha256={digest}")
    (sdcard / "autoexec.txt").write_bytes(b"SET KEYBOARD 1\r\ncd m\r\nload m.bin\r\nrun\r\n")

    result = app / "music_result.bin"
    environment = os.environ.copy()
    artifacts = Path(
        environment.setdefault("AGON_FLEXE_ARTIFACTS", str(work / "flexe-artifacts"))
    )
    artifacts.mkdir(parents=True, exist_ok=True)
    environment["SDL_VIDEODRIVER"] = "dummy"
    environment["SDL_AUDIODRIVER"] = "dummy"
    local_lib = str(Path.home() / ".local/lib")
    environment["LD_LIBRARY_PATH"] = local_lib + (
        ":" + environment["LD_LIBRARY_PATH"] if environment.get("LD_LIBRARY_PATH") else ""
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
                if len(payload) == RESULT_SIZE and payload[:4] == b"W3MU" and payload[11] == 1:
                    break
            time.sleep(0.05)
        else:
            detail = f"; stalled in {STAGES.get(payload[10], payload[10])}" if len(payload) == RESULT_SIZE else ""
            raise RuntimeError(f"timed out waiting for music regression result{detail}")
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
            f"FAIL: {errors} failures in {checks} music checks; first case={first_case} "
            f"reason={REASONS.get(reason, reason)} expected={expected:#04x} actual={actual:#04x}"
        )
        return 1
    print(f"PASS: {checks}/{checks} direct production-music eZ80 checks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
