#!/usr/bin/env python3
"""Assemble and run the direct production Wolf3D audio eZ80 regression."""

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
STAGED_FIXTURE = STAGED_ROOT / "src/asm/wolf3d_audio/src/audio_regression.asm"
FAB = RUNTIME_ROOT / "agonport/emulator/fab-agon-emulator"
MOS = RUNTIME_ROOT / "agonport/emulator/mos_console8.bin"
VDP = RUNTIME_ROOT / "agonport/emulator/vdp_stock.so"
RESULT_SIZE = 32

PHASES = {
    1: "stable IDs and loaded state",
    2: "priority batch",
    3: "catch-up suppression",
    4: "buffered runtime wire",
    5: "direct fallback wire",
    6: "command procedure installation",
    7: "shutdown",
    8: "PRT1 dispatch timing",
}

REASONS = {
    1: "scalar",
    2: "stable mapping",
    3: "queue ordering",
    4: "diagnostic counter",
    5: "wire bytes",
    6: "carry contract",
    7: "loaded state",
}


def run(command: list[str], *, cwd: Path | None = None) -> None:
    print("+", " ".join(command))
    subprocess.run(command, check=True, cwd=cwd)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--timeout", type=float, default=60.0)
    args = parser.parse_args()

    dependencies = (STAGED_SRC, STAGED_FIXTURE, FAB, MOS, VDP)
    missing = [path for path in dependencies if not path.exists()]
    if missing:
        raise FileNotFoundError(
            "missing audio regression dependency: " + ", ".join(map(str, missing))
        )

    # ez80asm retains DOS-era path-length restrictions. Keep includes and the
    # output inside one disposable short directory.
    work = Path(tempfile.mkdtemp(prefix="w"))
    atexit.register(shutil.rmtree, work, ignore_errors=True)
    for include in STAGED_SRC.glob("*.inc"):
        (work / include.name).symlink_to(include.resolve())
    entry = work / "w.asm"
    shutil.copyfile(STAGED_FIXTURE, entry)

    sdcard = work / "sdcard"
    app = sdcard / "w"
    app.mkdir(parents=True)
    binary = app / "w.bin"
    run(["ez80asm", str(entry), str(binary)], cwd=work)
    digest = hashlib.sha256(binary.read_bytes()).hexdigest()
    print(f"binary: {binary.stat().st_size} bytes, sha256={digest}")
    (sdcard / "autoexec.txt").write_bytes(
        b"SET KEYBOARD 1\r\ncd w\r\nload w.bin\r\nrun\r\n"
    )

    result = app / "audio_result.bin"
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
                if len(payload) == RESULT_SIZE and payload[:4] == b"W3AU":
                    break
            time.sleep(0.05)
        else:
            observed = (
                f" ({len(payload)} bytes, prefix={payload[:4]!r})" if payload else ""
            )
            raise RuntimeError("timed out waiting for audio emulator result" + observed)
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
    if schema != 2:
        raise RuntimeError(f"unsupported audio mailbox schema {schema}")
    if errors:
        print(
            f"FAIL: {errors} mismatches in {checks} direct-eZ80 checks; "
            f"phase={PHASES.get(phase, phase)} "
            f"reason={REASONS.get(reason, reason)} "
            f"expected={expected:#04x} actual={actual:#04x}"
        )
        return 1

    print(
        f"PASS: {checks} direct production audio checks across "
        f"{len(PHASES)} phases"
    )

    request_total = int.from_bytes(payload[13:16], "little")
    request_baseline = int.from_bytes(payload[16:19], "little")
    flush_total = int.from_bytes(payload[19:22], "little")
    flush_baseline = int.from_bytes(payload[22:25], "little")
    iterations = int.from_bytes(payload[25:27], "little")
    timer_hz = int.from_bytes(payload[27:29], "little")
    timing_flags = payload[29]
    if not iterations or not timer_hz or not timing_flags & 1:
        raise RuntimeError(
            "invalid audio timing metadata: "
            f"iterations={iterations} timer_hz={timer_hz} flags={timing_flags:#04x}"
        )

    def report_timing(label: str, total: int, baseline: int) -> None:
        # Independent 1 kHz stopwatch runs can differ by one boundary tick.
        # Clamp that quantization case while retaining every raw count.
        backend_ticks = max(0, total - baseline)
        total_ms = total * 1000.0 / timer_hz
        baseline_ms = baseline * 1000.0 / timer_hz
        backend_ms = backend_ticks * 1000.0 / timer_hz
        average_us = backend_ticks * 1_000_000.0 / timer_hz / iterations
        print(
            f"PRT1 timing: {iterations:,} {label}: total={total} ticks "
            f"({total_ms:.3f} ms), matched baseline={baseline} ticks "
            f"({baseline_ms:.3f} ms), backend={backend_ticks} ticks "
            f"({backend_ms:.3f} ms, {average_us:.3f} us/call)"
        )
        if total < baseline:
            print("  note: backend delta was below the independent 1 ms timer resolution")

    report_timing(
        "loaded active-batch request calls",
        request_total,
        request_baseline,
    )
    report_timing(
        "one-event buffered capture flushes",
        flush_total,
        flush_baseline,
    )
    print("Timing capture excludes UART transmission and VDP/audio-device latency.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
