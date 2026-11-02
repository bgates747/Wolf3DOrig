#!/usr/bin/env python3
"""Stage the isolated Wolf audio-ring profile on Oryx and leave it stopped."""

from __future__ import annotations

import json
from pathlib import Path
import shlex
import subprocess


HERE = Path(__file__).resolve().parent
REMOTE_TASK = "/home/smith/Agon/mystuff/Wolf3dOrig/agonport/vdplet/audio-ring"
REMOTE_PROFILE = "/home/smith/Agon/mystuff/Wolf3dOrig/.emulator/wolf3d-vdplet-audio-ring-r02"


def run(command: list[object], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run([str(value) for value in command], check=True, **kwargs)


def main() -> None:
    run(["ssh", "-o", "BatchMode=yes", "oryx-linuxlite", "mkdir", "-p", REMOTE_TASK])
    run([
        "rsync", "-a", "--delete", str(HERE) + "/",
        "oryx-linuxlite:" + REMOTE_TASK + "/",
    ])
    command = [
        "/home/smith/Agon/mystuff/Wolf3dOrig/.venv/bin/python",
        REMOTE_TASK + "/prepare_profile.py",
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
        " && test -d ring-output"
        " && test -z \"$(find ring-output -mindepth 1 -maxdepth 1 -print -quit)\""
        " && grep -Fqx 'export FLEXE_RING_WINDOW_AFTER_MS=\"90000\"' flexe-agon-emulator"
        " && ! grep -q 'FLEXE_UART_OBSERVER_OUTPUT' flexe-agon-emulator"
    )
    run(["ssh", "-o", "BatchMode=yes", "oryx-linuxlite", verify])
    required = {
        "stopped": True,
        "emulator_launched": False,
        "audio_device_opened": False,
        "reservation_created": False,
        "application_sha256": "5723cd60234e46a8c34809fa8fba5f5286058f3cf7ad9d5bfc27c9f72a4d4ae7",
        "module_sha256": "12449bab795f4fd8ecfbbb2f4c547299632bba9bda88dc7ebf4e68160aac9c63",
        "backend_sha256": "0f4bdc1b663374720d1b7ea208507238358bbd8568be28c109a3030959f117a2",
        "observer_directory_empty": True,
        "observer_window_after_ms": 90000,
    }
    for key, expected in required.items():
        if receipt.get(key) != expected:
            raise AssertionError(f"{key}: {receipt.get(key)!r} != {expected!r}")
    (HERE / "staging.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
