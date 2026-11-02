#!/usr/bin/env python3
"""Stage the corrected late profile under live FIFO custody; never launch it."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shlex
import subprocess


HERE = Path(__file__).resolve().parent
TASK = HERE.parent
VDPLET = TASK.parent
LEASE_TOOL = Path("/Agon/mystuff/agon-dev-env/cross-agent/vdplet-rollout/oryx_lease.py")
LEASE_PYTHON = Path("/Agon/mystuff/agon-dev-env/.venv/bin/python")
CENTRAL_RUN = Path("/Agon/mystuff/agon-dev-env/cross-agent/vdplet-rollout/wolf-ring-late-corrected-run-v1.md")
REMOTE_TASK = "/home/smith/Agon/mystuff/Wolf3dOrig/agonport/vdplet/audio-ring-late-corrected"
REMOTE_TARGET = REMOTE_TASK + "/target"
REMOTE_PROFILE = "/home/smith/Agon/mystuff/Wolf3dOrig/.emulator/wolf3d-vdplet-audio-ring-late-corrected-r01"


def run(command: list[object], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run([str(value) for value in command], check=True, **kwargs)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lease", required=True)
    args = parser.parse_args()
    run([
        LEASE_PYTHON, LEASE_TOOL, "assert-owner",
        "--owner", "wolf3dorig", "--lease", args.lease,
    ])

    run(["ssh", "-o", "BatchMode=yes", "oryx-linuxlite", "mkdir", "-p", REMOTE_TARGET])
    run(["rsync", "-a", "--delete", str(TASK) + "/", "oryx-linuxlite:" + REMOTE_TASK + "/"])
    run([
        "rsync", "-a", str(VDPLET / "audio-ring/staging.json"),
        "oryx-linuxlite:" + REMOTE_TARGET + "/accepted-old-staging.json",
    ])
    run([
        "rsync", "-a", str(VDPLET / "audio-ring-startup/staging.json"),
        "oryx-linuxlite:" + REMOTE_TARGET + "/accepted-corrected-staging.json",
    ])
    run([
        "rsync", "-a", CENTRAL_RUN,
        "oryx-linuxlite:" + REMOTE_TARGET + "/accepted-central-run.md",
    ])
    command = [
        "/home/smith/Agon/mystuff/Wolf3dOrig/.venv/bin/python",
        REMOTE_TARGET + "/prepare_profile.py",
    ]
    result = run(
        ["ssh", "-o", "BatchMode=yes", "oryx-linuxlite", shlex.join(command)],
        text=True, stdout=subprocess.PIPE,
    )
    receipt = json.loads(result.stdout)
    verify = (
        f"cd {shlex.quote(REMOTE_PROFILE)}"
        " && bash -n flexe-agon-emulator"
        " && sha256sum --check --status .runtime.sha256"
        " && test -x runner.py"
        " && test -x read_residence.py"
        " && test -d ring-output-late-corrected"
        " && test -z \"$(find ring-output-late-corrected -mindepth 1 -maxdepth 1 -print -quit)\""
        " && grep -Fqx 'export FLEXE_RING_WINDOW_AFTER_MS=\"90000\"' flexe-agon-emulator"
        " && ! grep -q 'FLEXE_UART_OBSERVER_OUTPUT' flexe-agon-emulator"
    )
    run(["ssh", "-o", "BatchMode=yes", "oryx-linuxlite", verify])
    required = {
        "stopped": True,
        "emulator_launched": False,
        "audio_device_opened": False,
        "build_performed": False,
        "measurement_mode": "late-corrected",
        "backend_sha256": "943f432fecb96689f3a0d2ae80c72d08e20903dfe2a58a00ba88d8c7727ad400",
        "runner_sha256": "f0ffe79892f9a93edc41f590bb02551583580e899b7232545253b1141962ca98",
        "oracle_sha256": "ea4f7e644d3fb8ba21ab2545007e12f501113f22c980205d8fe4963d060f0b8d",
        "observer_directory_empty": True,
        "observer_window_after_ms": 90000,
        "shot_overlap_required": True,
        "initial_empty_history_required": False,
        "runtime_differences_from_old_r02": ["flexe-agon-emulator", "flexe-vdp.so"],
    }
    for key, expected in required.items():
        if receipt.get(key) != expected:
            raise AssertionError(f"{key}: {receipt.get(key)!r} != {expected!r}")
    (HERE / "staging.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
