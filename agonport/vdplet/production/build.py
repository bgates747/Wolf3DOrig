#!/usr/bin/env python3
"""Regenerate and exercise the pure production world-mirror contract."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess


HERE = Path(__file__).resolve().parent
BUILD = HERE / "build"
TEST = BUILD / "test_world_mirror"
RENDERER_TEST = BUILD / "test_renderer"
RENDERER_ORACLE = BUILD / "renderer_oracle"
ORACLE_ROOT = Path("/Agon/mystuff/agon-vdp-wolf3d")


def run(command: list[str]) -> None:
    subprocess.run(command, cwd=HERE, check=True)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    run(["python3", "contract.py", "--check"])
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
    module_frame = BUILD / "renderer-frame.bin"
    module_geometry = BUILD / "renderer-geometry.bin"
    oracle_frame = BUILD / "oracle-frame.bin"
    oracle_geometry = BUILD / "oracle-geometry.bin"
    run([str(RENDERER_TEST), str(module_frame), str(module_geometry)])
    run([str(RENDERER_ORACLE), str(oracle_frame), str(oracle_geometry)])
    if module_frame.read_bytes() != oracle_frame.read_bytes():
        raise AssertionError("production renderer pixels differ from standalone oracle")
    if module_geometry.read_bytes() != oracle_geometry.read_bytes():
        raise AssertionError("production renderer DDA differs from standalone oracle")
    receipt = {
        "schema": 1,
        "argument_bytes": 24,
        "batch_max_bytes": 6912,
        "batch_max_records": 617,
        "maximum_full_snapshot_bytes": 6891,
        "atomic_validation": True,
        "renderer_scenarios": 3,
        "renderer_frame_bytes_compared": len(module_frame.read_bytes()),
        "renderer_geometry_bytes_compared": len(module_geometry.read_bytes()),
        "renderer_frame_sha256": sha(module_frame),
        "renderer_geometry_sha256": sha(module_geometry),
        "renderer_scope": "background, DDA, walls, doors, actors, statics",
        "passed": True,
    }
    (BUILD / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
