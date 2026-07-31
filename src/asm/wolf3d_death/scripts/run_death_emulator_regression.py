#!/usr/bin/env python3
"""Assemble and run the direct production death-state eZ80 regression."""

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
FIXTURE = STAGED_ROOT / "src/asm/wolf3d_death/src/death_regression.asm"
FAB = RUNTIME_ROOT / "agonport/emulator/fab-agon-emulator"
MOS = RUNTIME_ROOT / "agonport/emulator/mos_console8.bin"
VDP = RUNTIME_ROOT / "agonport/emulator/vdp_stock.so"

RESULT_SIZE = 16
RESULT_SCHEMA = 1
EXPECTED_CHECKS = 182
LOG_TAIL_BYTES = 16 * 1024

CASE_NAMES = {
    1: "callback mailbox routing",
    2: "render ownership and purpose",
    3: "fizzle token and sequence",
    4: "killer bearing",
    5: "shortest turn and cadence",
    6: "target-sync and fizzle transition",
    7: "acknowledgment, lives, and respawn",
    8: "production reseed and submission",
}


def run(command: list[str], *, cwd: Path | None = None) -> None:
    print("+", " ".join(command))
    subprocess.run(command, check=True, cwd=cwd)


def read_log_tail(path: Path) -> str:
    """Return a bounded, decode-safe subprocess log tail."""
    try:
        with path.open("rb") as stream:
            stream.seek(0, os.SEEK_END)
            size = stream.tell()
            truncated = size > LOG_TAIL_BYTES
            stream.seek(max(0, size - LOG_TAIL_BYTES))
            payload = stream.read()
    except OSError as exc:
        return f"<unable to read {path.name}: {exc}>"
    decoded = payload.decode("utf-8", errors="replace").strip()
    if truncated:
        decoded = "<earlier output omitted>\n" + decoded
    return decoded


def emulator_failure_message(
    summary: str,
    *,
    stdout_log: Path,
    stderr_log: Path,
    mailbox: bytes,
) -> str:
    sections = [summary]
    if mailbox:
        sections.append(
            f"last mailbox ({len(mailbox)} bytes): {mailbox.hex(' ')}"
        )
    stdout_tail = read_log_tail(stdout_log)
    stderr_tail = read_log_tail(stderr_log)
    if stdout_tail:
        sections.append("emulator stdout tail:\n" + stdout_tail)
    if stderr_tail:
        sections.append("emulator stderr tail:\n" + stderr_tail)
    if not stdout_tail and not stderr_tail:
        sections.append("emulator produced no stdout/stderr diagnostics")
    return "\n".join(sections)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--timeout", type=float, default=30.0)
    args = parser.parse_args()

    dependencies = [PRODUCTION_SRC, FIXTURE, FAB, MOS, VDP]
    production_includes = sorted(PRODUCTION_SRC.glob("*.inc"))
    dependencies.extend(production_includes)
    missing = [path for path in dependencies if not path.exists()]
    if missing:
        raise FileNotFoundError(
            "missing death regression dependency: " + ", ".join(map(str, missing))
        )

    # ez80asm retains DOS-era filename/path limits. Keep the entry, includes,
    # binary, and MOS working directory deliberately short and isolated.
    work = Path(tempfile.mkdtemp(prefix="wd"))
    atexit.register(shutil.rmtree, work, ignore_errors=True)
    build = work / "s"
    build.mkdir()
    for include in production_includes:
        shutil.copyfile(include, build / include.name)
    entry = build / "d.asm"
    shutil.copyfile(FIXTURE, entry)

    sdcard = work / "sd"
    app = sdcard / "d"
    app.mkdir(parents=True)
    binary = app / "d.bin"
    run(["ez80asm", entry.name, str(binary)], cwd=build)
    (sdcard / "autoexec.txt").write_bytes(
        b"SET KEYBOARD 1\r\n"
        b"cd d\r\n"
        b"load d.bin\r\n"
        b"run\r\n"
    )

    result = app / "death_result.bin"
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
    stdout_log = work / "emulator.stdout.log"
    stderr_log = work / "emulator.stderr.log"
    payload = b""
    failure: str | None = None
    with stdout_log.open("wb") as stdout_stream, stderr_log.open("wb") as stderr_stream:
        process = subprocess.Popen(
            emulator,
            cwd=work,
            env=environment,
            stdout=stdout_stream,
            stderr=stderr_stream,
        )
        try:
            deadline = time.monotonic() + args.timeout
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    failure = f"emulator exited with {process.returncode}"
                    break
                if result.exists():
                    payload = result.read_bytes()
                    if len(payload) == RESULT_SIZE and payload[:4] == b"W3D1":
                        break
                time.sleep(0.05)
            else:
                failure = "timed out waiting for death emulator result"
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()

    if failure is not None:
        raise RuntimeError(
            emulator_failure_message(
                failure,
                stdout_log=stdout_log,
                stderr_log=stderr_log,
                mailbox=payload,
            )
        )

    checks, errors, first_case, reason, expected, actual = payload[4:10]
    if payload[15] != RESULT_SCHEMA:
        raise RuntimeError(f"unsupported death mailbox schema {payload[15]}")
    if errors:
        case_name = CASE_NAMES.get(first_case, f"case {first_case}")
        print(
            f"FAIL: {errors} failed death checks in {checks}; "
            f"first={case_name}, reason={reason}, "
            f"expected={expected:#04x}, actual={actual:#04x}"
        )
        return 1
    if checks != EXPECTED_CHECKS:
        print(f"FAIL: expected {EXPECTED_CHECKS} checks, fixture reported {checks}")
        return 1
    print(f"PASS: {checks}/{checks} direct production death-state eZ80 checks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
