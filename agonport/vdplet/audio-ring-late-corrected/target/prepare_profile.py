#!/usr/bin/env python3
"""Stage the selected corrected late profile from accepted artifacts; no build/run."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import platform
import shutil
import subprocess


HOME = Path.home()
PROJECT = HOME / "Agon/mystuff/Wolf3dOrig"
TASK = PROJECT / "agonport/vdplet/audio-ring-late-corrected"
TARGET_TASK = TASK / "target"
OLD = PROJECT / ".emulator/wolf3d-vdplet-audio-ring-r02"
CORRECTED = PROJECT / ".emulator/wolf3d-vdplet-audio-ring-startup-r01"
PROFILE = PROJECT / ".emulator/wolf3d-vdplet-audio-ring-late-corrected-r01"
OUTPUT = PROFILE / "ring-output-late-corrected"
OLD_RECEIPT = TARGET_TASK / "accepted-old-staging.json"
CORRECTED_RECEIPT = TARGET_TASK / "accepted-corrected-staging.json"
CENTRAL_RUN = TARGET_TASK / "accepted-central-run.md"

PINS = {
    "preparation": "2d5c93e5851f4ab34e93fe927126bea2c65f96b2053919650e7714d6c35182f9",
    "central_run": "da3cb10cbde6176967b65dcce29c37eabefe0274db11787c2c7f2d605dbe26c6",
    "old_receipt": "6f463041d7517e2e7062f2ff9bbec66f9df5f7eadf150012066cf129301b6750",
    "corrected_receipt": "8abadc27c357f06975ab78a72a85c99808acaf1fe7a6e49baba649f6342b3202",
    "backend": "943f432fecb96689f3a0d2ae80c72d08e20903dfe2a58a00ba88d8c7727ad400",
    "runner": "f0ffe79892f9a93edc41f590bb02551583580e899b7232545253b1141962ca98",
    "oracle": "ea4f7e644d3fb8ba21ab2545007e12f501113f22c980205d8fe4963d060f0b8d",
    "kernel": "7.1.5-76070105-generic",
    "boot_id": "9ba12fbc-c204-4332-9ff9-8bda03dfe2b2",
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(path: Path, expected: str) -> None:
    actual = sha(path)
    if actual != expected:
        raise SystemExit(f"pin mismatch for {path}: {actual} != {expected}")


def ensure_stopped(profile: Path) -> None:
    marker = str(profile / "sdcard").encode()
    for process in Path("/proc").glob("[0-9]*"):
        try:
            if marker in (process / "cmdline").read_bytes().split(b"\0"):
                raise SystemExit(f"profile is running as PID {process.name}: {profile}")
        except OSError:
            continue


def runtime_map(profile: Path) -> dict[str, str]:
    result = {}
    for line in (profile / ".runtime.sha256").read_text().splitlines():
        digest, name = line.split("  ", 1)
        result[name] = digest
    return result


def dependency_pins(lines: list[str]) -> list[dict]:
    pins = []
    for line in lines:
        fields = line.strip().split()
        candidate = None
        if len(fields) >= 3 and fields[1] == "=>" and fields[2].startswith("/"):
            candidate = fields[2]
        elif fields and fields[0].startswith("/"):
            candidate = fields[0]
        if candidate:
            pins.append({"path": candidate, "sha256": sha(Path(candidate))})
    return pins


def rewrite_launcher(text: str, old_output: str, new_output: str) -> str:
    old_line = f'export FLEXE_RING_OBSERVER_DIR="{old_output}"'
    new_line = f'export FLEXE_RING_OBSERVER_DIR="{new_output}"'
    if text.count(old_line) != 1:
        raise ValueError("launcher has no unique old observer output")
    if text.count('export FLEXE_RING_WINDOW_AFTER_MS="90000"') != 1:
        raise ValueError("launcher late-window offset drift")
    return text.replace(old_line, new_line, 1)


def main() -> None:
    verify(TASK / "preparation.json", PINS["preparation"])
    verify(CENTRAL_RUN, PINS["central_run"])
    verify(OLD_RECEIPT, PINS["old_receipt"])
    verify(CORRECTED_RECEIPT, PINS["corrected_receipt"])
    old_receipt = json.loads(OLD_RECEIPT.read_text())
    corrected_receipt = json.loads(CORRECTED_RECEIPT.read_text())

    if platform.release() != PINS["kernel"]:
        raise SystemExit(f"kernel drift: {platform.release()}")
    boot_id = Path("/proc/sys/kernel/random/boot_id").read_text().strip()
    if boot_id != PINS["boot_id"]:
        raise SystemExit(f"boot drift: {boot_id}")
    for source in (OLD, CORRECTED):
        ensure_stopped(source)
        subprocess.run(["sha256sum", "--check", "--status", ".runtime.sha256"],
                       cwd=source, check=True)
    verify(OLD / "runner.py", PINS["runner"])
    verify(OLD / "oracle.json", PINS["oracle"])
    verify(CORRECTED / "flexe-vdp.so", PINS["backend"])
    if PROFILE.exists():
        raise SystemExit(f"refusing existing profile: {PROFILE}")

    preserved = (
        "application_sha256", "module_sha256", "frontend_sha256",
        "firmware_sha256", "firmware_elf_sha256", "mos_sha256",
        "helper_source_sha256", "helper_binary_sha256", "reader_sha256",
    )
    for key in preserved:
        if old_receipt[key] != corrected_receipt[key]:
            raise SystemExit(f"accepted receipt drift: {key}")
    if old_receipt["frontend_dependency_pins"] != corrected_receipt["frontend_dependency_pins"]:
        raise SystemExit("accepted frontend dependency drift")
    if old_receipt["helper_dependency_pins"] != corrected_receipt["helper_dependency_pins"]:
        raise SystemExit("accepted helper dependency drift")

    ignored = shutil.ignore_patterns(
        "last-run", "ring-output", "audio-ring-run", "audio-ring-profile.json",
    )
    shutil.copytree(OLD, PROFILE, symlinks=True, ignore=ignored)
    (PROFILE / "last-run").mkdir()
    shutil.copyfile(CORRECTED / "flexe-vdp.so", PROFILE / "flexe-vdp.so")
    old_output = old_receipt["observer_directory"]
    launcher = rewrite_launcher(
        (PROFILE / "flexe-agon-emulator").read_text(), old_output, str(OUTPUT),
    )
    (PROFILE / "flexe-agon-emulator").write_text(launcher)
    (PROFILE / "flexe-agon-emulator").chmod(0o755)
    OUTPUT.mkdir()

    old_runtime = runtime_map(OLD)
    (PROFILE / ".runtime.sha256").write_text("".join(
        f"{sha(PROFILE / name)}  {name}\n" for name in old_runtime
    ))
    subprocess.run(["sha256sum", "--check", "--status", ".runtime.sha256"],
                   cwd=PROFILE, check=True)
    ensure_stopped(PROFILE)
    target_runtime = runtime_map(PROFILE)
    changed = sorted(
        name for name in old_runtime if old_runtime[name] != target_runtime[name]
    )
    if changed != ["flexe-agon-emulator", "flexe-vdp.so"]:
        raise SystemExit(f"unexpected runtime differences: {changed}")

    helper_dependencies = subprocess.run(
        ["ldd", str(PROFILE / "review-input.so")], check=True,
        text=True, stdout=subprocess.PIPE,
    ).stdout.splitlines()
    frontend_dependencies = subprocess.run(
        ["ldd", str(PROFILE / "flexe-agon-emulator.bin")], check=True,
        text=True, stdout=subprocess.PIPE,
    ).stdout.splitlines()
    helper_pins = dependency_pins(helper_dependencies)
    frontend_pins = dependency_pins(frontend_dependencies)
    if helper_pins != old_receipt["helper_dependency_pins"]:
        raise SystemExit("actual helper dependency drift")
    if frontend_pins != old_receipt["frontend_dependency_pins"]:
        raise SystemExit("actual frontend dependency drift")

    receipt = {
        "schema": "wolf3d-corrected-late-ring-staged-profile-v1",
        "profile": str(PROFILE),
        "stopped": True,
        "emulator_launched": False,
        "audio_device_opened": False,
        "build_performed": False,
        "measurement_mode": "late-corrected",
        "application_sha256": sha(PROFILE / "sdcard/wolf3d/wolf3d.bin"),
        "module_sha256": sha(PROFILE / "sdcard/wolf3d/wolf3d.vdpl"),
        "frontend_sha256": sha(PROFILE / "flexe-agon-emulator.bin"),
        "firmware_sha256": sha(PROFILE / "esp32-firmware.bin"),
        "firmware_elf_sha256": sha(PROFILE / "esp32-firmware.elf"),
        "mos_sha256": sha(PROFILE / "mos_platform.bin"),
        "backend_sha256": sha(PROFILE / "flexe-vdp.so"),
        "helper_source_sha256": sha(PROFILE / "sdl_review.c"),
        "helper_binary_sha256": sha(PROFILE / "review-input.so"),
        "runner_sha256": sha(PROFILE / "runner.py"),
        "oracle_sha256": sha(PROFILE / "oracle.json"),
        "reader_sha256": sha(PROFILE / "read_residence.py"),
        "launcher_sha256": sha(PROFILE / "flexe-agon-emulator"),
        "runtime_manifest_sha256": sha(PROFILE / ".runtime.sha256"),
        "runtime_members": len(target_runtime),
        "unchanged_runtime_members": len(target_runtime) - len(changed),
        "runtime_differences_from_old_r02": changed,
        "observer_directory": str(OUTPUT),
        "observer_directory_empty": not any(OUTPUT.iterdir()),
        "observer_window_after_ms": 90000,
        "shot_overlap_required": True,
        "initial_empty_history_required": False,
        "helper_dependency_pins": helper_pins,
        "frontend_dependency_pins": frontend_pins,
        "kernel": platform.release(),
        "boot_id": boot_id,
        "preparation_sha256": sha(TASK / "preparation.json"),
        "central_run_sha256": sha(CENTRAL_RUN),
        "source_profiles": {"old_late": str(OLD), "corrected": str(CORRECTED)},
    }
    (PROFILE / "late-corrected-profile.json").write_text(
        json.dumps(receipt, indent=2) + "\n"
    )
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
