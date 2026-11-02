#!/usr/bin/env python3
"""Verify the Pi-only corrected late-window selection without target access."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
VDPLET = HERE.parent
ROOT = VDPLET.parent.parent
CENTRAL = ROOT.parent / "agon-dev-env/cross-agent/vdplet-rollout/wolf-ring-late-corrected-preparation-v1.md"
OLD = VDPLET / "audio-ring"
STARTUP = VDPLET / "audio-ring-startup"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    preparation = json.loads((HERE / "preparation.json").read_text())
    old = json.loads((OLD / "staging.json").read_text())
    startup = json.loads((STARTUP / "staging.json").read_text())
    assert sha(CENTRAL) == preparation["authority_sha256"]
    assert sha(HERE / "PLAN.md") == preparation["plan_sha256"]
    assert sha(OLD / "staging.json") == preparation["retained_receipts"]["original_late_staging_sha256"]
    assert sha(STARTUP / "staging.json") == preparation["retained_receipts"]["corrected_startup_staging_sha256"]

    selected = preparation["selected"]
    preserved = (
        "application_sha256", "module_sha256", "frontend_sha256",
        "firmware_sha256", "firmware_elf_sha256", "mos_sha256",
        "helper_source_sha256", "helper_binary_sha256", "reader_sha256",
    )
    for key in preserved:
        assert old[key] == startup[key] == selected[key], key
    assert startup["backend_sha256"] == selected["backend_sha256"]
    assert old["runner_sha256"] == selected["runner_sha256"]
    assert old["oracle_sha256"] == selected["oracle_sha256"]
    assert sha(OLD / "runner.py") == selected["runner_sha256"]
    assert sha(OLD / "oracle.json") == selected["oracle_sha256"]
    assert old["observer_window_after_ms"] == 90000
    assert startup["observer_window_after_ms"] == 0
    assert old["frontend_dependency_pins"] == startup["frontend_dependency_pins"]
    assert old["helper_dependency_pins"] == startup["helper_dependency_pins"]

    measurement = preparation["measurement"]
    assert measurement == {
        "mode": "late-corrected",
        "observer_window_after_ms": 90000,
        "observer_window_seconds": 10,
        "shot_overlap_required": True,
        "initial_empty_history_required": False,
        "preserve_censoring": True,
    }
    assert preparation["finite_invocation"]["count"] == 1
    assert preparation["finite_invocation"]["retry"] is False
    assert all(preparation["not_performed"].values())
    print(json.dumps({
        "status": "verified-pi-device-free",
        "selected_backend": selected["backend_sha256"],
        "selected_runner": selected["runner_sha256"],
        "window_after_ms": measurement["observer_window_after_ms"],
        "target_contact": False,
    }))


if __name__ == "__main__":
    main()
