#!/usr/bin/env python3
"""Run the exact production-client fixture headlessly under an owned Oryx grant."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time


HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[3]
PROFILE = PROJECT / ".emulator/vdplet-client"
APP = PROFILE / "sdcard/wolfclient"
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


def verify_result(data: bytes) -> dict[str, int]:
    if len(data) != 16 or data[:4] != b"WVPC":
        raise AssertionError(data.hex())
    result = {
        "result": data[4],
        "status": data[5],
        "pending": data[6],
        "callback_error": data[7],
        "handle": int.from_bytes(data[8:10], "little"),
        "native_error": int.from_bytes(data[10:12], "little"),
        "token": int.from_bytes(data[12:14], "little"),
        "schema": int.from_bytes(data[14:16], "little"),
    }
    expected = {
        "result": 0, "status": 0, "pending": 0, "callback_error": 0,
        "handle": 0, "native_error": 0, "token": 7, "schema": 1,
    }
    if result != expected:
        raise AssertionError(result)
    return result


def main() -> None:
    subprocess.run(
        ["sha256sum", "--check", "--status", ".runtime.sha256"],
        cwd=PROFILE, check=True,
    )
    RUN.mkdir(exist_ok=True)
    for path in RUN.iterdir():
        if path.is_file():
            path.unlink()
    (APP / "client.dat").unlink(missing_ok=True)
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
    report: dict[str, object] = {}
    try:
        reference = (APP / "reference.ppm").read_bytes()
        scene = RUN / "scene.ppm"
        deadline = time.monotonic() + 180
        while True:
            if process.poll() is not None:
                raise RuntimeError(f"frontend exited during scene wait: {process.returncode}")
            observed = capture(events, process, scene)
            if observed == reference:
                break
            if time.monotonic() >= deadline:
                raise TimeoutError("exact copied-pixel scene did not appear")
            time.sleep(0.2)

        append_event(events, "key 40 1")
        time.sleep(0.05)
        append_event(events, "key 40 0")
        result_path = APP / "client.dat"
        wait_file(result_path, process, 30)
        result = verify_result(result_path.read_bytes())

        uart = artifacts / "esp32-uart0.log"
        deadline = time.monotonic() + 20
        while True:
            text = uart.read_text(errors="replace") if uart.exists() else ""
            if "/wolfclient *" in text:
                break
            if process.poll() is not None:
                raise RuntimeError("frontend exited before restored MOS prompt")
            if time.monotonic() >= deadline:
                raise TimeoutError("restored MOS prompt")
            time.sleep(0.1)

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
            "scope": "finite full-MOS production-client rehearsal; no physical claim",
            "scene_sha256": sha(scene),
            "reference_sha256": sha(APP / "reference.ppm"),
            "scene_exact": True,
            "result": result,
            "result_sha256": sha(result_path),
            "returned_to_mos_prompt": True,
            "keyboard_event_consumed": True,
            "owned_handle_unloaded": True,
            "callback_and_owned_buffers_released": True,
            "backend_stats": stats,
            "module_sha256": sha(APP / "wolf3d.vdpl"),
            "client_sha256": sha(APP / "client.bin"),
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
    import sys as _fw_sys
    from pathlib import Path as _FWPath
    _fw_sys.path.insert(0, str(_FWPath(__file__).resolve().parents[4] / "tools"))
    from wolf_firmware import legacy_exception
    legacy_exception(_fw_sys.argv, 'src/asm/wolf3d_vdplet_client/scripts/rehearse.py')

    main()
