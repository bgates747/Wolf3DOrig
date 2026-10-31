#!/usr/bin/env python3
"""Build the stopped direct-row review package after target qualification."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
QUALIFICATION = ROOT / "qualification/build"
COPIED_REVIEW = ROOT / "review"
BUILD = HERE / "build"
PACKAGE = BUILD / "package"
MOS_API = Path("/Agon/mystuff/golem/reference/agnb-asm/lib/mos_api.inc")
DIRECT_WORKSPACE_BYTES = 11552

DIRECT_GUEST_REPLACEMENTS = (
    (
        "The reviewed 320x240 scene is drawn entirely by wolf3d_scene.vdpl. This",
        "The reviewed 320x240 scene is drawn entirely by "
        "wolf3d_scene_rows.vdpl. This",
    ),
    (
        'db 13,10,"Loading exact bounded Wolf3D VDPlet review scene...",13,10\n'
        '    db "The reviewed frame will contain no host labels.",13,10',
        'db 13,10,"Loading exact Wolf3D direct-row VDPlet review...",13,10\n'
        '    db "C renders directly into hidden colour rows.",13,10\n'
        '    db "Saves 80,608 workspace bytes; costs about 33% more cycles.",13,10\n'
        '    db "The reviewed frame will contain no host labels.",13,10',
    ),
    (
        'db "The scene was drawn entirely by wolf3d_scene.vdpl.",13,10\n'
        '    db "Host labels were shown only before and after that frame.",13,10\n'
        '    db "Type dir at the MOS prompt below and report that it works.",13,10',
        'db "The scene was drawn by wolf3d_scene_rows.vdpl C code.",13,10\n'
        '    db "The host drew no scene pixels; one key requested cleanup.",13,10\n'
        '    db "MOS mode, cursor, callback, and buffers were restored.",13,10',
    ),
)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def direct_guest_source() -> str:
    """Derive the review-only host without changing the accepted control."""
    text = (COPIED_REVIEW / "review_guest.asm").read_text()
    for old, new in DIRECT_GUEST_REPLACEMENTS:
        if text.count(old) != 1:
            raise RuntimeError(f"direct guest source anchor count != 1: {old!r}")
        text = text.replace(old, new)
    return text


def load_review_builder():
    spec = importlib.util.spec_from_file_location(
        "wolf_copied_review_builder", COPIED_REVIEW / "build.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    module.CAPABILITIES = 287
    return module


def assemble(assembler: Path, destination: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="w3v-rows-review-") as name:
        temporary = Path(name)
        (temporary / "review.asm").write_text(direct_guest_source())
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
    parser.add_argument("--jit-receipt", type=Path,
                        default=QUALIFICATION / "rows-target-jit/evidence.json")
    parser.add_argument("--interp-receipt", type=Path,
                        default=QUALIFICATION / "rows-target-interp/evidence.json")
    parser.add_argument("--output", type=Path, default=PACKAGE)
    arguments = parser.parse_args()
    if (arguments.assembler is None) == (arguments.guest_binary is None):
        parser.error("provide exactly one of --assembler or --guest-binary")

    required = {
        "direct_module": QUALIFICATION / "wolf3d_scene_rows.vdpl",
        "copied_module": QUALIFICATION / "wolf3d_scene.vdpl",
        "oracle": QUALIFICATION / "oracle-frame.bin",
        "workspace": QUALIFICATION / "fixture/workspace.bin",
        "map": QUALIFICATION / "fixture/map.bin",
        "textures": QUALIFICATION / "fixture/textures.bin",
        "config": QUALIFICATION / "fixture/config.bin",
        "jit_receipt": arguments.jit_receipt.resolve(),
        "interp_receipt": arguments.interp_receipt.resolve(),
    }
    missing = [str(path) for path in required.values() if not path.is_file()]
    if missing:
        raise SystemExit(
            "Both granted target runs must pass before review packaging:\n" +
            "\n".join(missing)
        )
    for name in ("jit_receipt", "interp_receipt"):
        receipt = json.loads(required[name].read_text())
        if not receipt.get("passed"):
            raise SystemExit(f"target receipt did not pass: {required[name]}")

    helper = load_review_builder()
    workspace = required["workspace"].read_bytes()[:DIRECT_WORKSPACE_BYTES]
    script, transactions = helper.build_script(
        required["direct_module"].read_bytes(), workspace,
        required["map"].read_bytes(), required["textures"].read_bytes(),
        required["config"].read_bytes(),
    )

    BUILD.mkdir(parents=True, exist_ok=True)
    temporary = BUILD / f".package-{os.getpid()}"
    if temporary.exists():
        shutil.rmtree(temporary)
    temporary.mkdir()
    try:
        if arguments.guest_binary is not None:
            shutil.copyfile(arguments.guest_binary.resolve(),
                            temporary / "review.bin")
        else:
            assemble(arguments.assembler.resolve(), temporary / "review.bin")
        (temporary / "script.bin").write_bytes(script)
        shutil.copyfile(required["direct_module"],
                        temporary / "wolf3d_scene_rows.vdpl")
        shutil.copyfile(required["copied_module"],
                        temporary / "wolf3d_scene.vdpl")
        for name in ("map", "textures", "config"):
            shutil.copyfile(required[name], temporary / f"{name}.bin")
        (temporary / "workspace.bin").write_bytes(workspace)
        helper.write_reference_images(
            required["oracle"].read_bytes(), temporary / "reference.png",
            temporary / "reference.ppm",
        )
        shutil.copyfile(HERE / "REVIEW.md", temporary / "REVIEW.txt")

        source = temporary / "source"
        source.mkdir()
        for path in (
            ROOT / "wolf3d_scene_rows.cpp",
            ROOT / "wolf3d_scene_rows_contract.h",
            ROOT / "wolf3d_scene.cpp",
            ROOT / "wolf3d_scene_contract.h",
            ROOT / "wolf3d_tables.inc",
        ):
            shutil.copyfile(path, source / path.name)
        (source / "review_guest.asm").write_text(direct_guest_source())

        receipt = {
            "scope": "stopped direct-row full-MOS review package; no run claim",
            "reviewed_path": "direct ABI1.6 hidden colour rows",
            "control_path": "accepted copied RGB222 package; bundled but not run",
            "host_draws_scene_pixels": False,
            "transactions": transactions,
            "script_bytes": len(script),
            "workspace_bytes": len(workspace),
            "target_receipts": {
                name: sha(required[name])
                for name in ("jit_receipt", "interp_receipt")
            },
            "files": {},
        }
        for path in sorted(temporary.rglob("*")):
            if path.is_file() and path.name != "expected.json":
                receipt["files"][str(path.relative_to(temporary))] = {
                    "bytes": path.stat().st_size,
                    "sha256": sha(path),
                }
        (temporary / "expected.json").write_text(
            json.dumps(receipt, indent=2) + "\n"
        )
        output = arguments.output.resolve()
        if output.exists():
            shutil.rmtree(output)
        output.parent.mkdir(parents=True, exist_ok=True)
        temporary.rename(output)
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)

    print(json.dumps({
        "package": str(arguments.output.resolve()),
        "script_bytes": len(script),
        "workspace_bytes": len(workspace),
        "direct_module_sha256": sha(required["direct_module"]),
        "copied_control_sha256": sha(required["copied_module"]),
        "stopped": True,
    }, indent=2))


if __name__ == "__main__":
    main()
