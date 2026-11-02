#!/usr/bin/env python3
"""Stage the stopped full-game production-VDPlet profile on Oryx."""

from __future__ import annotations

import json
from pathlib import Path
import shlex
import subprocess


HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[3]
PACKAGE = HERE.parent / "tgt/package"
REMOTE_ROOT = "/home/smith/Agon/mystuff/Wolf3dOrig"
REMOTE_PROJECT = REMOTE_ROOT + "/src/asm/wolf3d_vdplet_app"
REMOTE_PROFILE = REMOTE_ROOT + "/.emulator/wolf3d-vdplet-app"


def run(command: list[object], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run([str(value) for value in command], check=True, **kwargs)


def main() -> None:
    if not (PACKAGE / "expected.json").is_file():
        raise SystemExit("prepare the VDPlet application package before staging")
    run([
        "ssh", "-o", "BatchMode=yes", "oryx-linuxlite", "mkdir", "-p",
        REMOTE_PROJECT + "/tgt/package", REMOTE_PROJECT + "/scripts",
    ])
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
        + " && test \"$(head -1 sdcard/autoexec.txt | tr -d '\\r')\""
        + " = 'SET KEYBOARD 1'",
    ])
    if not receipt.get("stopped") or receipt.get("GUI_launched"):
        raise AssertionError(receipt)
    (HERE.parent / "tgt/staging.json").write_text(
        json.dumps(receipt, indent=2) + "\n"
    )
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
