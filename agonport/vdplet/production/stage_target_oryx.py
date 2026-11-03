#!/usr/bin/env python3
"""Stage the stopped production Wolf3D VDPlet target gate on Oryx."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile


HERE = Path(__file__).resolve().parent
BUILD = HERE / "build"
FIXTURE = BUILD / "target-fixture"
TARGET_DRIVER = HERE.parent / "qualification/target.py"
REMOTE_HOST = "oryx-linuxlite"
REMOTE_ROOT = "/home/smith/Agon/mystuff/Wolf3dOrig"
REMOTE_STAGE = REMOTE_ROOT + "/agonport/vdplet/production/target-r2"
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
    "module": "266f809ff76e56733251da202e5c4747cd9c12d247d799d486471a262c0404b7",
    "full_frame": "a20c0387435f480ff7b551896d4cc02c0539bac40a6af3753148252fb81fdaf6",
    "retry_frame": "43dd54619cca5051bdf85a0bbde5907a2b4a4678927177d2d331510861a84b75",
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(command: list[object], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run([str(value) for value in command], check=True, **kwargs)


def main() -> None:
    sources = {
        "qualify.py": HERE / "qualify.py",
        "target.py": TARGET_DRIVER,
        "build/wolf3d_production.vdpl": BUILD / "wolf3d_production.vdpl",
    }
    for path in sorted(FIXTURE.iterdir()):
        if path.is_file():
            sources[f"build/target-fixture/{path.name}"] = path
    for relative, source in sources.items():
        if not source.is_file():
            raise SystemExit(f"missing staging input {relative}: {source}")
    for relative, expected in (
        ("build/wolf3d_production.vdpl", PINS["module"]),
        ("build/target-fixture/expected-full.bin", PINS["full_frame"]),
        ("build/target-fixture/expected-retry.bin", PINS["retry_frame"]),
    ):
        actual = sha(sources[relative])
        if actual != expected:
            raise SystemExit(f"local pin mismatch {relative}: {actual} != {expected}")

    remote_temporary = REMOTE_STAGE + f".tmp-{os.getpid()}"
    run([
        "ssh", "-o", "BatchMode=yes", REMOTE_HOST,
        "test ! -e " + REMOTE_STAGE + " && test ! -e " + remote_temporary,
    ])
    command = [
        REMOTE_ROOT + "/.venv/bin/python",
        REMOTE_STAGE + "/qualify.py",
        "--engine", "jit",
        "--firmware", REMOTE_FIRMWARE,
        "--backend", REMOTE_BACKEND,
        "--output", REMOTE_STAGE + "/results/jit-1",
        "--timeout", "600",
    ]

    BUILD.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="production-target-", dir=BUILD) as name:
        staging = Path(name)
        for relative, source in sources.items():
            destination = staging / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
        commands = {
            "policy": (
                "One finite headless JIT process under a self-service Oryx lease; "
                "stop on first failure and release before offline analysis."
            ),
            "jit": command,
            "output": REMOTE_STAGE + "/results/jit-1/evidence.json",
        }
        (staging / "commands.json").write_text(json.dumps(commands, indent=2) + "\n")
        (staging / "MANIFEST.sha256").write_text("".join(
            f"{sha(path)}  {path.relative_to(staging)}\n"
            for path in sorted(staging.rglob("*")) if path.is_file()
        ))
        run(["ssh", "-o", "BatchMode=yes", REMOTE_HOST,
             "mkdir -p " + remote_temporary])
        run(["rsync", "-a", str(staging) + "/",
             REMOTE_HOST + ":" + remote_temporary + "/"])

    firmware_elf = str(Path(REMOTE_FIRMWARE).with_suffix(".elf"))
    verify = (
        "set -eu; cd " + remote_temporary +
        "; sha256sum --check --status MANIFEST.sha256" +
        "; test \"$(sha256sum " + REMOTE_FIRMWARE + " | cut -d' ' -f1)\" = " +
        PINS["firmware"] +
        "; test \"$(sha256sum " + firmware_elf + " | cut -d' ' -f1)\" = " +
        PINS["firmware_elf"] +
        "; test \"$(sha256sum " + REMOTE_BACKEND + " | cut -d' ' -f1)\" = " +
        PINS["backend"] +
        "; " + REMOTE_ROOT + "/.venv/bin/python -m py_compile target.py qualify.py" +
        "; " + REMOTE_ROOT + "/.venv/bin/python qualify.py --help >/dev/null" +
        "; test ! -e results; mv " + remote_temporary + " " + REMOTE_STAGE
    )
    run(["ssh", "-o", "BatchMode=yes", REMOTE_HOST, verify])

    observed = run([
        "ssh", "-o", "BatchMode=yes", REMOTE_HOST, "sha256sum",
        REMOTE_FIRMWARE, firmware_elf, REMOTE_BACKEND,
        REMOTE_STAGE + "/build/wolf3d_production.vdpl",
        REMOTE_STAGE + "/build/target-fixture/expected-full.bin",
        REMOTE_STAGE + "/build/target-fixture/expected-retry.bin",
    ], stdout=subprocess.PIPE, text=True).stdout.splitlines()
    remote_hashes = {line.split()[1]: line.split()[0] for line in observed}
    expected_remote = {
        REMOTE_FIRMWARE: PINS["firmware"],
        firmware_elf: PINS["firmware_elf"],
        REMOTE_BACKEND: PINS["backend"],
        REMOTE_STAGE + "/build/wolf3d_production.vdpl": PINS["module"],
        REMOTE_STAGE + "/build/target-fixture/expected-full.bin": PINS["full_frame"],
        REMOTE_STAGE + "/build/target-fixture/expected-retry.bin": PINS["retry_frame"],
    }
    if remote_hashes != expected_remote:
        raise AssertionError({"observed": remote_hashes, "expected": expected_remote})

    receipt = {
        "scope": "verified stopped production Wolf target gate; no emulator run",
        "remote_host": REMOTE_HOST,
        "remote_stage": REMOTE_STAGE,
        "command": command,
        "output": REMOTE_STAGE + "/results/jit-1/evidence.json",
        "pins": PINS,
        "staged_file_count": len(sources) + 2,
        "backend_loaded": False,
        "emulator_started": False,
        "lease_requested": False,
        "expected_maximum_seconds": 60,
        "ready_for_self_service_reservation": True,
    }
    (BUILD / "target-staging.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
