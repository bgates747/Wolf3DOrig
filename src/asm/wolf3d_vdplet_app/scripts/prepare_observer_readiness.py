#!/usr/bin/env python3
"""Freeze the Wolf3D FX-114 observer plan locally; no SSH or emulator process."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import stage_observer_oryx as stage


HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[3]
PACKAGE = HERE.parent / "tgt/package"
OUTPUT = HERE.parent / "tgt/observer-readiness.json"
BASE_STAGING = HERE.parent / "tgt/staging.json"
CENTRAL = Path.home() / "Agon/mystuff/agon-dev-env/cross-agent/vdplet-rollout"
FX114 = Path.home() / "Agon/mystuff/flexe-agon-emulator/docs/tasks/FX-114"
FAB_RUNTIME = Path.home() / "Agon/mystuff/golem/.emulator/runtime/fab-1.2.5"

PINS = {
    CENTRAL / "uart-observer-v1.md":
        "e143d4a7b983aed28f8431f4d4ab3f429087ea3ce1a268c7ccf497fd2c11d00a",
    FX114 / "readiness.json":
        "948bf79143738927ac7998f61a4d91bd4766c9aa2f9b1ccdf0af2245970fe1d2",
    FX114 / "read_record.py": stage.READER_SHA256,
    FAB_RUNTIME / "firmware/mos_platform.bin":
        "d564243283972690933a4554296ad6202ca4ef54572279533a942960846bebae",
    FAB_RUNTIME / "firmware/mos_platform.map":
        "d69e60bbce61a7b4b3eef318ba395f11c4e1a5b585755755113992dc94edcb86",
}
BASE_FRONTEND_SHA256 = (
    "f7951314959be72ab7757579a9daf2a42383ccdb5187dec9d9653b42ad8a477c"
)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(path: Path, expected: str) -> None:
    actual = sha(path)
    if actual != expected:
        raise SystemExit(f"pin mismatch for {path}: {actual} != {expected}")


def main() -> None:
    for path, expected in PINS.items():
        verify(path, expected)

    expected_path = PACKAGE / "expected.json"
    expected = json.loads(expected_path.read_text())
    for relative, item in expected["files"].items():
        verify(PACKAGE / relative, item["sha256"])

    base = json.loads(BASE_STAGING.read_text())
    required_base = {
        "stopped": True,
        "GUI_launched": False,
        "application_sha256": expected["files"]["wolf3d.bin"]["sha256"],
        "module_sha256": expected["files"]["wolf3d.vdpl"]["sha256"],
        "backend_sha256":
            "0866265bd6f3d73ad572f31dc1bb954f308ed9a5d857efa9414d37e1ade13374",
    }
    for key, value in required_base.items():
        if base.get(key) != value:
            raise SystemExit(f"base staging mismatch for {key}: {base.get(key)!r}")

    receipt = {
        "state": "offline_readiness_complete_remote_stage_pending",
        "scope": "one Wolf3DOrig production-VDPlet FX-114 observer cohort",
        "oryx_contacted": False,
        "profile_staged": False,
        "emulator_run": False,
        "queue_request_created": False,
        "baseline": {
            "profile": base["profile"],
            "frontend_sha256": BASE_FRONTEND_SHA256,
            "application_sha256": base["application_sha256"],
            "module_sha256": base["module_sha256"],
            "backend_sha256": base["backend_sha256"],
            "firmware_sha256": base["firmware_sha256"],
            "mos_sha256": PINS[FAB_RUNTIME / "firmware/mos_platform.bin"],
            "mos_map_sha256": PINS[FAB_RUNTIME / "firmware/mos_platform.map"],
            "font_identity": "embedded in and frozen by backend_sha256",
            "payload_files": base["payload_files"],
            "expected_json_sha256": sha(expected_path),
        },
        "declared_changes_only": {
            "profile": stage.REMOTE_PROFILE,
            "frontend": stage.REMOTE_FRONTEND,
            "frontend_sha256": stage.FRONTEND_SHA256,
            "frontend_bytes": 1_954_496,
            "observer_output": stage.REMOTE_RECORD,
            "environment": "FLEXE_UART_OBSERVER_OUTPUT",
        },
        "observer_contract": {
            "schema": "fx114-sender-v1",
            "stall_ms": 50_000,
            "poll_ms": 100,
            "sample_offsets_ms": [0, 250, 500],
            "max_lifetime_ms": 630_000,
            "max_lines": 5,
            "reader": stage.REMOTE_READER,
            "reader_sha256": stage.READER_SHA256,
            "central_contract_sha256": PINS[CENTRAL / "uart-observer-v1.md"],
        },
        "frozen_failure_boundary": {
            "buffer_id": "0x1001",
            "asset": "wall_001",
            "declared_payload_bytes": 4096,
            "captured_payload_bytes": 333,
            "next_unsent_byte": "0xea",
        },
        "future_commands": {
            "stage_stopped_profile":
                ".venv/bin/python "
                "src/asm/wolf3d_vdplet_app/scripts/stage_observer_oryx.py",
            "launch_after_fifo_checkout":
                f"cd {stage.REMOTE_PROFILE} && ./flexe-agon-emulator",
            "read_record_after_close":
                f"{stage.REMOTE_ROOT}/.venv/bin/python "
                f"{stage.REMOTE_READER} {stage.REMOTE_RECORD}",
        },
        "human_input": (
            "GUI startup and any reproduction input remain manual; no deterministic "
            "input driver has been admitted for this cohort"
        ),
        "expected_outcomes": [
            "reproduced stall with a finalized three-sample observer window",
            "functional progress or changed timing with a finalized observer record",
            "missing, interrupted, or late record reported as incomplete",
        ],
        "manual_review_plan": {
            "whole_session_ceiling_seconds": 180,
            "startup_input": "none; do not press keys during asset loading",
            "stalled_boundary": (
                "leave the process open for at least 55 seconds after the last "
                "visible loading progress so the fixed observer window can finish"
            ),
            "progress_boundary": (
                "if loading completes, observe the stable scene briefly without "
                "gameplay input and then close normally"
            ),
            "normal_close_owner": "Author closes the GUI",
            "custodian": (
                "wolf3dorig retains the FIFO lease, retrieves and reads evidence, "
                "proves the host idle, releases, and notifies the next owner"
            ),
            "deadline_policy": (
                "at 180 seconds request Author closure and report the overrun; "
                "elapsed time alone never authorizes forced teardown"
            ),
        },
        "cleanup": [
            "close the owned GUI normally when practical",
            "preserve raw UART, delivered bytes, console, framebuffer, stats and JSONL",
            "run the pinned offline reader without extending the target timeout",
            "prove the whole host idle, release the lease, and notify the next owner",
        ],
        "prohibitions": [
            "no timeout, chunk-size, pacing, firmware, backend, payload or consumer change",
            "no automatic retry",
            "no repair claim from observer behavior",
            "no process until a separate FIFO checkout and Author-selected manual review",
        ],
    }
    OUTPUT.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
