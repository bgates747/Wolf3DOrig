#!/usr/bin/env python3
"""Later build/stage helper for the stopped direct-row Oryx review.

This script mutates a project-local Oryx profile and therefore must not be run
until both target receipts pass and Golem grants the staging step.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import shutil
import subprocess


HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[2]
BUILD = HERE / "build"
REMOTE_ROOT = "/home/smith/Agon/mystuff/Wolf3dOrig"
REMOTE_REVIEW = REMOTE_ROOT + "/agonport/vdplet/review-rows"
REMOTE_PROFILE = REMOTE_ROOT + "/.emulator/vdplet-rows-review"


def run(command: list[object], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run([str(value) for value in command], check=True, **kwargs)


def load_review_builder():
    spec = importlib.util.spec_from_file_location(
        "wolf_rows_review_builder", HERE / "build.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def main() -> None:
    builder = load_review_builder()
    local_asm = BUILD / "asm"
    local_asm.mkdir(parents=True, exist_ok=True)
    (local_asm / "review.asm").write_text(builder.direct_guest_source())
    shutil.copyfile(
        "/Agon/mystuff/golem/reference/agnb-asm/lib/mos_api.inc",
        local_asm / "mos_api.inc",
    )
    run(["ssh", "-o", "BatchMode=yes", "oryx-linuxlite",
         "mkdir", "-p", REMOTE_REVIEW + "/build/asm",
         REMOTE_REVIEW + "/build/package"])
    run(["rsync", "-a", local_asm / "review.asm",
         "oryx-linuxlite:" + REMOTE_REVIEW + "/build/asm/review.asm"])
    run(["rsync", "-a", local_asm / "mos_api.inc",
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
    run(["rsync", "-a", HERE / "rehearse.py",
         HERE / "../review/sdl_review.c",
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
        + " && test -f sdcard/wolfrows/source/wolf3d_scene_rows.cpp"
        + " && test -f sdcard/wolfrows/source/wolf3d_scene.cpp"
        + " && test -f sdcard/wolfrows/reference.png"
        + " && test -f review-input.so",
    ])
    if not receipt.get("stopped") or receipt.get("GUI_launched"):
        raise AssertionError(receipt)
    helper = run([
        "ssh", "-o", "BatchMode=yes", "oryx-linuxlite",
        "sha256sum", REMOTE_PROFILE + "/review-input.so",
        REMOTE_REVIEW + "/rehearse.py",
    ], stdout=subprocess.PIPE, text=True).stdout.splitlines()
    receipt["rehearsal_inputs"] = helper
    (BUILD / "staging.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
