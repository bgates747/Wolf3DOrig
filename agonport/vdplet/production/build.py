#!/usr/bin/env python3
"""Regenerate and exercise the pure production world-mirror contract."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess


HERE = Path(__file__).resolve().parent
BUILD = HERE / "build"
TEST = BUILD / "test_world_mirror"


def run(command: list[str]) -> None:
    subprocess.run(command, cwd=HERE, check=True)


def main() -> None:
    run(["python3", "contract.py", "--check"])
    BUILD.mkdir(parents=True, exist_ok=True)
    run([
        "g++", "-std=c++17", "-O2", "-Wall", "-Wextra", "-Werror",
        "-pedantic", "wolf3d_world_mirror.cpp", "test_world_mirror.cpp",
        "-o", str(TEST),
    ])
    run([str(TEST)])
    receipt = {
        "schema": 1,
        "argument_bytes": 24,
        "batch_max_bytes": 6912,
        "batch_max_records": 617,
        "maximum_full_snapshot_bytes": 6891,
        "atomic_validation": True,
        "passed": True,
    }
    (BUILD / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
