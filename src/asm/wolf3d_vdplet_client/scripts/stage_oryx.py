#!/usr/bin/env python3
"""Stage the stopped production-client Oryx profile without launching it."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shlex
import subprocess


HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[3]
PACKAGE = HERE.parent / "tgt/package"
REMOTE_ROOT = "/home/smith/Agon/mystuff/Wolf3dOrig"
REMOTE_CLIENT = REMOTE_ROOT + "/src/asm/wolf3d_vdplet_client"
REMOTE_PROFILE = REMOTE_ROOT + "/.emulator/vdplet-client"


def run(command: list[object], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run([str(value) for value in command], check=True, **kwargs)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--target-status",
        default="pending fresh central Oryx grant",
        help="gate state recorded in the stopped-profile receipt",
    )
    arguments = parser.parse_args()
    if not (PACKAGE / "expected.json").is_file():
        raise SystemExit("build the client fixture before staging")
    run(["ssh", "-o", "BatchMode=yes", "oryx-linuxlite",
         "mkdir", "-p", REMOTE_CLIENT + "/tgt/package",
         REMOTE_CLIENT + "/scripts"])
    run(["rsync", "-a", "--delete", str(PACKAGE) + "/",
         "oryx-linuxlite:" + REMOTE_CLIENT + "/tgt/package/"])
    run(["rsync", "-a", HERE / "prepare_profile.py", HERE / "rehearse.py",
         "oryx-linuxlite:" + REMOTE_CLIENT + "/scripts/"])
    run(["rsync", "-a", PROJECT / "agonport/vdplet/review/sdl_review.c",
         "oryx-linuxlite:" + REMOTE_CLIENT + "/scripts/"])
    prepare_command = [
        REMOTE_ROOT + "/.venv/bin/python",
        REMOTE_CLIENT + "/scripts/prepare_profile.py",
        "--package", REMOTE_CLIENT + "/tgt/package",
        "--target-status", arguments.target_status,
    ]
    result = run([
        "ssh", "-o", "BatchMode=yes", "oryx-linuxlite",
        shlex.join(prepare_command),
    ], stdout=subprocess.PIPE, text=True)
    receipt = json.loads(result.stdout)
    run([
        "ssh", "-o", "BatchMode=yes", "oryx-linuxlite",
        "cc -std=c11 -O2 -Wall -Wextra -Werror -shared -fPIC"
        + " -I/home/smith/.local/include " + REMOTE_CLIENT + "/scripts/sdl_review.c"
        + " -ldl -o " + REMOTE_PROFILE + "/review-input.so"
        + " && " + REMOTE_ROOT + "/.venv/bin/python -m py_compile "
        + REMOTE_CLIENT + "/scripts/rehearse.py",
    ])
    run([
        "ssh", "-o", "BatchMode=yes", "oryx-linuxlite",
        "cd " + REMOTE_PROFILE
        + " && bash -n flexe-agon-emulator"
        + " && sha256sum --check --status .runtime.sha256"
        + " && test -x flexe-agon-emulator"
        + " && test -f sdcard/wolfclient/source/wolf3d_vdplet_client.inc"
        + " && test \"$(head -1 sdcard/autoexec.txt | tr -d '\\r')\""
        + " = 'SET KEYBOARD 1'",
    ])
    if not receipt.get("stopped") or receipt.get("GUI_launched"):
        raise AssertionError(receipt)
    local_receipt = HERE.parent / "tgt/staging.json"
    local_receipt.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({
        "profile": receipt["profile"],
        "launcher": receipt["launcher"],
        "stopped": receipt["stopped"],
        "client_sha256": receipt["client_sha256"],
        "module_sha256": receipt["module_sha256"],
        "source_visible": receipt["source_visible"],
        "GUI_launched": receipt["GUI_launched"],
    }, indent=2))


if __name__ == "__main__":
    import sys as _fw_sys
    from pathlib import Path as _FWPath
    _fw_sys.path.insert(0, str(_FWPath(__file__).resolve().parents[4] / "tools"))
    from wolf_firmware import legacy_exception
    legacy_exception(_fw_sys.argv, 'src/asm/wolf3d_vdplet_client/scripts/stage_oryx.py')

    main()
