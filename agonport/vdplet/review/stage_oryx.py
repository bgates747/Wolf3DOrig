#!/usr/bin/env python3
"""Build and stage the stopped Oryx review profile without launching it."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess


HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[2]
BUILD = HERE / "build"
REMOTE_ROOT = "/home/smith/Agon/mystuff/Wolf3dOrig"
REMOTE_REVIEW = REMOTE_ROOT + "/agonport/vdplet/review"
REMOTE_PROFILE = REMOTE_ROOT + "/.emulator/vdplet-review"


def run(command: list[object], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run([str(value) for value in command], check=True, **kwargs)


def main() -> None:
    run(["ssh", "-o", "BatchMode=yes", "oryx-linuxlite",
         "mkdir", "-p", REMOTE_REVIEW + "/build/asm",
         REMOTE_REVIEW + "/build/package"])
    run(["rsync", "-a", HERE / "review_guest.asm",
         "oryx-linuxlite:" + REMOTE_REVIEW + "/build/asm/review.asm"])
    run(["rsync", "-a",
         "/Agon/mystuff/golem/reference/agnb-asm/lib/mos_api.inc",
         "oryx-linuxlite:" + REMOTE_REVIEW + "/build/asm/mos_api.inc"])
    run([
        "ssh", "-o", "BatchMode=yes", "oryx-linuxlite",
        "cd " + REMOTE_REVIEW + "/build/asm"
        + " && /home/smith/Agon/mystuff/trs-os-zds/.local/ez80asm"
        + " review.asm review.bin",
    ])
    BUILD.mkdir(parents=True, exist_ok=True)
    run(["rsync", "-a",
         "oryx-linuxlite:" + REMOTE_REVIEW + "/build/asm/review.bin",
         BUILD / "review.bin"])
    run([PROJECT / ".venv/bin/python", HERE / "build.py",
         "--guest-binary", BUILD / "review.bin"])
    run(["rsync", "-a", HERE / "prepare_profile.py",
         "oryx-linuxlite:" + REMOTE_REVIEW + "/prepare_profile.py"])
    run(["rsync", "-a", HERE / "rehearse.py", HERE / "sdl_review.c",
         "oryx-linuxlite:" + REMOTE_REVIEW + "/"])
    run(["rsync", "-a", "--delete", str(BUILD / "package") + "/",
         "oryx-linuxlite:" + REMOTE_REVIEW + "/build/package/"])

    result = run([
        "ssh", "-o", "BatchMode=yes", "oryx-linuxlite",
        REMOTE_ROOT + "/.venv/bin/python",
        REMOTE_REVIEW + "/prepare_profile.py",
        "--package", REMOTE_REVIEW + "/build/package",
    ], stdout=subprocess.PIPE, text=True)
    receipt = json.loads(result.stdout)
    run([
        "ssh", "-o", "BatchMode=yes", "oryx-linuxlite",
        "cc -std=c11 -O2 -Wall -Wextra -Werror -shared -fPIC"
        + " -I/home/smith/.local/include " + REMOTE_REVIEW + "/sdl_review.c"
        + " -ldl -o " + REMOTE_PROFILE + "/review-input.so"
        + " && " + REMOTE_ROOT + "/.venv/bin/python -m py_compile "
        + REMOTE_REVIEW + "/rehearse.py",
    ])
    run([
        "ssh", "-o", "BatchMode=yes", "oryx-linuxlite",
        "cd " + REMOTE_PROFILE
        + " && bash -n flexe-agon-emulator"
        + " && sha256sum --check --status .runtime.sha256"
        + " && test -x flexe-agon-emulator"
        + " && test -f sdcard/wolfvdpl/source/wolf3d_scene.cpp"
        + " && test -f sdcard/wolfvdpl/reference.png"
        + " && test \"$(head -1 sdcard/autoexec.txt | tr -d '\\r')\""
        + " = 'SET KEYBOARD 1'",
    ])
    if not receipt.get("stopped") or receipt.get("GUI_launched"):
        raise AssertionError(receipt)
    (BUILD / "staging.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({
        "profile": receipt["profile"],
        "launcher": receipt["launcher"],
        "stopped": receipt["stopped"],
        "source_visible": receipt["source_visible"],
        "reference_visible": receipt["reference_visible"],
        "module_sha256": receipt["module_sha256"],
        "review_binary_sha256": receipt["review_binary_sha256"],
        "GUI_launched": receipt["GUI_launched"],
    }, indent=2))


if __name__ == "__main__":
    main()
