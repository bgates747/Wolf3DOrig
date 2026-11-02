#!/usr/bin/env python3
"""Create and verify the isolated Wolf host-ring profile; never launch it."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess


HOME = Path.home()
PROJECT = HOME / "Agon/mystuff/Wolf3dOrig"
TASK = PROJECT / "agonport/vdplet/audio-ring"
BASE = PROJECT / ".emulator/wolf3d-vdplet-app-observed-r01"
PROFILE = PROJECT / ".emulator/wolf3d-vdplet-audio-ring-r02"
CANDIDATE = HOME / "Agon/mystuff/flexe-agon-emulator/build/fx124/candidate-r01/flexe-vdp-ring.so"
READER = HOME / "Agon/mystuff/flexe-agon-emulator/build/fx124/tools-r01/read_residence.py"
OUTPUT = PROFILE / "ring-output"

PINS = {
    "application": "5723cd60234e46a8c34809fa8fba5f5286058f3cf7ad9d5bfc27c9f72a4d4ae7",
    "module": "12449bab795f4fd8ecfbbb2f4c547299632bba9bda88dc7ebf4e68160aac9c63",
    "frontend": "7e7d0e1bc89af72bde7ffbd6c06446aaefda4d1803f89eb1faf3167307ee1e01",
    "firmware": "8d980025f891484cf7e6cc5f2992cf517cb80e0123ff7de712ae8d7f2dc1c807",
    "firmware_elf": "1a7c44482d4ba8c5bfb49976c0bd664b9a9c2a635c7027b30954929ca567f814",
    "mos": "d564243283972690933a4554296ad6202ca4ef54572279533a942960846bebae",
    "baseline_backend": "0866265bd6f3d73ad572f31dc1bb954f308ed9a5d857efa9414d37e1ade13374",
    "candidate_backend": "0f4bdc1b663374720d1b7ea208507238358bbd8568be28c109a3030959f117a2",
    "helper_source": "215bd2480a224827787b651db5685342e2f9cfe68a02f984d1988b661d119d10",
    "reader": "584e9d2a9e59606a1f9ce667d59e0ff0d04dc1eb59b0681b8a5d6354835d3d12",
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
            path = Path(candidate)
            pins.append({"path": candidate, "sha256": sha(path)})
    return pins


def main() -> None:
    ensure_stopped(BASE)
    subprocess.run(["sha256sum", "--check", "--status", ".runtime.sha256"],
                   cwd=BASE, check=True)
    verify(BASE / "sdcard/wolf3d/wolf3d.bin", PINS["application"])
    verify(BASE / "sdcard/wolf3d/wolf3d.vdpl", PINS["module"])
    verify(BASE / "flexe-agon-emulator.bin", PINS["frontend"])
    verify(BASE / "esp32-firmware.bin", PINS["firmware"])
    verify(BASE / "esp32-firmware.elf", PINS["firmware_elf"])
    verify(BASE / "mos_platform.bin", PINS["mos"])
    verify(BASE / "flexe-vdp.so", PINS["baseline_backend"])
    verify(CANDIDATE, PINS["candidate_backend"])
    verify(TASK.parent / "review/sdl_review.c", PINS["helper_source"])
    verify(READER, PINS["reader"])
    if PROFILE.exists():
        raise SystemExit(f"refusing existing profile: {PROFILE}")

    shutil.copytree(BASE, PROFILE, symlinks=True,
                    ignore=shutil.ignore_patterns("last-run", "profile.json"))
    (PROFILE / "last-run").mkdir()
    shutil.copyfile(CANDIDATE, PROFILE / "flexe-vdp.so")
    for source, name in (
        (TASK.parent / "review/sdl_review.c", "sdl_review.c"),
        (TASK / "PLAN.md", "PLAN.md"),
        (TASK / "runner.py", "runner.py"),
        (TASK / "oracle.json", "oracle.json"),
        (READER, "read_residence.py"),
    ):
        shutil.copyfile(source, PROFILE / name)
    (PROFILE / "runner.py").chmod(0o755)
    (PROFILE / "read_residence.py").chmod(0o755)

    compile_command = [
        "cc", "-std=c17", "-O2", "-Wall", "-Wextra", "-Werror",
        "-fPIC", "-shared", "-I/home/smith/.local/include",
        str(PROFILE / "sdl_review.c"), "-ldl", "-o",
        str(PROFILE / "review-input.so"),
    ]
    subprocess.run(compile_command, check=True)

    script = (PROFILE / "flexe-agon-emulator").read_text()
    lines = [line for line in script.splitlines()
             if not line.startswith("export FLEXE_UART_OBSERVER_OUTPUT=")]
    script = "\n".join(lines) + "\n"
    environment = (
        f'export FLEXE_RING_OBSERVER_DIR="{OUTPUT}"\n'
        'export FLEXE_RING_WINDOW_AFTER_MS="90000"\n'
    )
    if script.count("\nvdp_name=") != 1:
        raise SystemExit("launcher has no unique VDP selection point")
    (PROFILE / "flexe-agon-emulator").write_text(
        script.replace("\nvdp_name=", "\n" + environment + "vdp_name=", 1)
    )
    (PROFILE / "flexe-agon-emulator").chmod(0o755)
    OUTPUT.mkdir()

    runtime_names = []
    for line in (BASE / ".runtime.sha256").read_text().splitlines():
        _, name = line.split("  ", 1)
        runtime_names.append(name)
    runtime_names.extend([
        "flexe-agon-emulator", "PLAN.md", "sdl_review.c", "review-input.so",
        "runner.py", "oracle.json", "read_residence.py",
    ])
    (PROFILE / ".runtime.sha256").write_text("".join(
        f"{sha(PROFILE / name)}  {name}\n" for name in runtime_names
    ))
    subprocess.run(["sha256sum", "--check", "--status", ".runtime.sha256"],
                   cwd=PROFILE, check=True)
    ensure_stopped(PROFILE)

    compiler = shutil.which("cc")
    assert compiler is not None
    compiler = str(Path(compiler).resolve())
    pkg_version = subprocess.run(
        ["pkg-config", "--modversion", "sdl3"], check=True,
        text=True, stdout=subprocess.PIPE,
    ).stdout.strip()
    pkg_flags = subprocess.run(
        ["pkg-config", "--cflags", "--libs", "sdl3"], check=True,
        text=True, stdout=subprocess.PIPE,
    ).stdout.strip()
    dependencies = subprocess.run(
        ["ldd", str(PROFILE / "review-input.so")], check=True,
        text=True, stdout=subprocess.PIPE,
    ).stdout.splitlines()
    frontend_dependencies = subprocess.run(
        ["ldd", str(PROFILE / "flexe-agon-emulator.bin")], check=True,
        text=True, stdout=subprocess.PIPE,
    ).stdout.splitlines()
    receipt = {
        "schema": "wolf3d-audio-ring-stopped-profile-v1",
        "profile": str(PROFILE),
        "stopped": True,
        "emulator_launched": False,
        "audio_device_opened": False,
        "reservation_created": False,
        "application_sha256": sha(PROFILE / "sdcard/wolf3d/wolf3d.bin"),
        "module_sha256": sha(PROFILE / "sdcard/wolf3d/wolf3d.vdpl"),
        "frontend_sha256": sha(PROFILE / "flexe-agon-emulator.bin"),
        "firmware_sha256": sha(PROFILE / "esp32-firmware.bin"),
        "firmware_elf_sha256": sha(PROFILE / "esp32-firmware.elf"),
        "mos_sha256": sha(PROFILE / "mos_platform.bin"),
        "backend_sha256": sha(PROFILE / "flexe-vdp.so"),
        "helper_source_sha256": sha(PROFILE / "sdl_review.c"),
        "helper_binary_sha256": sha(PROFILE / "review-input.so"),
        "plan_sha256": sha(PROFILE / "PLAN.md"),
        "launcher_sha256": sha(PROFILE / "flexe-agon-emulator"),
        "runner_sha256": sha(PROFILE / "runner.py"),
        "oracle_sha256": sha(PROFILE / "oracle.json"),
        "reader_sha256": sha(PROFILE / "read_residence.py"),
        "observer_directory": str(OUTPUT),
        "observer_directory_empty": not any(OUTPUT.iterdir()),
        "observer_window_after_ms": 90000,
        "video_driver_for_runner": "dummy",
        "audio_driver_for_runner": "pulseaudio (explicit; dummy/disk/unpinned rejected)",
        "compiler": compiler,
        "compiler_sha256": sha(Path(compiler)),
        "sdl3_pkg_version": pkg_version,
        "sdl3_pkg_flags": pkg_flags,
        "helper_dependencies": dependencies,
        "frontend_dependencies": frontend_dependencies,
        "helper_dependency_pins": dependency_pins(dependencies),
        "frontend_dependency_pins": dependency_pins(frontend_dependencies),
        "compile_command": compile_command,
    }
    (PROFILE / "audio-ring-profile.json").write_text(
        json.dumps(receipt, indent=2) + "\n"
    )
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
