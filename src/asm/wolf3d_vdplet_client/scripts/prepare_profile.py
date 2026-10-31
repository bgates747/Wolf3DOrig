#!/usr/bin/env python3
"""Prepare the stopped canonical Oryx production-client profile; never launch it."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess


HOME = Path.home()
PROJECT = HOME / "Agon/mystuff/Wolf3dOrig"
PROFILE = PROJECT / ".emulator/vdplet-client"
DEFAULT_PACKAGE = PROJECT / "src/asm/wolf3d_vdplet_client/tgt/package"
CANONICAL = HOME / "Agon/mystuff/agon-dev-env/scripts/setup_emulator.py"
FAB_RUNTIME = HOME / "Agon/mystuff/golem/.emulator/runtime/fab-1.2.5"
FLEXE_FRONTEND = (
    HOME / "Agon/mystuff/golem/docs/tasks/GOLEM-037/binding/build/runtime/"
    "flexe-agon-emulator"
)
CANDIDATE = HOME / "Agon/mystuff/agon-vdplet/build/vdpl-010"
FIRMWARE = CANDIDATE / "pixels/firmware.bin"
FIRMWARE_ELF = CANDIDATE / "pixels/firmware.elf"
BACKEND = CANDIDATE / "runtime/flexe-vdp.so"

PINS = {
    "firmware.bin": "b42ae55f69900c44acacfbf0d665ef278e87b277b3b9fd4208e17ebf378f74b6",
    "firmware.elf": "a10f7989d5c1f9974fc999428865ca74771fb65a0d4d694a2ac2b81c19df9902",
    "flexe-vdp.so": "108ec5b02122381e6c3ae851508188ec0a96240ca5f74be804fd2201b141e6e9",
    "wolf3d.vdpl": "57b635fc1807d9108e576cfff4c79c7f57ade48164fc5be97d75a3562e54b1be",
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_canonical():
    spec = importlib.util.spec_from_file_location("agon_emulator_setup", CANONICAL)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def ensure_stopped(profile: Path) -> None:
    marker = str(profile / "sdcard").encode()
    for process in Path("/proc").glob("[0-9]*"):
        try:
            if marker in (process / "cmdline").read_bytes().split(b"\0"):
                raise SystemExit(f"Client profile is running as PID {process.name}")
        except OSError:
            continue


def verify_pin(path: Path, expected: str) -> None:
    actual = sha(path)
    if actual != expected:
        raise SystemExit(f"Pin mismatch for {path}: {actual} != {expected}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=Path, default=DEFAULT_PACKAGE)
    parser.add_argument(
        "--target-status",
        default="pending fresh central Oryx grant",
        help="durable gate state recorded in the stopped-profile receipt",
    )
    arguments = parser.parse_args()
    package = arguments.package.resolve()
    expected = json.loads((package / "expected.json").read_text())

    verify_pin(FIRMWARE, PINS["firmware.bin"])
    verify_pin(FIRMWARE_ELF, PINS["firmware.elf"])
    verify_pin(BACKEND, PINS["flexe-vdp.so"])
    verify_pin(package / "wolf3d.vdpl", PINS["wolf3d.vdpl"])
    for relative, receipt in expected["package_files"].items():
        verify_pin(package / relative, receipt["sha256"])

    ensure_stopped(PROFILE)
    canonical = load_canonical()
    sdcard = canonical.link_shared_runtime(PROFILE, FAB_RUNTIME)
    canonical.replace_symlink(PROFILE / "fab-agon-emulator.bin", FLEXE_FRONTEND)
    shutil.copyfile(BACKEND, PROFILE / "flexe-vdp.so")
    shutil.copyfile(FIRMWARE, PROFILE / "esp32-firmware.bin")
    shutil.copyfile(FIRMWARE_ELF, PROFILE / "esp32-firmware.elf")
    (PROFILE / ".bespoke-vdp-profile").write_text("flexe-vdp.so\n")

    app = sdcard / "wolfclient"
    canonical.replace_tree(package, app)
    (app / "client.dat").unlink(missing_ok=True)
    (sdcard / "autoexec.txt").write_bytes(
        b"SET KEYBOARD 1\r\n"
        b"cd /wolfclient\r\n"
        b"load client.bin\r\n"
        b"run .\r\n"
    )

    canonical.write_profile_launcher(PROFILE, strict_bespoke=True)
    launcher = PROFILE / "fab-agon-emulator"
    script = launcher.read_text()
    environment = """
rm -f -- "$profile_dir/sdcard/wolfclient/client.dat"
export AGON_FLEXE_FIRMWARE="$profile_dir/esp32-firmware.bin"
export AGON_FLEXE_ELF="$profile_dir/esp32-firmware.elf"
export AGON_FLEXE_ENGINE="${AGON_FLEXE_ENGINE:-jit}"
export AGON_FLEXE_ARTIFACTS="$profile_dir/last-run"
mkdir -p "$AGON_FLEXE_ARTIFACTS"
"""
    if script.count("\nvdp_name=") != 1:
        raise SystemExit("Canonical launcher does not expose one VDP selection point")
    launcher.write_text(script.replace("\nvdp_name=", environment + "\nvdp_name=", 1))
    launcher.chmod(0o755)

    inputs = [
        "fab-agon-emulator.bin", "flexe-vdp.so", "esp32-firmware.bin",
        "esp32-firmware.elf", "mos_platform.bin", "mos_platform.map",
        "sdcard/autoexec.txt",
    ]
    inputs.extend(
        str(path.relative_to(PROFILE))
        for path in sorted(app.rglob("*")) if path.is_file()
    )
    (PROFILE / ".runtime.sha256").write_text("".join(
        f"{sha(PROFILE / name)}  {name}\n" for name in inputs
    ))
    canonical.name_flexe_profile(PROFILE)
    subprocess.run(
        ["sha256sum", "--check", "--status", ".runtime.sha256"],
        cwd=PROFILE, check=True,
    )
    ensure_stopped(PROFILE)
    # name_flexe_profile normalizes the human-facing launcher after the
    # canonical builder initially creates fab-agon-emulator. Report the path
    # that actually exists in the finished profile.
    launcher = PROFILE / "flexe-agon-emulator"
    if not launcher.is_file() or not os.access(launcher, os.X_OK):
        raise SystemExit(f"missing normalized profile launcher: {launcher}")

    receipt = {
        "scope": "stopped copied-pixel production-client Oryx profile",
        "profile": str(PROFILE),
        "launcher": str(launcher),
        "stopped": True,
        "autoexec": (sdcard / "autoexec.txt").read_text(),
        "runtime_identities": (PROFILE / ".runtime.sha256").read_text().splitlines(),
        "client_sha256": sha(app / "client.bin"),
        "module_sha256": sha(app / "wolf3d.vdpl"),
        "reference_sha256": sha(app / "reference.ppm"),
        "firmware_sha256": sha(PROFILE / "esp32-firmware.bin"),
        "firmware_elf_sha256": sha(PROFILE / "esp32-firmware.elf"),
        "backend_sha256": sha(PROFILE / "flexe-vdp.so"),
        "frontend_sha256": sha(PROFILE / "flexe-agon-emulator.bin"),
        "source_visible": (app / "source/wolf3d_vdplet_client.inc").is_file(),
        "GUI_launched": False,
        "target_execution": arguments.target_status,
    }
    (PROFILE / "client-profile.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
