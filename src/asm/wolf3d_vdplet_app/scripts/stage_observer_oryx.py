#!/usr/bin/env python3
"""Stage the stopped FX-114 Wolf3D UART-observer cohort on Oryx; never run it."""

from __future__ import annotations

import json
from pathlib import Path
import shlex
import subprocess


HERE = Path(__file__).resolve().parent
PACKAGE = HERE.parent / "tgt/package"
REMOTE_ROOT = "/home/smith/Agon/mystuff/Wolf3dOrig"
REMOTE_PROJECT = REMOTE_ROOT + "/src/asm/wolf3d_vdplet_app"
REMOTE_PROFILE = REMOTE_ROOT + "/.emulator/wolf3d-vdplet-app-observed-r01"
REMOTE_FRONTEND = (
    "/home/smith/Agon/mystuff/flexe-agon-emulator/build/fx114/"
    "candidate-r02/flexe-agon-emulator"
)
REMOTE_READER = (
    "/home/smith/Agon/mystuff/flexe-agon-emulator/build/fx114/"
    "contract-r02/read_record.py"
)
REMOTE_EVIDENCE = REMOTE_ROOT + "/agonport/emulator/evidence/uart-observer-r01"
REMOTE_RECORD = REMOTE_EVIDENCE + "/wolf3d-uart-observer.jsonl"
FRONTEND_SHA256 = (
    "7e7d0e1bc89af72bde7ffbd6c06446aaefda4d1803f89eb1faf3167307ee1e01"
)
READER_SHA256 = (
    "12817411df487931407d1ec7cf4e51c9742a5f350582af2efce5db3fb4a96cde"
)


def run(command: list[object], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run([str(value) for value in command], check=True, **kwargs)


def main() -> None:
    if not (PACKAGE / "expected.json").is_file():
        raise SystemExit("prepare the VDPlet application package before staging")
    run([
        "ssh", "-o", "BatchMode=yes", "oryx-linuxlite", "mkdir", "-p",
        REMOTE_PROJECT + "/tgt/package", REMOTE_PROJECT + "/scripts",
        REMOTE_EVIDENCE,
    ])
    remote_admission = (
        f"test ! -e {shlex.quote(REMOTE_RECORD)}"
        f" && echo '{FRONTEND_SHA256}  {REMOTE_FRONTEND}' | sha256sum -c --status"
        f" && echo '{READER_SHA256}  {REMOTE_READER}' | sha256sum -c --status"
    )
    run(["ssh", "-o", "BatchMode=yes", "oryx-linuxlite", remote_admission])
    run([
        "rsync", "-a", "--delete", str(PACKAGE) + "/",
        "oryx-linuxlite:" + REMOTE_PROJECT + "/tgt/package/",
    ])
    run([
        "rsync", "-a", HERE / "prepare_profile.py",
        "oryx-linuxlite:" + REMOTE_PROJECT + "/scripts/",
    ])
    command = [
        REMOTE_ROOT + "/.venv/bin/python",
        REMOTE_PROJECT + "/scripts/prepare_profile.py",
        "--package", REMOTE_PROJECT + "/tgt/package",
        "--profile", REMOTE_PROFILE,
        "--frontend", REMOTE_FRONTEND,
        "--frontend-sha256", FRONTEND_SHA256,
        "--observer-output", REMOTE_RECORD,
    ]
    result = run([
        "ssh", "-o", "BatchMode=yes", "oryx-linuxlite", shlex.join(command),
    ], stdout=subprocess.PIPE, text=True)
    receipt = json.loads(result.stdout)
    run([
        "ssh", "-o", "BatchMode=yes", "oryx-linuxlite",
        "cd " + REMOTE_PROFILE
        + " && bash -n flexe-agon-emulator"
        + " && sha256sum --check --status .runtime.sha256"
        + " && test -x flexe-agon-emulator"
        + " && grep -Fqx 'export FLEXE_UART_OBSERVER_OUTPUT=\""
        + REMOTE_RECORD + "\"' flexe-agon-emulator",
    ])
    if (
        not receipt.get("stopped")
        or receipt.get("GUI_launched")
        or not receipt.get("observer_enabled")
        or receipt.get("observer_output") != REMOTE_RECORD
        or receipt.get("frontend_sha256") != FRONTEND_SHA256
    ):
        raise AssertionError(receipt)
    (HERE.parent / "tgt/observer-staging.json").write_text(
        json.dumps(receipt, indent=2) + "\n"
    )
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
