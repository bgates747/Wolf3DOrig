#!/usr/bin/env python3
"""Stage every stopped Wolf3D acceptance profile on Oryx."""

from __future__ import annotations

import json
from pathlib import Path
import shlex
import subprocess


HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[3]
TARGET = HERE.parent / "tgt"
SCENARIOS = (
    "pushwall",
    "ordinary-transition",
    "secret-transition",
    "hans",
    "victory",
    "ghosts",
    "pause-resume",
    "highscore-qualifying",
    "highscore-nonqualifying",
)
REMOTE_ROOT = "/home/smith/Agon/mystuff/Wolf3dOrig"
REMOTE_ACCEPTANCE = REMOTE_ROOT + "/src/asm/wolf3d_acceptance"
REMOTE_APP = REMOTE_ROOT + "/src/asm/wolf3d_vdplet_app"
REMOTE_PROFILES = REMOTE_ROOT + "/.emulator/wolf3d-acceptance-r01"


def run(command: list[object], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run([str(value) for value in command], check=True, **kwargs)


def main() -> None:
    for scenario in SCENARIOS:
        if not (TARGET / scenario / "expected.json").is_file():
            raise SystemExit(
                f"missing {scenario} payload; run acceptance prepare.py first"
            )

    run([
        "ssh", "-o", "BatchMode=yes", "oryx-linuxlite", "mkdir", "-p",
        REMOTE_ACCEPTANCE + "/tgt",
        REMOTE_APP + "/scripts",
        REMOTE_PROFILES,
    ])
    run([
        "rsync", "-a", "--delete", str(TARGET) + "/",
        "oryx-linuxlite:" + REMOTE_ACCEPTANCE + "/tgt/",
    ])
    run([
        "rsync", "-a",
        PROJECT / "src/asm/wolf3d_vdplet_app/scripts/prepare_profile.py",
        "oryx-linuxlite:" + REMOTE_APP + "/scripts/",
    ])

    receipts: list[dict[str, object]] = []
    for scenario in SCENARIOS:
        command = [
            REMOTE_ROOT + "/.venv/bin/python",
            REMOTE_APP + "/scripts/prepare_profile.py",
            "--package", REMOTE_ACCEPTANCE + "/tgt/" + scenario,
            "--profile", REMOTE_PROFILES + "/" + scenario,
        ]
        result = run([
            "ssh", "-o", "BatchMode=yes", "oryx-linuxlite",
            shlex.join(command),
        ], stdout=subprocess.PIPE, text=True)
        receipt = json.loads(result.stdout)
        if not receipt.get("stopped") or receipt.get("GUI_launched"):
            raise AssertionError(receipt)
        profile = REMOTE_PROFILES + "/" + scenario
        run([
            "ssh", "-o", "BatchMode=yes", "oryx-linuxlite",
            "cd " + shlex.quote(profile)
            + " && bash -n flexe-agon-emulator"
            + " && sha256sum --check --status .runtime.sha256"
            + " && test -x flexe-agon-emulator",
        ])
        receipts.append(receipt)

    staging = {
        "scope": "stopped Wolf3DOrig visual-acceptance cohort",
        "profiles": receipts,
        "GUI_launched": False,
    }
    (TARGET / "staging.json").write_text(json.dumps(staging, indent=2) + "\n")
    print(json.dumps(staging, indent=2))


if __name__ == "__main__":
    main()
