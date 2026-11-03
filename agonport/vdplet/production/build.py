#!/usr/bin/env python3
"""Qualify the production mirror, renderer, wrapper, and Xtensa package."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import subprocess


HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[2]
BUILD = HERE / "build"
TEST = BUILD / "test_world_mirror"
RENDERER_TEST = BUILD / "test_renderer"
RENDERER_ORACLE = BUILD / "renderer_oracle"
MODULE_TEST = BUILD / "test_module"
ORACLE_ROOT = Path("/Agon/mystuff/agon-vdp-wolf3d")
SDK = Path("/Agon/mystuff/agon-vdplet/build/vdpl-014/baseline")
SDK_PYTHON = Path("/Agon/mystuff/agon-vdplet/.venv/bin/python")
TOOLCHAIN = Path("/home/smith/.platformio/packages/toolchain-xtensa-esp32/bin")
EXPECTED_PACKAGE_SHA256 = (
    "fdd78204aabf94900415c0741fb98da7ee4035781fb3e957784522d2277ec1bc"
)
FRAME_BYTES = 76800
HUD_MANIFEST = (
    PROJECT / "agonport/assets/generated/wolf3d/hud/hud_assets.jsonl"
)


def run(command: list[str]) -> None:
    subprocess.run(command, cwd=HERE, check=True)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_hud_manifest() -> int:
    entries = {
        entry["chunkId"]: entry
        for line in HUD_MANIFEST.read_text().splitlines()
        if line.strip()
        for entry in [json.loads(line)]
    }
    expected = {98: (320, 40)}
    expected.update({chunk: (48, 24) for chunk in range(103, 107)})
    expected.update({chunk: (8, 16) for chunk in range(107, 121)})
    expected.update({chunk: (24, 32) for chunk in range(121, 144)})
    for chunk, dimensions in expected.items():
        entry = entries.get(chunk)
        if entry is None or (entry["width"], entry["height"]) != dimensions:
            raise AssertionError(f"HUD chunk {chunk} dimension contract drifted")
        payload = HUD_MANIFEST.parent / entry["rgba2"]
        if payload.stat().st_size != dimensions[0] * dimensions[1]:
            raise AssertionError(f"HUD chunk {chunk} payload size drifted")
    return len(expected)


def parse_stack(path: Path) -> dict[str, int]:
    result = {}
    for line in path.read_text().splitlines():
        fields = line.rsplit("\t", 2)
        if len(fields) == 3:
            result[fields[0].split(":", 3)[-1]] = int(fields[1])
    return result


def main() -> None:
    run(["python3", "contract.py", "--check"])
    hud_assets_verified = verify_hud_manifest()
    BUILD.mkdir(parents=True, exist_ok=True)
    run([
        "g++", "-std=c++17", "-O2", "-Wall", "-Wextra", "-Werror",
        "-pedantic", "wolf3d_world_mirror.cpp", "test_world_mirror.cpp",
        "-o", str(TEST),
    ])
    run([str(TEST)])
    warnings = ["-Wall", "-Wextra", "-Werror", "-pedantic"]
    run([
        "g++", "-std=c++17", "-O2", *warnings,
        "wolf3d_world_mirror.cpp", "wolf3d_renderer.cpp",
        "test_renderer.cpp", "-o", str(RENDERER_TEST),
    ])
    run([
        "g++", "-std=c++17", "-O2", *warnings,
        "-I" + str(ORACLE_ROOT), "renderer_oracle.cpp",
        "-o", str(RENDERER_ORACLE),
    ])
    renderer_frame = BUILD / "renderer-frame.bin"
    renderer_geometry = BUILD / "renderer-geometry.bin"
    oracle_frame = BUILD / "oracle-frame.bin"
    oracle_geometry = BUILD / "oracle-geometry.bin"
    run([str(RENDERER_TEST), str(renderer_frame), str(renderer_geometry)])
    run([str(RENDERER_ORACLE), str(oracle_frame), str(oracle_geometry)])
    if renderer_frame.read_bytes() != oracle_frame.read_bytes():
        raise AssertionError("production renderer pixels differ from standalone oracle")
    if renderer_geometry.read_bytes() != oracle_geometry.read_bytes():
        raise AssertionError("production renderer DDA differs from standalone oracle")

    run([
        "g++", "-std=c++17", "-O2", *warnings, "-DWOLF3D_HOST_TEST",
        "-I" + str(SDK / "include"),
        "-I" + str(PROJECT / "agonport/vdplet/qualification"),
        "wolf3d_module.cpp", "test_module.cpp", "-o", str(MODULE_TEST),
    ])
    published_frame = BUILD / "module-frame.bin"
    target_fixture = BUILD / "target-fixture"
    if target_fixture.exists():
        shutil.rmtree(target_fixture)
    run([str(MODULE_TEST), str(published_frame), str(target_fixture)])
    if published_frame.read_bytes() != renderer_frame.read_bytes()[:FRAME_BYTES]:
        raise AssertionError("module publication differs from pure renderer/oracle")

    module_dir = BUILD / "module"
    module_dir.mkdir(exist_ok=True)
    run([
        SDK_PYTHON, SDK / "tools/build_module.py", "wolf3d_module.cpp",
        "--output", module_dir, "--name", "wolf3d_production",
        "--capabilities", "257", "--abi-minor", "6",
        "--text-limit", "65536", "--data-limit", "16384",
        "--stack-limit", "2048", "--image-limit", "131072",
        "--build-id", "0x20261031",
    ])
    manifest = json.loads(
        (module_dir / "wolf3d_production.json").read_text())
    package = manifest["module"]
    if package["sha256"] != EXPECTED_PACKAGE_SHA256:
        raise AssertionError("production package changed without pin update")
    if (package["capabilities"], package["abi_minor"]) != (257, 6):
        raise AssertionError("production package ABI/capability drifted")
    undefined = subprocess.check_output([
        str(TOOLCHAIN / "xtensa-esp32-elf-nm"), "-u",
        str(module_dir / "wolf3d_production.o"),
    ], text=True).strip().splitlines()
    if undefined:
        raise AssertionError(f"production package has undefined symbols: {undefined}")
    relocations = [
        line.strip() for line in
        (module_dir / "wolf3d_production.readelf.txt").read_text().splitlines()
        if "R_XTENSA_" in line
    ]
    if not relocations or any(
            "R_XTENSA_RELATIVE" not in line for line in relocations):
        raise AssertionError(f"unexpected production relocations: {relocations}")
    stack = parse_stack(module_dir / "wolf3d_production.su")
    def stack_for(fragment: str) -> int:
        matches = [value for name, value in stack.items() if fragment in name]
        if len(matches) != 1:
            raise AssertionError(
                f"expected one stack entry containing {fragment!r}, got {matches}")
        return matches[0]

    call_chains = {
        "entry -> apply_update_batch -> validate_batch": (
            stack_for("vdplet_entry") +
            stack_for("apply_update_batch") +
            stack_for("validate_batch")
        ),
        "entry -> direct renderer -> compositor -> asset acquire": (
            stack_for("vdplet_entry") +
            stack_for("render_world_direct") +
            stack_for("render_world_to_target") +
            stack_for("acquire_asset")
        ),
        "entry -> descriptor match -> descriptor copy": (
            stack_for("vdplet_entry") +
            stack_for("require_matching_descriptor") +
            stack_for("copy_descriptor")
        ),
    }
    if max(call_chains.values()) > 2048:
        raise AssertionError(f"production source call chain exceeds limit: {call_chains}")
    shutil.copyfile(module_dir / "wolf3d_production.vdpl",
                    BUILD / "wolf3d_production.vdpl")
    fixture_files = sorted(
        path for path in target_fixture.iterdir() if path.is_file())
    receipt = {
        "schema": 2,
        "argument_bytes": 24,
        "batch_max_bytes": 7168,
        "batch_max_records": 618,
        "maximum_full_snapshot_bytes": 6982,
        "atomic_validation": True,
        "renderer_scenarios": 6,
        "renderer_frame_bytes_compared": len(renderer_frame.read_bytes()),
        "renderer_geometry_bytes_compared": len(renderer_geometry.read_bytes()),
        "renderer_frame_sha256": sha(renderer_frame),
        "renderer_geometry_sha256": sha(renderer_geometry),
        "hud_assets_verified": hud_assets_verified,
        "renderer_scope": (
            "background, DDA, walls, moving/completed pushwalls, doors, "
            "actors, statics, view weapon, HUD"
        ),
        "module_frame_sha256": sha(published_frame),
        "module_lifecycle": (
            "CONFIG/APPLY/RESET/FINI plus publication and asset retry"
        ),
        "target_fixture_files": len(fixture_files),
        "target_fixture_bytes": sum(path.stat().st_size for path in fixture_files),
        "target_fixture_sha256": {
            path.name: sha(path) for path in fixture_files
        },
        "package": package,
        "package_component_sha256": {
            "world_mirror": sha(HERE / "wolf3d_world_mirror.cpp"),
            "renderer": sha(HERE / "wolf3d_renderer.cpp"),
            "contract": sha(HERE / "wolf3d_production_contract.h"),
            "tables": sha(HERE.parent / "wolf3d_tables.inc"),
        },
        "undefined_symbols": undefined,
        "relative_relocations": len(relocations),
        "source_stack_frames": stack,
        "largest_source_stack_frame": max(stack.values()),
        "source_call_chain_sums": call_chains,
        "largest_source_call_chain_sum": max(call_chains.values()),
        "stack_limit_note": (
            "Conservative sums of visible module-owned source frames; runtime "
            "and compiler-generated overhead remain target-qualification evidence."
        ),
        "passed": True,
    }
    (BUILD / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
