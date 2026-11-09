#!/usr/bin/env python3
"""Atomically stage the stopped Wolf rows target cohort on Oryx.

This deploys and verifies files only. It never imports Target, loads the
backend, starts an emulator, requests a lease, or stages the human review.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import os
import shutil
import subprocess
import tempfile


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PROJECT = ROOT.parents[1]
BUILD = HERE / "build"
REMOTE_HOST = "oryx-linuxlite"
REMOTE_ROOT = "/home/smith/Agon/mystuff/Wolf3dOrig"
REMOTE_STAGE = REMOTE_ROOT + "/agonport/vdplet/qualification/build/rows-cohort"
REMOTE_FIRMWARE = (
    "/home/smith/Agon/mystuff/agon-vdplet/build/vdpl-012/rows-r1/firmware.bin"
)
REMOTE_BACKEND = (
    "/home/smith/Agon/mystuff/flexe-agon-emulator/build/fx072/maintained-r02/"
    "flexe-vdp-maintained.so"
)

PINS = {
    "firmware": "8d980025f891484cf7e6cc5f2992cf517cb80e0123ff7de712ae8d7f2dc1c807",
    "firmware_elf": "1a7c44482d4ba8c5bfb49976c0bd664b9a9c2a635c7027b30954929ca567f814",
    "backend": "0866265bd6f3d73ad572f31dc1bb954f308ed9a5d857efa9414d37e1ade13374",
    "copied_module": "57b635fc1807d9108e576cfff4c79c7f57ade48164fc5be97d75a3562e54b1be",
    "direct_module": "c32381bc659b6e1fcc479eef22168a77eea22da310202da794234f172ccab670",
    "oracle_frame": "6b569190c057996d4c50c1cc182c5b210a05a5e8c6fc7f9e60059d892363bf93",
    "oracle_geometry": "2a15866957fa06d34f72067b2b1ff42325b3c3d0f02403059d43dc9a6812d820",
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(command: list[object], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run([str(value) for value in command], check=True, **kwargs)


def main() -> None:
    sources = {
        "target.py": HERE / "target.py",
        "qualify_rows.py": HERE / "qualify_rows.py",
        "build/wolf3d_scene.vdpl": BUILD / "wolf3d_scene.vdpl",
        "build/wolf3d_scene_rows.vdpl": BUILD / "wolf3d_scene_rows.vdpl",
        "build/oracle-frame.bin": BUILD / "oracle-frame.bin",
        "build/oracle-geometry.bin": BUILD / "oracle-geometry.bin",
        "build/fixture/workspace.bin": BUILD / "fixture/workspace.bin",
        "build/fixture/map.bin": BUILD / "fixture/map.bin",
        "build/fixture/textures.bin": BUILD / "fixture/textures.bin",
        "build/fixture/config.bin": BUILD / "fixture/config.bin",
        "source/wolf3d_scene.cpp": ROOT / "wolf3d_scene.cpp",
        "source/wolf3d_scene_contract.h": ROOT / "wolf3d_scene_contract.h",
        "source/wolf3d_scene_rows.cpp": ROOT / "wolf3d_scene_rows.cpp",
        "source/wolf3d_scene_rows_contract.h": ROOT / "wolf3d_scene_rows_contract.h",
        "source/wolf3d_tables.inc": ROOT / "wolf3d_tables.inc",
        "source/target-plan.md": PROJECT / "agonport/doc/wolf3d-vdplet-color-rows-target-plan.md",
    }
    for relative, path in sources.items():
        if not path.is_file():
            raise SystemExit(f"missing staging input {relative}: {path}")
    for relative, expected in (
        ("build/wolf3d_scene.vdpl", PINS["copied_module"]),
        ("build/wolf3d_scene_rows.vdpl", PINS["direct_module"]),
        ("build/oracle-frame.bin", PINS["oracle_frame"]),
        ("build/oracle-geometry.bin", PINS["oracle_geometry"]),
    ):
        actual = sha(sources[relative])
        if actual != expected:
            raise SystemExit(f"local pin mismatch {relative}: {actual} != {expected}")

    remote_temporary = REMOTE_STAGE + f".tmp-{os.getpid()}"
    check_absent = run([
        "ssh", "-o", "BatchMode=yes", REMOTE_HOST,
        "test ! -e " + REMOTE_STAGE + " && test ! -e " + remote_temporary,
    ])
    if check_absent.returncode:
        raise SystemExit("remote target staging path already exists")

    command_base = [
        REMOTE_ROOT + "/.venv/bin/python",
        REMOTE_STAGE + "/qualify_rows.py",
    ]
    commands = {
        "policy": (
            "Run JIT first. Stop on its first failure. Run interpreter only "
            "after JIT passes. Each command is one fresh process under the "
            "same granted central lease."
        ),
        "jit": command_base + [
            "--engine", "jit", "--firmware", REMOTE_FIRMWARE,
            "--backend", REMOTE_BACKEND,
            "--output", REMOTE_STAGE + "/results/jit-1",
            "--rounds", "6", "--runs", "5", "--timeout", "600",
        ],
        "interp": command_base + [
            "--engine", "interp", "--firmware", REMOTE_FIRMWARE,
            "--backend", REMOTE_BACKEND,
            "--output", REMOTE_STAGE + "/results/interp-1",
            "--rounds", "6", "--runs", "5", "--timeout", "600",
        ],
        "outputs": {
            "jit": REMOTE_STAGE + "/results/jit-1/evidence.json",
            "interp": REMOTE_STAGE + "/results/interp-1/evidence.json",
        },
    }

    BUILD.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="rows-stage-", dir=BUILD) as name:
        staging = Path(name)
        for relative, source in sources.items():
            destination = staging / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
        (staging / "commands.json").write_text(
            json.dumps(commands, indent=2) + "\n"
        )
        deployment = {
            "scope": "stopped Wolf copied/direct target cohort inputs; no run",
            "task": "G057-WLF-003 / TODO 8b",
            "remote_host": REMOTE_HOST,
            "remote_stage": REMOTE_STAGE,
            "external_paths": {
                "firmware": REMOTE_FIRMWARE,
                "firmware_elf": str(Path(REMOTE_FIRMWARE).with_suffix(".elf")),
                "backend": REMOTE_BACKEND,
            },
            "pins": PINS,
            "commands": commands,
            "profile_required": False,
            "backend_loaded": False,
            "emulator_started": False,
            "lease_requested": False,
        }
        (staging / "deployment.json").write_text(
            json.dumps(deployment, indent=2) + "\n"
        )
        manifest_files = sorted(
            path for path in staging.rglob("*") if path.is_file()
        )
        (staging / "MANIFEST.sha256").write_text("".join(
            f"{sha(path)}  {path.relative_to(staging)}\n"
            for path in manifest_files
        ))
        run([
            "ssh", "-o", "BatchMode=yes", REMOTE_HOST,
            "mkdir -p " + remote_temporary,
        ])
        run(["rsync", "-a", str(staging) + "/",
             REMOTE_HOST + ":" + remote_temporary + "/"])

    verify_command = (
        "set -eu; cd " + remote_temporary +
        "; sha256sum --check --status MANIFEST.sha256" +
        "; test \"$(sha256sum " + REMOTE_FIRMWARE + " | cut -d' ' -f1)\" = " +
        PINS["firmware"] +
        "; test \"$(sha256sum " + str(Path(REMOTE_FIRMWARE).with_suffix(".elf")) +
        " | cut -d' ' -f1)\" = " + PINS["firmware_elf"] +
        "; test \"$(sha256sum " + REMOTE_BACKEND + " | cut -d' ' -f1)\" = " +
        PINS["backend"] +
        "; " + REMOTE_ROOT + "/.venv/bin/python -m py_compile target.py qualify_rows.py" +
        "; " + REMOTE_ROOT + "/.venv/bin/python qualify_rows.py --help >/dev/null" +
        "; test ! -e results; mv " + remote_temporary + " " + REMOTE_STAGE
    )
    run(["ssh", "-o", "BatchMode=yes", REMOTE_HOST, verify_command])

    remote_manifest = run([
        "ssh", "-o", "BatchMode=yes", REMOTE_HOST,
        "cd " + REMOTE_STAGE + " && sha256sum --check MANIFEST.sha256",
    ], stdout=subprocess.PIPE, text=True)
    receipt = {
        "scope": "verified stopped Oryx input deployment; no target execution",
        "task": "G057-WLF-003 / TODO 8b",
        "remote_host": REMOTE_HOST,
        "remote_stage": REMOTE_STAGE,
        "commands_path": REMOTE_STAGE + "/commands.json",
        "jit_output": commands["outputs"]["jit"],
        "interp_output": commands["outputs"]["interp"],
        "external_pins": PINS,
        "remote_manifest": remote_manifest.stdout.splitlines(),
        "backend_loaded": False,
        "emulator_started": False,
        "lease_requested": False,
        "ready_for_central_request": True,
    }
    destination = BUILD / "rows-target-oryx-staging.json"
    destination.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    import sys as _fw_sys
    from pathlib import Path as _FWPath
    _fw_sys.path.insert(0, str(_FWPath(__file__).resolve().parents[3] / "tools"))
    from wolf_firmware import legacy_exception
    legacy_exception(_fw_sys.argv, 'agonport/vdplet/qualification/stage_rows_target_oryx.py')

    main()
