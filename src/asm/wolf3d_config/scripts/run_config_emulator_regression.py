#!/usr/bin/env python3
"""Assemble and run the durable-preference production eZ80 regression."""

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

_root_override = os.environ.get("W3D_STAGED_ROOT")
_runtime_override = os.environ.get("W3D_RUNTIME_ROOT")
_installed_root = (
    Path(_runtime_override)
    if _runtime_override
    else Path(__file__).resolve().parents[4]
)
STAGED_ROOT = Path(_root_override) if _root_override else _installed_root
RUNTIME_ROOT = Path(_runtime_override) if _runtime_override else _installed_root
PRODUCTION_SRC = STAGED_ROOT / "src/asm/wolf3d/src"
FIXTURE = STAGED_ROOT / "src/asm/wolf3d_config/src/config_regression.asm"
_runtime_emulator = (
    RUNTIME_ROOT / "agonport/emulator"
    if (RUNTIME_ROOT / "agonport/emulator").is_dir()
    else RUNTIME_ROOT / "emulator"
)
FAB = _runtime_emulator / "fab-agon-emulator"
MOS = _runtime_emulator / "mos_console8.bin"
VDP = _runtime_emulator / "vdp_stock.so"
ASSEMBLER = os.environ.get("W3D_ASSEMBLER") or shutil.which("ez80asm") or str(
    STAGED_ROOT / "src/asm/wolf3d/tgt/.tools/ez80asm"
)
RESULT_SIZE = 16

REASONS = {1: "decode result", 2: "SFX preference", 3: "music preference", 4: "encoded flags", 5: "file I/O result"}


def run(command: list[str], *, cwd: Path | None = None) -> None:
    print("+", " ".join(map(str, command)))
    subprocess.run(command, check=True, cwd=cwd)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--prebuilt", type=Path)
    parser.add_argument("--assemble-only", type=Path, metavar="OUTPUT")
    args = parser.parse_args()
    dependencies = () if args.assemble_only else (FAB, MOS, VDP)
    if not args.prebuilt:
        dependencies = (PRODUCTION_SRC, FIXTURE, Path(ASSEMBLER), *dependencies)
    for dependency in dependencies:
        if not dependency.exists():
            raise FileNotFoundError(f"missing config regression dependency: {dependency}")

    work = Path(tempfile.mkdtemp(prefix="wc"))
    atexit.register(shutil.rmtree, work, ignore_errors=True)
    sdcard = work / "sd"
    app = sdcard / "c"
    app.mkdir(parents=True)
    binary = app / "c.bin"
    if args.prebuilt:
        shutil.copyfile(args.prebuilt, binary)
    else:
        build_src = work / "src"
        shutil.copytree(PRODUCTION_SRC, build_src)
        entry = build_src / "c.asm"
        shutil.copyfile(FIXTURE, entry)
        run([ASSEMBLER, entry.name, str(binary)], cwd=build_src)
    print(f"binary: {binary.stat().st_size} bytes, sha256={hashlib.sha256(binary.read_bytes()).hexdigest()}")
    if args.assemble_only:
        args.assemble_only.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(binary, args.assemble_only)
        print(f"assembled fixture: {args.assemble_only}")
        return 0
    (sdcard / "autoexec.txt").write_bytes(b"SET KEYBOARD 1\r\ncd c\r\nload c.bin\r\nrun\r\n")

    result = app / "config_result.bin"
    environment = os.environ.copy()
    environment["SDL_VIDEODRIVER"] = "dummy"
    environment["SDL_AUDIODRIVER"] = "dummy"
    local_lib = str(Path.home() / ".local/lib")
    environment["LD_LIBRARY_PATH"] = local_lib + (":" + environment["LD_LIBRARY_PATH"] if environment.get("LD_LIBRARY_PATH") else "")
    emulator = [str(FAB.resolve()), "--renderer", "sw", "--firmware", "console8", "--mos", str(MOS.resolve()), "--vdp", str(VDP.resolve()), "--sdcard", str(sdcard), "--zero"]
    process = subprocess.Popen(emulator, cwd=work, env=environment, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    payload = b""
    try:
        deadline = time.monotonic() + args.timeout
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError(f"emulator exited with {process.returncode}")
            if result.exists():
                payload = result.read_bytes()
                if len(payload) == RESULT_SIZE and payload[:4] == b"W3C1":
                    break
            time.sleep(0.05)
        else:
            raise RuntimeError("timed out waiting for config result")
    finally:
        process.terminate()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()

    checks, errors, first_case, reason, expected, actual = payload[4:10]
    if errors:
        print(f"FAIL: {errors} failures in {checks} checks; case={first_case} reason={REASONS.get(reason, reason)} expected={expected:#04x} actual={actual:#04x}")
        return 1
    print(f"PASS: {checks}/{checks} durable-config direct eZ80 checks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
