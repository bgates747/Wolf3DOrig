#!/usr/bin/env python3
"""Headlessly rehearse the exact direct-row full-MOS review under a lease."""

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import signal
import struct
import subprocess
import time


HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[2]
PROFILE = PROJECT / ".emulator/vdplet-rows-review"
APP = PROFILE / "sdcard/wolfrows"
RUN = PROFILE / "rehearsal-run"


def load_base():
    spec = importlib.util.spec_from_file_location(
        "wolf_copied_review_rehearsal", HERE.parent / "review/rehearse.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


BASE = load_base()


def verify_results(data: bytes) -> list[dict]:
    if len(data) != 50:
        raise AssertionError(f"expected 50 reply bytes, got {len(data)}")
    replies = []
    for offset in range(0, len(data), 10):
        record = data[offset:offset + 10]
        if record[:5] != b"VDPL\x01":
            raise AssertionError(record.hex())
        kind, token, value = struct.unpack_from("<BHH", record, 5)
        replies.append({"kind": kind, "token": token, "value": value})
    if [row["kind"] for row in replies] != [4, 2, 3, 3, 3]:
        raise AssertionError(replies)
    if [row["token"] for row in replies] != [1, 2, 3, 4, 5]:
        raise AssertionError(replies)
    if replies[0]["value"] != 287 or not replies[1]["value"]:
        raise AssertionError(replies)
    if any(row["value"] for row in replies[2:]):
        raise AssertionError(replies)
    return replies


def main() -> None:
    subprocess.run(
        ["sha256sum", "--check", "--status", ".runtime.sha256"],
        cwd=PROFILE, check=True,
    )
    RUN.mkdir(exist_ok=True)
    for path in list(RUN.iterdir()):
        if path.is_file():
            path.unlink()
    for name in ("results.dat", "failure.dat"):
        (APP / name).unlink(missing_ok=True)
    artifacts = PROFILE / "last-run"
    artifacts.mkdir(exist_ok=True)
    for name in ("esp32-uart0.log", "stats.json", "final.ppm"):
        (artifacts / name).unlink(missing_ok=True)

    events = RUN / "events.txt"
    events.write_text("")
    frontend_log = (RUN / "frontend.log").open("w")
    environment = dict(os.environ)
    environment.pop("BASH_ENV", None)
    environment.update(
        SDL_VIDEODRIVER="dummy",
        SDL_AUDIODRIVER="dummy",
        LD_PRELOAD=str(PROFILE / "review-input.so"),
        W3V_REVIEW_EVENTS=str(events),
        W3V_REVIEW_VDP=str(PROFILE / "flexe-vdp.so"),
    )
    process = subprocess.Popen(
        ["./flexe-agon-emulator"], cwd=PROFILE, env=environment,
        stdout=frontend_log, stderr=subprocess.STDOUT, start_new_session=True,
    )
    started = time.monotonic()
    report = {}
    try:
        reference = (APP / "reference.ppm").read_bytes()
        scene = RUN / "scene.ppm"
        deadline = time.monotonic() + 180
        while True:
            if process.poll() is not None:
                raise RuntimeError(
                    f"frontend exited during scene wait: {process.returncode}"
                )
            if (APP / "failure.dat").exists():
                raise RuntimeError("guest reported failure before review scene")
            observed = BASE.capture(events, process, scene)
            if observed == reference:
                break
            if time.monotonic() >= deadline:
                raise TimeoutError("exact direct-row scene did not appear")
            time.sleep(0.2)

        # The guest remains blocked in its real mos_getkey until this Enter.
        BASE.append_event(events, "key 40 1")
        time.sleep(0.05)
        BASE.append_event(events, "key 40 0")
        results = APP / "results.dat"
        BASE.wait_file(results, process, 30)
        replies = verify_results(results.read_bytes())
        if (APP / "failure.dat").exists():
            raise RuntimeError("guest saved failure state")

        uart = artifacts / "esp32-uart0.log"
        deadline = time.monotonic() + 20
        while True:
            text = uart.read_text(errors="replace") if uart.exists() else ""
            if ("Wolf VDPlet review finished." in text and
                    "wolf3d_scene_rows.vdpl C code." in text and
                    "MOS mode, cursor, callback, and buffers were restored." in text and
                    "/wolfrows *" in text):
                break
            if process.poll() is not None:
                raise RuntimeError("frontend exited before restored MOS prompt")
            if time.monotonic() >= deadline:
                raise TimeoutError("restored direct-row MOS prompt")
            time.sleep(0.1)

        mos_screen = RUN / "mos.ppm"
        if BASE.capture(events, process, mos_screen) == reference:
            raise AssertionError("display did not leave the direct-row scene")
        BASE.append_event(events, "quit")
        process.wait(timeout=15)
        if process.returncode != 0:
            raise RuntimeError(f"frontend return code {process.returncode}")
        stats = json.loads((artifacts / "stats.json").read_text())
        if any(stats.get(key) for key in
               ("failed", "unhandled", "unregistered", "unmapped")):
            raise AssertionError(stats)
        report = {
            "passed": True,
            "scope": (
                "exact direct-row full-MOS headless rehearsal; "
                "no human/physical claim"
            ),
            "scene_sha256": BASE.sha(scene),
            "reference_sha256": BASE.sha(APP / "reference.ppm"),
            "scene_exact": True,
            "replies": replies,
            "results_sha256": BASE.sha(results),
            "returned_to_mos_prompt": True,
            "keyboard_event_consumed": True,
            "callback_cleanup_and_cursor_enable_path_exercised": True,
            "backend_stats": stats,
            "module_sha256": BASE.sha(APP / "wolf3d_scene_rows.vdpl"),
            "copied_control_sha256": BASE.sha(APP / "wolf3d_scene.vdpl"),
            "review_binary_sha256": BASE.sha(APP / "review.bin"),
            "runtime_identities": (
                PROFILE / ".runtime.sha256"
            ).read_text().splitlines(),
            "helper_sha256": BASE.sha(PROFILE / "review-input.so"),
            "tradeoff": {
                "workspace_bytes_saved": 80608,
                "workspace_reduction_percent": 87.47,
                "direct_modelled_cycle_increase_percent": 32.93,
            },
            "GUI_launched": False,
            "elapsed_seconds": round(time.monotonic() - started, 3),
        }
    finally:
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
        frontend_log.close()
        report.setdefault("frontend_returncode", process.returncode)
        (RUN / "rehearsal.json").write_text(
            json.dumps(report, indent=2) + "\n"
        )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
