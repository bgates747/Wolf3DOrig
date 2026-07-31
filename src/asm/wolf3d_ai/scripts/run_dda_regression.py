#!/usr/bin/env python3
"""Generate, assemble, and run the eZ80 Wolf3D sight regression in Fab."""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import struct
import subprocess
import sys
import time
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[1]
REPOSITORY = Path(__file__).resolve().parents[4]
PYTHON = REPOSITORY / ".venv/bin/python"
GENERATOR = PROJECT / "scripts/generate_dda_vectors.py"
SHARED_GENERATOR = REPOSITORY / "agonport/tools/gen_dda_fixture.py"
SHARED_MAP = REPOSITORY / "agonport/assets/generated/dda_smoke_test_map.bin"
ASSEMBLY = PROJECT / "src/dda_regression.asm"
TARGET = PROJECT / "tgt"
# wolf3d_math.inc/wolf3d_sight.inc/wolf3d_world.inc live in the permanent
# "wolf3d" app now (graduated out of this AI-prototyping project once
# validated); ez80asm resolves a nested bare include relative to its cwd, not
# the including file's own directory, so ez80asm must run with this as cwd.
WOLF3D_APP_SRC = PROJECT.parent / "wolf3d/src"
PROFILE = REPOSITORY / "agonport/emulator"
FAB = PROFILE / "fab-agon-emulator"
VDP = PROFILE / "vdp_stock.so"
MOS = PROFILE / "mos_console8.bin"
SDCARD = PROFILE / "sdcard"

RECORD = struct.Struct("<BBHBBBBBBBBiiiiI")
RESULT_SIZE = 34
EXPECTED_MAP_SHA256 = (
    "640b7d254f1d887b122a126414fefc708718a8f044f35ca7b6130f6b56d81ce2"
)


def run(command: list[str], *, cwd: Path | None = None) -> None:
    print("+", " ".join(command))
    subprocess.run(command, check=True, cwd=cwd)


def validate_map() -> bytes:
    payload = SHARED_MAP.read_bytes()
    if len(payload) != 4096:
        raise RuntimeError(f"map length is {len(payload)}, expected 4096")
    digest = hashlib.sha256(payload).hexdigest()
    if digest != EXPECTED_MAP_SHA256:
        raise RuntimeError(f"unexpected map hash {digest}")
    for coordinate in range(64):
        indices = (
            coordinate,
            63 * 64 + coordinate,
            coordinate * 64,
            coordinate * 64 + 63,
        )
        if any(payload[index] == 0 for index in indices):
            raise RuntimeError("map outer border is not completely solid")
    if payload[13 * 64 + 13] != 0x80:
        raise RuntimeError("canonical door is not 0x80 at (13,13)")
    return payload


def validate_vectors(path: Path) -> tuple[bytes, int, tuple[int, int]]:
    payload = path.read_bytes()
    if len(payload) < 4:
        raise RuntimeError("vector file is shorter than its header")
    count = struct.unpack_from("<I", payload)[0]
    expected_size = 4 + count * RECORD.size
    if len(payload) != expected_size:
        raise RuntimeError(
            f"vector size {len(payload)} != expected {expected_size}"
        )
    last_opcode = 0
    seen_sequences: set[int] = set()
    counts = [0, 0]
    for offset in range(4, len(payload), RECORD.size):
        fields = RECORD.unpack_from(payload, offset)
        opcode, expected = fields[:2]
        if opcode not in (0, 1):
            raise RuntimeError(f"bad opcode {opcode} at offset {offset}")
        if opcode < last_opcode:
            raise RuntimeError("vectors are not grouped by opcode")
        if expected not in (0, 1):
            raise RuntimeError(f"bad expected boolean at offset {offset}")
        last_opcode = opcode
        counts[opcode] += 1
        sequence = fields[-1]
        if sequence in seen_sequences:
            raise RuntimeError(f"duplicate sequence id {sequence}")
        seen_sequences.add(sequence)
    if min(counts) < 10:
        raise RuntimeError(f"insufficient per-op coverage: {counts}")
    print(f"vector coverage: CheckLine={counts[0]}, CheckSight={counts[1]}")
    return payload, count, (counts[0], counts[1])


def replace_test_link() -> None:
    link = SDCARD / "wolf3d_ai"
    if link.is_symlink():
        link.unlink()
    elif link.exists():
        raise RuntimeError(f"refusing to replace non-symlink {link}")
    link.symlink_to(os.path.relpath(TARGET, link.parent), target_is_directory=True)


def decode_failure(vectors: bytes, index: int) -> str:
    if index == 0xFFFF:
        return "no first-failure record"
    offset = 4 + index * RECORD.size
    if offset + RECORD.size > len(vectors):
        return f"first-failure index {index} is outside vector payload"
    fields = RECORD.unpack_from(vectors, offset)
    names = (
        "opcode", "expected", "door_position", "door_vertical",
        "direction", "actor_area", "area_connected", "made_noise",
        "patch_x", "patch_y", "patch_value", "actor_x", "actor_y",
        "player_x", "player_y", "sequence",
    )
    return ", ".join(f"{name}={value}" for name, value in zip(names, fields))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--random-cases", type=int, default=10_000)
    parser.add_argument("--timeout", type=float, default=90.0)
    args = parser.parse_args()

    TARGET.mkdir(parents=True, exist_ok=True)
    vectors_path = TARGET / "dda_vectors.bin"
    binary_path = TARGET / "dda_regression.bin"
    result_path = TARGET / "dda_result.bin"
    map_copy = TARGET / SHARED_MAP.name
    if result_path.exists():
        result_path.unlink()

    run([str(PYTHON), str(SHARED_GENERATOR)])
    map_payload = validate_map()
    map_copy.write_bytes(map_payload)
    run(
        [
            str(PYTHON),
            str(GENERATOR),
            "--random-cases",
            str(args.random_cases),
            "--output",
            str(vectors_path),
        ]
    )
    vectors, expected_records, counts = validate_vectors(vectors_path)
    if expected_records > 0xFFFF:
        raise RuntimeError("assembly result format supports at most 65535 records")

    run(
        [
            "ez80asm",
            os.path.relpath(ASSEMBLY, WOLF3D_APP_SRC),
            os.path.relpath(TARGET / "dda_regression.bin", WOLF3D_APP_SRC),
        ],
        cwd=WOLF3D_APP_SRC,
    )
    replace_test_link()
    (SDCARD / "autoexec.txt").write_bytes(
        b"SET KEYBOARD 1\r\n"
        b"cd wolf3d_ai\r\n"
        b"load dda_regression.bin\r\n"
        b"run\r\n"
    )

    environment = os.environ.copy()
    environment["SDL_VIDEODRIVER"] = "dummy"
    environment["SDL_AUDIODRIVER"] = "dummy"
    local_lib = str(Path.home() / ".local/lib")
    environment["LD_LIBRARY_PATH"] = (
        local_lib
        + (
            ":" + environment["LD_LIBRARY_PATH"]
            if environment.get("LD_LIBRARY_PATH")
            else ""
        )
    )
    command = [
        str(FAB.resolve()),
        "--renderer", "sw",
        "--firmware", "console8",
        "--mos", str(MOS.resolve()),
        "--vdp", str(VDP.resolve()),
        "--sdcard", str(SDCARD.resolve()),
        "--zero",
    ]
    print("+", " ".join(command))
    process = subprocess.Popen(
        command,
        cwd=PROFILE,
        env=environment,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        deadline = time.monotonic() + args.timeout
        result_payload = b""
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError(f"emulator exited with {process.returncode}")
            if result_path.exists():
                result_payload = result_path.read_bytes()
                if len(result_payload) == RESULT_SIZE:
                    magic = result_payload[:4]
                    if magic == b"W3R1":
                        break
            time.sleep(0.05)
        else:
            raise RuntimeError("timed out waiting for emulator result")
    finally:
        process.terminate()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()

    magic = result_payload[:4]
    records = int.from_bytes(result_payload[4:7], "little")
    errors = int.from_bytes(result_payload[7:10], "little")
    line_errors = int.from_bytes(result_payload[10:13], "little")
    sight_errors = int.from_bytes(result_payload[13:16], "little")
    first_index = int.from_bytes(result_payload[16:19], "little")
    first_expected = result_payload[19]
    first_actual = result_payload[20]
    first_opcode = result_payload[21]
    first_carry = result_payload[22]
    first_sequence = int.from_bytes(result_payload[23:26], "little")
    milliseconds = (
        int.from_bytes(result_payload[26:29], "little"),
        int.from_bytes(result_payload[29:32], "little"),
    )
    if magic != b"W3R1":
        raise RuntimeError(f"bad result magic {magic!r}")
    if errors:
        if first_opcode == 0xFE:
            reasons = {
                1: "A result",
                2: "Z flag",
                3: "carry flag",
                4: "preserved registers",
            }
            print(
                "FAIL: public ABI preservation preflight "
                f"(case={first_sequence}, "
                f"reason={reasons.get(first_actual, first_actual)}, "
                f"returnA={first_expected}, probeTile={first_carry})"
            )
            return 1
        if first_opcode == 0xFD:
            print("FAIL: short vector-file read")
            return 1
        print(
            f"FAIL: {errors} errors in {records} records "
            f"(CheckLine={line_errors}, CheckSight={sight_errors})"
        )
        print(
            "first failure: "
            f"index={first_index}, sequence={first_sequence}, "
            f"opcode={first_opcode}, expected={first_expected}, "
            f"actual={first_actual}, carry={first_carry}"
        )
        print(decode_failure(vectors, first_index))
        return 1
    if records != expected_records:
        print(
            f"FAIL: harness completed only {records} of "
            f"{expected_records} records"
        )
        return 1
    print(
        f"PASS: {records} records "
        f"(CheckLine={counts[0]}, CheckSight={counts[1]})"
    )
    print("PRT timing (validation and fixture preparation included):")
    for name, count, elapsed in zip(
        ("CheckLine", "CheckSight"), counts, milliseconds
    ):
        if elapsed:
            per_frame = count * 1000 / (elapsed * 60)
            print(
                f"  {name:10s} {count:5d} calls / {elapsed:4d} ms"
                f" = {per_frame:8.1f} calls per 60 Hz frame"
            )
        else:
            print(f"  {name:10s} below 1 ms timer resolution")
    return 0


if __name__ == "__main__":
    sys.exit(main())
