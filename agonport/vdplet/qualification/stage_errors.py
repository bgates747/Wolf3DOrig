#!/usr/bin/env python3
"""Stage the stopped bounded error-path target candidate on Oryx."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess


HERE = Path(__file__).resolve().parent
BUILD = HERE / "build"
REMOTE = "/home/smith/Agon/mystuff/Wolf3dOrig/agonport/vdplet/qualification/error-target"
FIRMWARE = "/home/smith/Agon/mystuff/agon-vdplet/build/vdpl-010/pixels/firmware.bin"
ELF = "/home/smith/Agon/mystuff/agon-vdplet/build/vdpl-010/pixels/firmware.elf"
BACKEND = "/home/smith/Agon/mystuff/agon-vdplet/build/vdpl-010/runtime/flexe-vdp.so"

EXPECTED = {
    FIRMWARE: "b42ae55f69900c44acacfbf0d665ef278e87b277b3b9fd4208e17ebf378f74b6",
    ELF: "a10f7989d5c1f9974fc999428865ca74771fb65a0d4d694a2ac2b81c19df9902",
    BACKEND: "108ec5b02122381e6c3ae851508188ec0a96240ca5f74be804fd2201b141e6e9",
}


def run(command: list[object], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run([str(value) for value in command], check=True, **kwargs)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    required = [
        HERE / "target.py",
        HERE / "qualify_errors.py",
        BUILD / "wolf3d_scene.vdpl",
        BUILD / "oracle-frame.bin",
        BUILD / "fixture/workspace.bin",
        BUILD / "fixture/map.bin",
        BUILD / "fixture/textures.bin",
        BUILD / "fixture/config.bin",
    ]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise SystemExit("Run the pinned host build first:\n" + "\n".join(missing))

    run(["ssh", "-o", "BatchMode=yes", "oryx-linuxlite", "mkdir", "-p",
         REMOTE + "/build/fixture"])
    run(["rsync", "-a", HERE / "target.py", HERE / "qualify_errors.py",
         "oryx-linuxlite:" + REMOTE + "/"])
    run(["rsync", "-a", BUILD / "wolf3d_scene.vdpl",
         BUILD / "oracle-frame.bin", "oryx-linuxlite:" + REMOTE + "/build/"])
    run(["rsync", "-a", BUILD / "fixture/workspace.bin",
         BUILD / "fixture/map.bin", BUILD / "fixture/textures.bin",
         BUILD / "fixture/config.bin",
         "oryx-linuxlite:" + REMOTE + "/build/fixture/"])

    remote_paths = [*EXPECTED, *(
        REMOTE + "/" + relative for relative in (
            "target.py", "qualify_errors.py", "build/wolf3d_scene.vdpl",
            "build/oracle-frame.bin", "build/fixture/workspace.bin",
            "build/fixture/map.bin", "build/fixture/textures.bin",
            "build/fixture/config.bin",
        )
    )]
    result = run(
        ["ssh", "-o", "BatchMode=yes", "oryx-linuxlite", "sha256sum",
         *remote_paths], stdout=subprocess.PIPE, text=True,
    )
    observed = {}
    for line in result.stdout.splitlines():
        digest, path = line.split(maxsplit=1)
        observed[path] = digest
    for path, digest in EXPECTED.items():
        if observed.get(path) != digest:
            raise AssertionError(f"runtime pin mismatch: {path}")

    local_expected = {
        REMOTE + "/target.py": sha(HERE / "target.py"),
        REMOTE + "/qualify_errors.py": sha(HERE / "qualify_errors.py"),
        REMOTE + "/build/wolf3d_scene.vdpl": sha(BUILD / "wolf3d_scene.vdpl"),
        REMOTE + "/build/oracle-frame.bin": sha(BUILD / "oracle-frame.bin"),
        REMOTE + "/build/fixture/workspace.bin": sha(BUILD / "fixture/workspace.bin"),
        REMOTE + "/build/fixture/map.bin": sha(BUILD / "fixture/map.bin"),
        REMOTE + "/build/fixture/textures.bin": sha(BUILD / "fixture/textures.bin"),
        REMOTE + "/build/fixture/config.bin": sha(BUILD / "fixture/config.bin"),
    }
    for path, digest in local_expected.items():
        if observed.get(path) != digest:
            raise AssertionError(f"staged input mismatch: {path}")

    command = (
        f"cd {REMOTE} && "
        "/home/smith/Agon/mystuff/Wolf3dOrig/.venv/bin/python "
        f"qualify_errors.py --engine jit --firmware {FIRMWARE} "
        f"--backend {BACKEND}"
    )
    receipt = {
        "scope": "stopped bounded Wolf error-path target candidate",
        "profile": REMOTE,
        "command": command,
        "stopped": True,
        "GUI_launched": False,
        "expected_seconds": 15,
        "pins": observed,
    }
    (BUILD / "error-staging.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({
        "profile": REMOTE,
        "stopped": True,
        "module_sha256": observed[REMOTE + "/build/wolf3d_scene.vdpl"],
        "qualifier_sha256": observed[REMOTE + "/qualify_errors.py"],
        "firmware_sha256": observed[FIRMWARE],
        "backend_sha256": observed[BACKEND],
        "expected_seconds": 15,
    }, indent=2))


if __name__ == "__main__":
    import sys as _fw_sys
    from pathlib import Path as _FWPath
    _fw_sys.path.insert(0, str(_FWPath(__file__).resolve().parents[3] / "tools"))
    from wolf_firmware import legacy_exception
    legacy_exception(_fw_sys.argv, 'agonport/vdplet/qualification/stage_errors.py')

    main()
