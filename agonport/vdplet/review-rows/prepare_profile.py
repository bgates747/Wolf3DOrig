#!/usr/bin/env python3
"""Prepare the separate stopped Oryx direct-row review; never launch it."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess


HOME = Path.home()
PROJECT = HOME / "Agon/mystuff/Wolf3dOrig"
PROFILE = PROJECT / ".emulator/vdplet-rows-review"
DEFAULT_PACKAGE = PROJECT / "agonport/vdplet/review-rows/build/package"
CANONICAL = HOME / "Agon/mystuff/agon-dev-env/scripts/setup_emulator.py"
FAB_RUNTIME = HOME / "Agon/mystuff/golem/.emulator/runtime/fab-1.2.5"
FLEXE_FRONTEND = (
    HOME / "Agon/mystuff/golem/docs/tasks/GOLEM-037/binding/build/runtime/"
    "flexe-agon-emulator"
)
FIRMWARE = HOME / "Agon/mystuff/agon-vdplet/build/vdpl-012/rows-r1/firmware.bin"
FIRMWARE_ELF = FIRMWARE.with_suffix(".elf")
BACKEND = (
    HOME / "Agon/mystuff/flexe-agon-emulator/build/fx072/maintained-r02/"
    "flexe-vdp-maintained.so"
)

PINS = {
    "firmware.bin": "8d980025f891484cf7e6cc5f2992cf517cb80e0123ff7de712ae8d7f2dc1c807",
    "firmware.elf": "1a7c44482d4ba8c5bfb49976c0bd664b9a9c2a635c7027b30954929ca567f814",
    "flexe-vdp-maintained.so": "0866265bd6f3d73ad572f31dc1bb954f308ed9a5d857efa9414d37e1ade13374",
    "wolf3d_scene_rows.vdpl": "c32381bc659b6e1fcc479eef22168a77eea22da310202da794234f172ccab670",
    "wolf3d_scene.vdpl": "57b635fc1807d9108e576cfff4c79c7f57ade48164fc5be97d75a3562e54b1be",
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(path: Path, expected: str) -> None:
    actual = sha(path)
    if actual != expected:
        raise SystemExit(f"pin mismatch {path}: {actual} != {expected}")


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
                raise SystemExit(f"review profile is running as PID {process.name}")
        except OSError:
            continue


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=Path, default=DEFAULT_PACKAGE)
    arguments = parser.parse_args()
    package = arguments.package.resolve()
    expected = json.loads((package / "expected.json").read_text())
    verify(FIRMWARE, PINS["firmware.bin"])
    verify(FIRMWARE_ELF, PINS["firmware.elf"])
    verify(BACKEND, PINS["flexe-vdp-maintained.so"])
    for name in ("wolf3d_scene_rows.vdpl", "wolf3d_scene.vdpl"):
        verify(package / name, PINS[name])
    for relative, receipt in expected["files"].items():
        verify(package / relative, receipt["sha256"])

    ensure_stopped(PROFILE)
    canonical = load_canonical()
    sdcard = canonical.link_shared_runtime(PROFILE, FAB_RUNTIME)
    canonical.replace_symlink(PROFILE / "fab-agon-emulator.bin", FLEXE_FRONTEND)
    shutil.copyfile(BACKEND, PROFILE / "flexe-vdp.so")
    shutil.copyfile(FIRMWARE, PROFILE / "esp32-firmware.bin")
    shutil.copyfile(FIRMWARE_ELF, PROFILE / "esp32-firmware.elf")
    (PROFILE / ".bespoke-vdp-profile").write_text("flexe-vdp.so\n")

    app = sdcard / "wolfrows"
    canonical.replace_tree(package, app)
    for name in ("results.dat", "failure.dat"):
        (app / name).unlink(missing_ok=True)
    (sdcard / "autoexec.txt").write_bytes(
        b"SET KEYBOARD 1\r\n"
        b"cd /wolfrows\r\n"
        b"load review.bin\r\n"
        b"run .\r\n"
    )
    canonical.write_profile_launcher(PROFILE, strict_bespoke=True)
    launcher = PROFILE / "fab-agon-emulator"
    script = launcher.read_text()
    environment = """
rm -f -- "$profile_dir/sdcard/wolfrows/results.dat" "$profile_dir/sdcard/wolfrows/failure.dat"
export AGON_FLEXE_FIRMWARE="$profile_dir/esp32-firmware.bin"
export AGON_FLEXE_ELF="$profile_dir/esp32-firmware.elf"
export AGON_FLEXE_ENGINE="${AGON_FLEXE_ENGINE:-jit}"
export AGON_FLEXE_ARTIFACTS="$profile_dir/last-run"
mkdir -p "$AGON_FLEXE_ARTIFACTS"
"""
    if script.count("\nvdp_name=") != 1:
        raise SystemExit("canonical launcher lacks one VDP selection point")
    launcher.write_text(script.replace("\nvdp_name=", environment + "\nvdp_name=", 1))
    launcher.chmod(0o755)

    canonical.name_flexe_profile(PROFILE)
    identities = [
        "flexe-agon-emulator.bin", "flexe-vdp.so", "esp32-firmware.bin",
        "esp32-firmware.elf", "mos_platform.bin", "mos_platform.map",
        "sdcard/autoexec.txt",
    ]
    identities.extend(
        str(path.relative_to(PROFILE))
        for path in sorted(app.rglob("*")) if path.is_file()
    )
    (PROFILE / ".runtime.sha256").write_text("".join(
        f"{sha(PROFILE / name)}  {name}\n" for name in identities
    ))
    subprocess.run(
        ["sha256sum", "--check", "--status", ".runtime.sha256"],
        cwd=PROFILE, check=True,
    )
    ensure_stopped(PROFILE)
    receipt = {
        "scope": "new stopped direct-row full-MOS review profile",
        "profile": str(PROFILE),
        "launcher": str(PROFILE / "flexe-agon-emulator"),
        "stopped": True,
        "reviewed_module_sha256": sha(app / "wolf3d_scene_rows.vdpl"),
        "copied_control_sha256": sha(app / "wolf3d_scene.vdpl"),
        "roles_documented": (app / "REVIEW.txt").is_file(),
        "direct_source_visible": (app / "source/wolf3d_scene_rows.cpp").is_file(),
        "copied_source_visible": (app / "source/wolf3d_scene.cpp").is_file(),
        "reference_visible": (app / "reference.png").is_file(),
        "firmware_sha256": sha(PROFILE / "esp32-firmware.bin"),
        "firmware_elf_sha256": sha(PROFILE / "esp32-firmware.elf"),
        "backend_sha256": sha(PROFILE / "flexe-vdp.so"),
        "frontend_sha256": sha(PROFILE / "flexe-agon-emulator.bin"),
        "GUI_launched": False,
        "human_review": "pending separate central Author grant",
    }
    (PROFILE / "review-profile.json").write_text(
        json.dumps(receipt, indent=2) + "\n"
    )
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
