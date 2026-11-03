#!/usr/bin/env python3
"""Assemble and run the direct production-shell eZ80 semantic regression."""

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
if _root_override:
    STAGED_ROOT = Path(_root_override)
    _installed_root = STAGED_ROOT
else:
    _installed_root = Path(__file__).resolve().parents[4]
    STAGED_ROOT = _installed_root
RUNTIME_ROOT = Path(os.environ.get("W3D_RUNTIME_ROOT", _installed_root))
PRODUCTION_SRC = STAGED_ROOT / "src/asm/wolf3d/src"
FIXTURE = STAGED_ROOT / "src/asm/wolf3d_shell/src/shell_regression.asm"
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
    12: "application-global exit latch",
    13: "victory presentation handoff",
    14: "high-score handoff/view",
    15: "End Game confirmation plot sequence",
    16: "sound-effects preference",
    17: "music preference",
    18: "original music assignment",
    19: "remembered quick slot",
    20: "shell sound count",
    21: "shell logical sound id",
    22: "help container load count",
    23: "help buffer clear count",
}

STAGES = {
    1: "input actions",
    2: "main-menu results",
    3: "episode selection",
    4: "difficulty selection",
    5: "lifecycle entries",
    6: "pause menu",
    7: "control pages",
    8: "canonical help article",
    9: "attract timing",
    10: "draw contracts",
    11: "F1-F10 gameplay quick keys",
    12: "original control-panel sounds",
    109: "main-menu Quit",
    110: "main-menu Escape",
    111: "main-menu New Game",
    136: "main-menu View Scores",
    147: "main-menu Load Game",
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
            raise FileNotFoundError(f"missing shell regression dependency: {dependency}")
    if args.prebuilt and not args.prebuilt.is_file():
        raise FileNotFoundError(f"missing prebuilt shell fixture: {args.prebuilt}")

    work = Path(tempfile.mkdtemp(prefix="ws"))
    atexit.register(shutil.rmtree, work, ignore_errors=True)
    sdcard = work / "sd"
    app = sdcard / "s"
    app.mkdir(parents=True)
    binary = app / "s.bin"
    if args.prebuilt:
        shutil.copyfile(args.prebuilt, binary)
        print("+ prebuilt", args.prebuilt, "->", binary)
    else:
        # ez80asm retains DOS-era input and output path limits. Keep the entry
        # basename short while resolving production bare includes from an isolated
        # copy. This also keeps concurrent production assemblies race-free.
        build_src = work / "src"
        shutil.copytree(PRODUCTION_SRC, build_src)
        entry = build_src / "s.asm"
        shutil.copyfile(FIXTURE, entry)
        run([str(ASSEMBLER), entry.name, str(binary)], cwd=build_src)
    digest = hashlib.sha256(binary.read_bytes()).hexdigest()
    print(f"binary: {binary.stat().st_size} bytes, sha256={digest}")
    (sdcard / "autoexec.txt").write_bytes(
        b"SET KEYBOARD 1\r\ncd s\r\nload s.bin\r\nrun\r\n"
    )

    result = app / "shell_result.bin"
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
                    and payload[:4] == b"W3S2"
                    and payload[13] == 1
                ):
                    break
            time.sleep(0.05)
        else:
            detail = ""
            if len(payload) == RESULT_SIZE and payload[:4] == b"W3S2":
                detail = f"; stalled in {STAGES.get(payload[12], payload[12])}"
            raise RuntimeError(f"timed out waiting for shell regression result{detail}")
    finally:
        process.terminate()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()

    checks = int.from_bytes(payload[4:6], "little")
    errors = int.from_bytes(payload[6:8], "little")
    first_case, reason, expected, actual = payload[8:12]
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
