#!/usr/bin/env python3
"""Exercise W3L1 fail-closed validation through the production eZ80 loader."""

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


PROJECT_ROOT = Path(__file__).resolve().parents[4]
SOURCE_ROOT = PROJECT_ROOT / "src/asm/wolf3d/src"
GENERATED = PROJECT_ROOT / "agonport/assets/generated/wolf3d"
FAB = PROJECT_ROOT / "agonport/emulator/fab-agon-emulator"
MOS = PROJECT_ROOT / "agonport/emulator/mos_console8.bin"
VDP = PROJECT_ROOT / "agonport/emulator/vdp_wolf3d.so"
MAX_PACKAGE_SIZE = 24 * 1024


def run(command: list[str], *, cwd: Path | None = None) -> None:
    print("+", " ".join(command))
    subprocess.run(command, check=True, cwd=cwd)


def instrument(source: str) -> str:
    source = source.replace(
        "mos_load:        equ 01h\n",
        "mos_load:        equ 01h\nmos_save:        equ 02h\n",
        1,
    )
    # Shell loading and keyboard-driven title presentation now precede normal
    # startup. This regression is deliberately about the production loader,
    # so replace the application-body entry with a tiny direct caller instead
    # of staging unrelated shell assets or coupling to either fatal route.
    marker = "w3d_main_body:\n"
    if source.count(marker) != 1:
        raise RuntimeError("production loader marker changed; update W3L regression")
    source = source.replace(
        marker,
        marker + "    jp w3l_regression_run\n",
        1,
    )
    return source + r'''

; Added only to the temporary W3L validation-regression source.
w3l_regression_run:
    ld a,2
    ld (w3d_requested_difficulty),a
    ld b,a
    xor a
    call w3d_load_level_package
    jp w3l_regression_record_and_exit

w3l_regression_record_and_exit:
    ld (w3l_regression_result+4),a
    ld hl,w3l_regression_filename
    ld de,w3l_regression_result
    ld bc,5
    MOSCALL mos_save
    ret

w3l_regression_filename:
    db "loader_result.bin",0
w3l_regression_result:
    db "W3R1",0
'''


def changed(package: bytes, offset: int, value: int) -> bytes:
    result = bytearray(package)
    result[offset] = value
    return bytes(result)


def cases(valid: bytes) -> tuple[tuple[str, bytes | None, int], ...]:
    noncanonical_offset = bytearray(valid)
    noncanonical_offset[26] += 1
    wrong_total = bytearray(valid)
    declared = int.from_bytes(wrong_total[14:16], "little")
    wrong_total[14:16] = (declared - 1).to_bytes(2, "little")
    return (
        ("valid", valid, 0),
        ("missing_file", None, 1),
        ("bad_magic", changed(valid, 0, ord("X")), 2),
        ("bad_version", changed(valid, 4, 2), 3),
        ("wrong_level", changed(valid, 6, 1), 4),
        ("door_capacity", changed(valid, 8, 65), 5),
        ("reserved_header", changed(valid, 40, 1), 6),
        ("noncanonical_offset", bytes(noncanonical_offset), 6),
        ("wrong_total", bytes(wrong_total), 6),
        ("truncated_footer", valid[:-1], 6),
        (
            "bounded_load_ignores_trailing_bytes",
            valid + bytes(MAX_PACKAGE_SIZE + 1 - len(valid)),
            0,
        ),
    )


def run_case(
    *,
    name: str,
    package: bytes | None,
    expected: int,
    app: Path,
    emulator: list[str],
    environment: dict[str, str],
    work: Path,
    timeout: float,
) -> str | None:
    state = app / "level_00/state_medium.w3l"
    if package is None:
        state.unlink(missing_ok=True)
    else:
        state.write_bytes(package)

    result = app / "loader_result.bin"
    result.unlink(missing_ok=True)
    stdout_path = work / f"{name}.stdout.log"
    stderr_path = work / f"{name}.stderr.log"
    with stdout_path.open("wb") as stdout_stream, stderr_path.open("wb") as stderr_stream:
        process = subprocess.Popen(
            emulator,
            cwd=work,
            env=environment,
            stdout=stdout_stream,
            stderr=stderr_stream,
        )
        payload = b""
        failure: str | None = None
        try:
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    failure = f"emulator exited with {process.returncode}"
                    break
                if result.exists():
                    payload = result.read_bytes()
                    if len(payload) == 5 and payload[:4] == b"W3R1":
                        break
                time.sleep(0.025)
            else:
                failure = "timed out waiting for loader result"
        finally:
            process.terminate()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()

    if failure:
        stdout_tail = stdout_path.read_text(errors="replace")[-2000:]
        stderr_tail = stderr_path.read_text(errors="replace")[-2000:]
        return (
            f"{name}: {failure}\nstdout tail:\n{stdout_tail}\n"
            f"stderr tail:\n{stderr_tail}"
        )
    actual = payload[4]
    if actual != expected:
        return f"{name}: returned {actual}, expected {expected}"
    print(f"PASS: {name} -> W3D_LEVEL_LOAD_{expected}")
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timeout", type=float, default=15.0)
    args = parser.parse_args()

    valid = (
        GENERATED / "levels/level_00/state_medium.w3l"
    ).read_bytes()
    work = Path(tempfile.mkdtemp(prefix="w3l"))
    atexit.register(shutil.rmtree, work, ignore_errors=True)
    source_root = work / "src"
    shutil.copytree(SOURCE_ROOT, source_root)
    source_path = source_root / "wolf3d.asm"
    source_path.write_text(instrument(source_path.read_text()))

    sdcard = work / "sdcard"
    app = sdcard / "wolf3d"
    (app / "level_00").mkdir(parents=True)
    binary = app / "wolf3d.bin"
    run(["ez80asm", "wolf3d.asm", str(binary)], cwd=source_root)
    (sdcard / "autoexec.txt").write_bytes(
        b"SET KEYBOARD 1\r\ncd wolf3d\r\nload wolf3d.bin\r\nrun\r\n"
    )

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

    failures = []
    for name, package, expected in cases(valid):
        failure = run_case(
            name=name,
            package=package,
            expected=expected,
            app=app,
            emulator=emulator,
            environment=environment,
            work=work,
            timeout=args.timeout,
        )
        if failure:
            failures.append(failure)
    if failures:
        print("\n".join(f"FAIL: {failure}" for failure in failures))
        return 1
    print(f"PASS: {len(cases(valid))} production W3L loader cases")
    return 0


if __name__ == "__main__":
    sys.exit(main())
