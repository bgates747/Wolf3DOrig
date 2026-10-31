#!/usr/bin/env python3
"""Headlessly rehearse the exact full-MOS review under an owned Oryx lease."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import signal
import struct
import subprocess
import time


HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[2]
PROFILE = PROJECT / ".emulator/vdplet-review"
APP = PROFILE / "sdcard/wolfvdpl"
RUN = PROFILE / "rehearsal-run"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def append_event(path: Path, line: str) -> None:
    with path.open("a") as stream:
        stream.write(line + "\n")


def wait_file(path: Path, process: subprocess.Popen, timeout: float) -> None:
    deadline = time.monotonic() + timeout
    while not path.is_file():
        if process.poll() is not None:
            raise RuntimeError(f"frontend exited before {path.name}: {process.returncode}")
        if time.monotonic() >= deadline:
            raise TimeoutError(path)
        time.sleep(0.05)


def capture(events: Path, process: subprocess.Popen, destination: Path) -> bytes:
    destination.unlink(missing_ok=True)
    append_event(events, "capture " + str(destination))
    deadline = time.monotonic() + 10
    while True:
        if destination.exists():
            try:
                with destination.open("rb") as stream:
                    magic = stream.readline()
                    size = stream.readline()
                    scale = stream.readline()
                    header = stream.tell()
                width, height = map(int, size.split())
                if (magic == b"P6\n" and scale == b"255\n" and
                        destination.stat().st_size == header + width * height * 3):
                    return destination.read_bytes()
            except (OSError, ValueError):
                pass
        if process.poll() is not None:
            raise RuntimeError("frontend exited during framebuffer capture")
        if time.monotonic() >= deadline:
            raise TimeoutError(destination)
        time.sleep(0.05)


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
    if replies[0]["value"] != 31 or not replies[1]["value"]:
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
                raise RuntimeError(f"frontend exited during scene wait: {process.returncode}")
            if (APP / "failure.dat").exists():
                raise RuntimeError("guest reported failure before review scene")
            observed = capture(events, process, scene)
            if observed == reference:
                break
            if time.monotonic() >= deadline:
                raise TimeoutError("exact module scene did not appear")
            time.sleep(0.2)

        # Exact guest remains blocked at mos_getkey until this injected Enter.
        append_event(events, "key 40 1")
        time.sleep(0.05)
        append_event(events, "key 40 0")
        results = APP / "results.dat"
        wait_file(results, process, 30)
        replies = verify_results(results.read_bytes())
        if (APP / "failure.dat").exists():
            raise RuntimeError("guest saved failure state")

        uart = artifacts / "esp32-uart0.log"
        deadline = time.monotonic() + 20
        while True:
            text = uart.read_text(errors="replace") if uart.exists() else ""
            if "Wolf VDPlet review finished." in text and "/wolfvdpl *" in text:
                break
            if process.poll() is not None:
                raise RuntimeError("frontend exited before restored MOS prompt")
            if time.monotonic() >= deadline:
                raise TimeoutError("restored MOS prompt")
            time.sleep(0.1)

        mos_screen = RUN / "mos.ppm"
        if capture(events, process, mos_screen) == reference:
            raise AssertionError("display did not leave the module scene")
        append_event(events, "quit")
        process.wait(timeout=15)
        if process.returncode != 0:
            raise RuntimeError(f"frontend return code {process.returncode}")
        stats = json.loads((artifacts / "stats.json").read_text())
        if any(stats.get(key) for key in
               ("failed", "unhandled", "unregistered", "unmapped")):
            raise AssertionError(stats)
        report = {
            "passed": True,
            "scope": "exact full-MOS headless rehearsal; no human/physical claim",
            "scene_sha256": sha(scene),
            "reference_sha256": sha(APP / "reference.ppm"),
            "scene_exact": True,
            "replies": replies,
            "results_sha256": sha(results),
            "returned_to_mos_prompt": True,
            "keyboard_event_consumed": True,
            "callback_cleanup_and_cursor_enable_path_exercised": True,
            "backend_stats": stats,
            "module_sha256": sha(APP / "wolf3d_scene.vdpl"),
            "review_binary_sha256": sha(APP / "review.bin"),
            "runtime_identities": (PROFILE / ".runtime.sha256").read_text().splitlines(),
            "helper_sha256": sha(PROFILE / "review-input.so"),
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
        (RUN / "rehearsal.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
