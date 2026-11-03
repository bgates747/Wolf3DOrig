#!/usr/bin/env python3
"""Assemble, execute, and byte-validate the production eZ80 batch serializer."""

from __future__ import annotations

import argparse
import atexit
import hashlib
import os
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import time


HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent
_installed_root = HERE.parents[3]
STAGED_ROOT = Path(os.environ.get("W3D_STAGED_ROOT", _installed_root))
RUNTIME_ROOT = Path(os.environ.get("W3D_RUNTIME_ROOT", _installed_root))
SOURCE = STAGED_ROOT / "src/asm/wolf3d/src"
ASSEMBLER = Path(
    os.environ.get(
        "W3D_EZ80ASM",
        STAGED_ROOT / "src/asm/wolf3d/tgt/.tools/ez80asm",
    )
)
FAB = RUNTIME_ROOT / "agonport/emulator/fab-agon-emulator"
MOS = RUNTIME_ROOT / "agonport/emulator/mos_console8.bin"
VDP = RUNTIME_ROOT / "agonport/emulator/vdp_stock.so"


def run(command: list[str], *, cwd: Path | None = None) -> None:
    print("+", " ".join(command))
    subprocess.run(command, cwd=cwd, check=True)


def validate_assembled(binary: Path) -> None:
    descriptor = (
        b"W3PA" + bytes((2, 24)) +
        struct.pack("<HHHHHHHHH", 2, 0x7100, 0x7101, 2, 0x1000, 0x2000, 0x4000, 0, 0)
    )
    payload = binary.read_bytes()
    if len(descriptor) != 24 or payload.count(descriptor) != 1:
        raise AssertionError("assembled production descriptor template is not unique/exact")


def parse_batch(payload: bytes) -> tuple[int, int, list[tuple[int, bytes]]]:
    if len(payload) < 16 or payload[:4] != b"W3DU":
        raise AssertionError("bad batch magic/size")
    schema, header, flags, total, count, generation, reserved = struct.unpack_from(
        "<BBHHHHH", payload, 4
    )
    if (schema, header, total, reserved) != (2, 16, len(payload), 0):
        raise AssertionError("bad batch header")
    records: list[tuple[int, bytes]] = []
    cursor = 16
    for _ in range(count):
        if cursor + 2 > len(payload):
            raise AssertionError("truncated record header")
        kind, size = payload[cursor : cursor + 2]
        cursor += 2
        end = cursor + size
        if end > len(payload):
            raise AssertionError("truncated record payload")
        records.append((kind, payload[cursor:end]))
        cursor = end
    if cursor != len(payload):
        raise AssertionError("trailing batch bytes")
    return flags, generation, records


def validate_outputs(app: Path) -> None:
    result = (app / "batch.dat").read_bytes()
    if len(result) != 16 or result[:4] != b"W3B1":
        raise AssertionError("missing/invalid batch result")
    code, retry_mask, final_mask, empty_status = result[4:8]
    last_generation, full_size, dirty_size, schema = struct.unpack_from("<HHHH", result, 8)
    if (code, retry_mask, final_mask, empty_status, last_generation, schema) != (
        0, 0xFF, 0, 1, 2, 2
    ):
        raise AssertionError(
            "bad lifecycle receipt: "
            f"code={code} retry={retry_mask:#04x} final={final_mask:#04x} "
            f"empty={empty_status} generation={last_generation} schema={schema}"
        )

    full = (app / "full.bin").read_bytes()
    retry = (app / "retry.bin").read_bytes()
    dirty = (app / "dirty.bin").read_bytes()
    if full != retry:
        raise AssertionError("generation-1 retry is not byte-identical")
    if (len(full), len(dirty)) != (full_size, dirty_size):
        raise AssertionError("receipt byte counts do not match files")

    flags, generation, records = parse_batch(full)
    kinds = [kind for kind, _ in records]
    expected_kinds = [1, 2, 9] + [3] * 22 + [4] * 21 + [6] * 121 + [7, 8]
    if (flags, generation, len(full), kinds) != (1, 1, 1833, expected_kinds):
        raise AssertionError("full snapshot shape changed")
    if records[0][1] != bytes((2, 0, 22, 121, 0, 0)):
        raise AssertionError("bad level binding")
    if records[1][1] != bytes((0, 128, 29, 0, 0, 128, 57, 0, 0, 0)):
        raise AssertionError("bad initial player pose")
    if records[2][1] != bytes(89):
        raise AssertionError("full snapshot pushwall reset changed")
    if [payload[0] for kind, payload in records if kind == 3] != list(range(22)):
        raise AssertionError("door ids are not complete/ordered")
    if [int.from_bytes(payload[:2], "little") for kind, payload in records if kind == 4] != list(range(1, 22)):
        raise AssertionError("actor ids are not complete/ordered")
    first_actor = next(payload for kind, payload in records if kind == 4)
    if first_actor != struct.pack(
        "<HhiiHB", 1, 50, 0x00218000, 0x00098000, 270, 8
    ):
        raise AssertionError("shared actor wire conversion changed")
    if [int.from_bytes(payload[:2], "little") for kind, payload in records if kind == 6] != list(range(121)):
        raise AssertionError("static ids are not complete/ordered")

    flags, generation, records = parse_batch(dirty)
    if (flags, generation, len(dirty), [kind for kind, _ in records]) != (
        0, 2, 161, [2, 9, 3, 5, 6, 7, 8]
    ):
        raise AssertionError("dirty snapshot shape changed")
    if records[0][1][0] != 0x40:
        raise AssertionError("dirty player pose not serialized")
    if records[1][1][:8] != bytes((1, 10, 10, 10, 10, 0, 32, 4)):
        raise AssertionError("dirty pushwall not serialized")
    if records[2][1][0] != 0 or records[2][1][6:8] != b"\x80\x00":
        raise AssertionError("dirty door not serialized")
    if records[3][1] != b"\x01\x00":
        raise AssertionError("actor removal not serialized")
    if records[4][1][:2] != b"\x01\x00" or records[4][1][4:6] != b"\xff\xff":
        raise AssertionError("static removal not serialized")
    if records[5][1][0] != 73 or records[5][1][9] != 3:
        raise AssertionError("complete HUD value not serialized")
    if records[6][1] != b"\xff\xff":
        raise AssertionError("view-weapon removal not serialized")

    print(
        "PASS: real-eZ80 full/dirty serializer; "
        f"full={len(full)} retry_sha={hashlib.sha256(retry).hexdigest()} "
        f"dirty={len(dirty)} dirty_sha={hashlib.sha256(dirty).hexdigest()}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument(
        "--results-dir", type=Path,
        help="validate already-retrieved target evidence without launching an emulator",
    )
    args = parser.parse_args()
    if args.results_dir is not None:
        validate_outputs(args.results_dir.resolve())
        return
    missing = [path for path in (SOURCE, ASSEMBLER, FAB, MOS, VDP) if not path.exists()]
    if missing:
        raise FileNotFoundError("missing regression dependency: " + ", ".join(map(str, missing)))

    work = Path(tempfile.mkdtemp(prefix="w3b"))
    atexit.register(shutil.rmtree, work, ignore_errors=True)
    sdcard = work / "sdcard"
    app = sdcard / "b"
    app.mkdir(parents=True)
    entry = work / "b.asm"
    shutil.copyfile(PROJECT / "src/batch_regression.asm", entry)
    binary = app / "b.bin"
    run([str(ASSEMBLER), str(entry), str(binary)], cwd=SOURCE)
    validate_assembled(binary)
    (sdcard / "autoexec.txt").write_bytes(
        b"SET KEYBOARD 1\r\ncd b\r\nload b.bin\r\nrun\r\n"
    )

    environment = os.environ.copy()
    environment["SDL_VIDEODRIVER"] = "dummy"
    environment["SDL_AUDIODRIVER"] = "dummy"
    local_lib = str(Path.home() / ".local/lib")
    environment["LD_LIBRARY_PATH"] = local_lib + (
        ":" + environment["LD_LIBRARY_PATH"] if environment.get("LD_LIBRARY_PATH") else ""
    )
    command = [
        str(FAB.resolve()), "--renderer", "sw", "--firmware", "console8",
        "--mos", str(MOS.resolve()), "--vdp", str(VDP.resolve()),
        "--sdcard", str(sdcard), "--zero",
    ]
    print("+", " ".join(command))
    process = subprocess.Popen(
        command, cwd=work, env=environment,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    try:
        deadline = time.monotonic() + args.timeout
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError(f"emulator exited with {process.returncode}")
            result = app / "batch.dat"
            if result.is_file() and result.stat().st_size == 16:
                break
            time.sleep(0.05)
        else:
            raise RuntimeError("timed out waiting for serializer result")
    finally:
        process.terminate()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()

    validate_outputs(app)


if __name__ == "__main__":
    main()
