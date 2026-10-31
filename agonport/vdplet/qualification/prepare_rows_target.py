#!/usr/bin/env python3
"""Prepare and pin the finite rows target cohort without loading a backend."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import py_compile


HERE = Path(__file__).resolve().parent
BUILD = HERE / "build"
PLAN = HERE.parents[1] / "doc/wolf3d-vdplet-color-rows-target-plan.md"
REVIEW = HERE.parent / "review-rows"

PINS = {
    "wolf3d_scene.vdpl": "57b635fc1807d9108e576cfff4c79c7f57ade48164fc5be97d75a3562e54b1be",
    "wolf3d_scene_rows.vdpl": "c32381bc659b6e1fcc479eef22168a77eea22da310202da794234f172ccab670",
    "oracle-frame.bin": "6b569190c057996d4c50c1cc182c5b210a05a5e8c6fc7f9e60059d892363bf93",
    "oracle-geometry.bin": "2a15866957fa06d34f72067b2b1ff42325b3c3d0f02403059d43dc9a6812d820",
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path,
                        default=BUILD / "rows-target-readiness.json")
    arguments = parser.parse_args()
    for name, expected in PINS.items():
        path = BUILD / name
        actual = sha(path)
        if actual != expected:
            raise SystemExit(f"pin mismatch {path}: {actual} != {expected}")
    scripts = (
        HERE / "target.py",
        HERE / "qualify_rows.py",
        HERE / "check_rows_preparation.py",
        REVIEW / "build.py",
        REVIEW / "prepare_profile.py",
        REVIEW / "stage_oryx.py",
    )
    for script in scripts:
        py_compile.compile(str(script), doraise=True)

    receipt = {
        "scope": "finite target preparation only; no backend loaded or emulator run",
        "task": "G057-WLF-003 / TODO 8b",
        "plan": str(PLAN),
        "plan_sha256": sha(PLAN),
        "qualifier": str(HERE / "qualify_rows.py"),
        "qualifier_sha256": sha(HERE / "qualify_rows.py"),
        "target_driver_sha256": sha(HERE / "target.py"),
        "host_preparation_check_sha256": sha(HERE / "check_rows_preparation.py"),
        "preparer_sha256": sha(Path(__file__)),
        "local_inputs": {
            name: {"path": str(BUILD / name), "sha256": expected}
            for name, expected in PINS.items()
        },
        "external_pins": {
            "firmware_sha256": "8d980025f891484cf7e6cc5f2992cf517cb80e0123ff7de712ae8d7f2dc1c807",
            "firmware_elf_sha256": "1a7c44482d4ba8c5bfb49976c0bd664b9a9c2a635c7027b30954929ca567f814",
            "x86_backend_sha256": "0866265bd6f3d73ad572f31dc1bb954f308ed9a5d857efa9414d37e1ade13374",
            "availability": "must be reverified on Oryx before a later lease request",
        },
        "engines": ["jit", "interp"],
        "timing_rounds": 6,
        "runs_per_arm_per_round": 5,
        "expected_maximum_seconds": {"jit": 180, "interp": 360},
        "proposed_profile": "/home/smith/Agon/mystuff/Wolf3dOrig/.emulator/vdplet-rows-review",
        "review_preparation": {
            "requires_passed_jit_and_interp_receipts": True,
            "review_document_sha256": sha(REVIEW / "REVIEW.md"),
            "build_script_sha256": sha(REVIEW / "build.py"),
            "profile_script_sha256": sha(REVIEW / "prepare_profile.py"),
            "stage_script_sha256": sha(REVIEW / "stage_oryx.py"),
            "profile_staged": False,
            "GUI_launched": False,
        },
        "backend_loaded": False,
        "emulator_run": False,
        "lease_requested": False,
        "ready_for_golem_execution_review": True,
    }
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
