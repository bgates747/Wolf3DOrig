#!/usr/bin/env python3
"""Build the exact stopped full-MOS human-review package."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import zlib


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
QUALIFICATION = ROOT / "qualification/build"
BUILD = HERE / "build"
PACKAGE = BUILD / "package"
MOS_API = Path("/Agon/mystuff/golem/reference/agnb-asm/lib/mos_api.inc")

MODULE_BUFFER = 60023
WORKSPACE_BUFFER = 0x7100
MAP_BUFFER = 0x7101
TEXTURE_BUFFER = 0x7102
CONFIG_BUFFER = 0x7103
CAPABILITIES = 31


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def buffer_command(buffer_id: int, operation: int) -> bytes:
    return bytes((23, 0, 160)) + struct.pack("<H", buffer_id) + bytes((operation,))


def raw(payload: bytes) -> bytes:
    if not payload or len(payload) > 0xffff:
        raise ValueError("raw review record length is invalid")
    return bytes((1,)) + struct.pack("<H", len(payload)) + payload


def transaction(token: int, kind: int, reply_flags: int, expected: int,
                handle_patch: int, packet: bytes) -> bytes:
    return (
        bytes((2,))
        + struct.pack(
            "<HBBHHH", token, kind, reply_flags, expected,
            handle_patch, len(packet),
        )
        + packet
    )


def vdpl_packet(operation: int, token: int, fields: bytes,
                 request_reply: bool = True) -> bytes:
    body = struct.pack(
        "<BBHBB", 1, operation, token, 1 if request_reply else 0, 0
    ) + fields
    return bytes((23, 0, 216)) + struct.pack("<H", len(body)) + body


def upload_records(buffer_id: int, data: bytes) -> list[bytes]:
    records = [raw(buffer_command(buffer_id, 2))]
    for offset in range(0, len(data), 4096):
        block = data[offset:offset + 4096]
        records.append(raw(buffer_command(buffer_id, 0)
                           + struct.pack("<H", len(block)) + block))
    records.append(raw(buffer_command(buffer_id, 14)))
    return records


def build_script(module: bytes, workspace: bytes, tilemap: bytes,
                 textures: bytes, config: bytes) -> tuple[bytes, list[dict]]:
    records = []
    manifest = []

    token = 1
    info = vdpl_packet(4, token, struct.pack("<H", 1))
    records.append(transaction(token, 4, 0, CAPABILITIES, 0xffff, info))
    manifest.append({"token": token, "operation": "INFO capabilities",
                     "reply_kind": 4, "value": CAPABILITIES})

    for buffer_id, name, payload in (
        (MODULE_BUFFER, "module", module),
        (WORKSPACE_BUFFER, "workspace", workspace),
        (MAP_BUFFER, "map", tilemap),
        (TEXTURE_BUFFER, "textures", textures),
        (CONFIG_BUFFER, "config", config),
    ):
        records.extend(upload_records(buffer_id, payload))
        manifest.append({"buffer": buffer_id, "role": name, "bytes": len(payload)})

    token += 1
    load = vdpl_packet(
        1, token, struct.pack("<HIH", MODULE_BUFFER, len(module), 0)
    )
    records.append(transaction(token, 2, 1, 0, 0xffff, load))
    manifest.append({"token": token, "operation": "LOAD",
                     "reply_kind": 2, "capture_handle": True})

    # The module owns every pixel in the reviewed frame. Host text is removed
    # before CONFIG/RENDER and no overlay is drawn over the scene.
    records.append(raw(bytes((22, 136, 23, 1, 0))))

    token += 1
    config_run = vdpl_packet(
        2, token, struct.pack("<HHH", 0, 0, CONFIG_BUFFER)
    )
    records.append(transaction(token, 3, 0, 0, 11, config_run))
    manifest.append({"token": token, "operation": "RUN CONFIG",
                     "reply_kind": 3, "value": 0})

    token += 1
    render_run = vdpl_packet(
        2, token, struct.pack("<HHH", 0, 1, CONFIG_BUFFER)
    )
    records.append(transaction(token, 3, 0, 0, 11, render_run))
    manifest.append({"token": token, "operation": "RUN RENDER",
                     "reply_kind": 3, "value": 0})
    records.append(raw(bytes((23, 0, 195))))
    records.append(bytes((9,)))  # Human acknowledges the unlabelled scene.

    token += 1
    unload = vdpl_packet(3, token, struct.pack("<H", 0))
    records.append(transaction(token, 3, 0, 0, 11, unload))
    records.append(bytes((3,)))  # Mark handle absent before common cleanup.
    manifest.append({"token": token, "operation": "UNLOAD",
                     "reply_kind": 3, "value": 0})
    records.append(bytes((0,)))

    script = b"".join(records)
    if len(script) > 0x20000:
        raise AssertionError(f"review script is too large: {len(script)}")
    return script, manifest


def png_chunk(kind: bytes, payload: bytes) -> bytes:
    body = kind + payload
    return struct.pack(">I", len(payload)) + body + struct.pack(">I", zlib.crc32(body))


def reference_rgb(frame: bytes) -> bytes:
    if len(frame) != 320 * 240:
        raise AssertionError("oracle frame must be exactly 320x240 RGB222")
    rgb = bytearray()
    for value in frame:
        rgb.extend(((value & 3) * 85, ((value >> 2) & 3) * 85,
                    ((value >> 4) & 3) * 85))
    return bytes(rgb)


def write_reference_images(frame: bytes, png_destination: Path,
                           ppm_destination: Path) -> None:
    rgb = reference_rgb(frame)
    filtered = b"".join(
        b"\0" + rgb[row * 320 * 3:(row + 1) * 320 * 3]
        for row in range(240)
    )
    png = (
        b"\x89PNG\r\n\x1a\n"
        + png_chunk(b"IHDR", struct.pack(">IIBBBBB", 320, 240, 8, 2, 0, 0, 0))
        + png_chunk(b"IDAT", zlib.compress(filtered, 9))
        + png_chunk(b"IEND", b"")
    )
    png_destination.write_bytes(png)
    ppm_destination.write_bytes(b"P6\n320 240\n255\n" + rgb)


def assemble(assembler: Path, destination: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="w3v-review-") as name:
        temporary = Path(name)
        shutil.copyfile(HERE / "review_guest.asm", temporary / "review.asm")
        shutil.copyfile(MOS_API, temporary / "mos_api.inc")
        subprocess.run(
            [str(assembler), "review.asm", "review.bin"],
            cwd=temporary, check=True,
        )
        shutil.copyfile(temporary / "review.bin", destination)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--assembler", type=Path)
    parser.add_argument("--guest-binary", type=Path)
    args = parser.parse_args()
    if (args.assembler is None) == (args.guest_binary is None):
        parser.error("provide exactly one of --assembler or --guest-binary")

    required = {
        "module": QUALIFICATION / "wolf3d_scene.vdpl",
        "oracle": QUALIFICATION / "oracle-frame.bin",
        "workspace": QUALIFICATION / "fixture/workspace.bin",
        "map": QUALIFICATION / "fixture/map.bin",
        "textures": QUALIFICATION / "fixture/textures.bin",
        "config": QUALIFICATION / "fixture/config.bin",
        "target_receipt": QUALIFICATION / "target-jit-evidence.json",
    }
    missing = [str(path) for path in required.values() if not path.is_file()]
    if missing:
        raise SystemExit("Run the pinned host/target qualification first:\n" + "\n".join(missing))

    BUILD.mkdir(parents=True, exist_ok=True)
    temporary_package = BUILD / f".package-{os.getpid()}"
    if temporary_package.exists():
        shutil.rmtree(temporary_package)
    temporary_package.mkdir()
    try:
        review_binary = temporary_package / "review.bin"
        if args.guest_binary is not None:
            shutil.copyfile(args.guest_binary.resolve(), review_binary)
        else:
            assemble(args.assembler.resolve(), review_binary)
        script, transactions = build_script(
            required["module"].read_bytes(), required["workspace"].read_bytes(),
            required["map"].read_bytes(), required["textures"].read_bytes(),
            required["config"].read_bytes(),
        )
        (temporary_package / "script.bin").write_bytes(script)
        shutil.copyfile(required["module"], temporary_package / "wolf3d_scene.vdpl")
        for name in ("workspace", "map", "textures", "config"):
            shutil.copyfile(required[name], temporary_package / f"{name}.bin")
        write_reference_images(
            required["oracle"].read_bytes(),
            temporary_package / "reference.png",
            temporary_package / "reference.ppm",
        )
        shutil.copyfile(HERE / "REVIEW.md", temporary_package / "REVIEW.txt")

        source = temporary_package / "source"
        source.mkdir()
        for path in (
            HERE / "review_guest.asm",
            ROOT / "wolf3d_scene.cpp",
            ROOT / "wolf3d_scene_contract.h",
            ROOT / "wolf3d_tables.inc",
            ROOT / "generate_fixture.py",
        ):
            shutil.copyfile(path, source / path.name)

        receipt = {
            "scope": "stopped bounded full-MOS human-review fixture; no run claim",
            "roles": {
                "source/wolf3d_scene.cpp": "exact reviewed C++ renderer module source",
                "wolf3d_scene.vdpl": "exact uploaded Xtensa package",
                "review.bin": "eZ80 host: upload/invoke/swap/wait/teardown only",
                "script.bin": "host command/data tape; contains the exact module and scene inputs",
                "reference.png": "expected module-only 320x240 output; not drawn by the host",
                "reference.ppm": "byte-exact RGB reference used only by agent rehearsal",
                "REVIEW.txt": "human instructions and host/module drawing boundary",
            },
            "transactions": transactions,
            "script_bytes": len(script),
            "expected_reply_bytes": 50,
            "target_evidence_sha256": sha(required["target_receipt"]),
            "oracle_frame_sha256": sha(required["oracle"]),
            "files": {},
        }
        for path in sorted(temporary_package.rglob("*")):
            if path.is_file() and path.name != "expected.json":
                receipt["files"][str(path.relative_to(temporary_package))] = {
                    "bytes": path.stat().st_size,
                    "sha256": sha(path),
                }
        (temporary_package / "expected.json").write_text(
            json.dumps(receipt, indent=2) + "\n"
        )

        if PACKAGE.exists():
            shutil.rmtree(PACKAGE)
        temporary_package.rename(PACKAGE)
    finally:
        if temporary_package.exists():
            shutil.rmtree(temporary_package)

    print(json.dumps({
        "package": str(PACKAGE),
        "review_binary_sha256": sha(PACKAGE / "review.bin"),
        "script_sha256": sha(PACKAGE / "script.bin"),
        "module_sha256": sha(PACKAGE / "wolf3d_scene.vdpl"),
        "reference_sha256": sha(PACKAGE / "reference.png"),
        "script_bytes": (PACKAGE / "script.bin").stat().st_size,
    }, indent=2))


if __name__ == "__main__":
    main()
