#!/usr/bin/env python3
"""Finite stopped-profile runner for one separately authorized Wolf ring run."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time


PROFILE = Path(__file__).resolve().parent
RUN = PROFILE / "audio-ring-run"
ARTIFACTS = PROFILE / "last-run"
OUTPUT = PROFILE / "ring-output"
EVENTS = RUN / "events.txt"
REPORT = RUN / "session.json"
WHOLE_SESSION_SECONDS = 180
OWNED_CLEANUP_RESERVE_SECONDS = 10
GAMEPLAY_READY_SECONDS = 85
READER_TIMEOUT_SECONDS = 5
FINALIZATION_TIMEOUT_SECONDS = 5

TITLE = "Wolf3DOrig App 0.1.0 Alpha 1"
LOAD_WITNESSES = [
    "Loading floor wall/door textures (tiles.agnb)",
    "Loading floor static sprite art (sprites.agnb)",
    "Loading original in-game status panel (hud.agnb)",
    "Loading native-rate Wolf3D sound effects (sfx.agnb)",
    "Uploading tilemap and rendering initial floor view",
    "VDPL LOAD",
]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def elapsed(t0_ns: int) -> float:
    return (time.monotonic_ns() - t0_ns) / 1_000_000_000


def remaining(t0_ns: int, deadline_seconds: float,
              reserve_cleanup: bool = True) -> float:
    ceiling = WHOLE_SESSION_SECONDS
    if reserve_cleanup:
        ceiling -= OWNED_CLEANUP_RESERVE_SECONDS
    deadline_seconds = min(deadline_seconds, ceiling)
    value = deadline_seconds - elapsed(t0_ns)
    if value <= 0:
        raise TimeoutError(f"deadline T0+{deadline_seconds}s")
    return value


def wait_until(t0_ns: int, seconds: float, process: subprocess.Popen) -> None:
    while elapsed(t0_ns) < seconds:
        remaining(t0_ns, seconds)
        if process.poll() is not None:
            raise RuntimeError(f"frontend exited early: {process.returncode}")
        time.sleep(min(0.05, seconds - elapsed(t0_ns)))


def uart_text() -> str:
    path = ARTIFACTS / "esp32-uart0.log"
    return path.read_text(errors="replace") if path.is_file() else ""


def wait_text(process: subprocess.Popen, predicate, deadline: float, t0_ns: int,
              description: str) -> str:
    while elapsed(t0_ns) < deadline:
        remaining(t0_ns, deadline)
        text = uart_text()
        if predicate(text):
            return text
        if process.poll() is not None:
            raise RuntimeError(f"frontend exited before {description}")
        time.sleep(0.05)
    raise TimeoutError(description)


def append_command(command: str, records: list[dict], t0_ns: int) -> None:
    before = time.monotonic_ns()
    with EVENTS.open("a") as stream:
        stream.write(command + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    after = time.monotonic_ns()
    records.append({
        "command": command,
        "before_ns": before,
        "after_ns": after,
        "runner_seconds": (before - t0_ns) / 1_000_000_000,
    })


def key_pair(scan: int, hold: float, records: list[dict], t0_ns: int) -> None:
    append_command(f"key {scan} 1", records, t0_ns)
    time.sleep(hold)
    append_command(f"key {scan} 0", records, t0_ns)


def read_ppm(path: Path) -> tuple[int, int, bytes]:
    with path.open("rb") as stream:
        if stream.readline() != b"P6\n":
            raise ValueError("not binary PPM")
        size = stream.readline()
        maximum = stream.readline()
        width, height = map(int, size.split())
        if maximum != b"255\n":
            raise ValueError("unexpected PPM range")
        pixels = stream.read()
    if len(pixels) != width * height * 3:
        raise ValueError("incomplete PPM")
    return width, height, pixels


def gameplay_ready(path: Path, oracle: dict) -> dict:
    width, height, pixels = read_ppm(path)
    if (width, height) != (oracle["width"], oracle["height"]):
        return {"ready": False, "reason": "geometry", "width": width, "height": height}
    hud_start = oracle["hud_y"] * width * 3
    hud = pixels[hud_start:]
    playfield = pixels[:hud_start]
    hud_pixels = len(hud) // 3
    blue = bright = nonblack = 0
    for offset in range(0, len(hud), 3):
        r, g, b = hud[offset:offset + 3]
        blue += b >= 128 and b > r + 32 and b > g + 16
        bright += r >= 192 and g >= 192 and b >= 192
    colours = set()
    for offset in range(0, len(playfield), 3):
        colour = tuple(playfield[offset:offset + 3])
        colours.add(colour)
        nonblack += colour != (0, 0, 0)
    metrics = {
        "hud_blue_fraction": blue / hud_pixels,
        "hud_bright_fraction": bright / hud_pixels,
        "playfield_nonblack_fraction": nonblack / (len(playfield) // 3),
        "playfield_distinct_colours": len(colours),
    }
    ready = (
        metrics["hud_blue_fraction"] >= oracle["minimum_hud_blue_fraction"]
        and metrics["hud_bright_fraction"] >= oracle["minimum_hud_bright_fraction"]
        and metrics["playfield_nonblack_fraction"] >= oracle["minimum_playfield_nonblack_fraction"]
        and metrics["playfield_distinct_colours"] >= oracle["minimum_playfield_distinct_colours"]
    )
    return {"ready": ready, "reason": "accepted" if ready else "predicate", **metrics}


def capture_until_ready(process: subprocess.Popen, records: list[dict],
                        t0_ns: int, oracle: dict) -> tuple[Path, dict]:
    capture = RUN / "gameplay.ppm"
    while elapsed(t0_ns) < GAMEPLAY_READY_SECONDS:
        capture.unlink(missing_ok=True)
        append_command("capture " + str(capture), records, t0_ns)
        limit_ns = min(
            time.monotonic_ns() + 3_000_000_000,
            t0_ns + GAMEPLAY_READY_SECONDS * 1_000_000_000,
        )
        while time.monotonic_ns() < limit_ns and not capture.is_file():
            if process.poll() is not None:
                raise RuntimeError("frontend exited during gameplay capture")
            time.sleep(0.05)
        if capture.is_file():
            try:
                result = gameplay_ready(capture, oracle)
                if result["ready"]:
                    if elapsed(t0_ns) >= GAMEPLAY_READY_SECONDS:
                        raise TimeoutError("late gameplay-ready framebuffer")
                    return capture, result
            except (OSError, ValueError):
                pass
        time.sleep(0.25)
    raise TimeoutError("gameplay-ready framebuffer by T0+85s")


def wait_observer_files(process: subprocess.Popen, paths: list[Path],
                        t0_ns: int) -> None:
    deadline = time.monotonic() + min(
        FINALIZATION_TIMEOUT_SECONDS,
        remaining(t0_ns, WHOLE_SESSION_SECONDS - OWNED_CLEANUP_RESERVE_SECONDS),
    )
    while not all(path.is_file() for path in paths):
        if process.poll() is None:
            raise RuntimeError("frontend still running during observer finalization")
        if time.monotonic() >= deadline:
            missing = [str(path) for path in paths if not path.is_file()]
            raise TimeoutError(f"observer finalization: {missing}")
        time.sleep(0.05)


def run_bounded_subprocess(command: list[str], timeout: float) -> subprocess.CompletedProcess:
    return subprocess.run(
        command, text=True, stdout=subprocess.PIPE, timeout=timeout,
    )


def run_reader(summary: Path, events: Path, timeout: float) -> subprocess.CompletedProcess:
    return run_bounded_subprocess(
        [sys.executable, str(PROFILE / "read_residence.py"),
         str(summary), str(events)], timeout,
    )


def terminate_owned_process(process: subprocess.Popen, t0_ns: int,
                            term_timeout: float = 5,
                            kill_timeout: float = 2) -> str:
    if process.poll() is not None:
        return "already_exited"
    os.killpg(process.pid, signal.SIGTERM)
    try:
        available = remaining(t0_ns, WHOLE_SESSION_SECONDS, reserve_cleanup=False)
        process.wait(timeout=min(term_timeout, available))
        return "terminated"
    except (subprocess.TimeoutExpired, TimeoutError):
        os.killpg(process.pid, signal.SIGKILL)
    try:
        available = remaining(t0_ns, WHOLE_SESSION_SECONDS, reserve_cleanup=False)
        process.wait(timeout=min(kill_timeout, available))
        return "killed"
    except (subprocess.TimeoutExpired, TimeoutError):
        return "kill_wait_timeout"


def session_qualifies(outcomes: dict, reader_returncode: int | None,
                      overlaps: bool, forced_cleanup: bool) -> bool:
    return (
        outcomes.get("startup") == "title_ready"
        and outcomes.get("functional") == "gameplay_ready"
        and outcomes.get("window") == "complete"
        and outcomes.get("finalization") == "complete"
        and outcomes.get("cleanup") == "normal_process_exit"
        and reader_returncode == 0
        and overlaps
        and not forced_cleanup
    )


def ordered_witnesses(text: str) -> bool:
    offset = 0
    for witness in LOAD_WITNESSES:
        offset = text.find(witness, offset)
        if offset < 0:
            return False
        offset += len(witness)
    return True


def reject_nonreal_audio_environment(environment: dict[str, str]) -> None:
    driver = environment.get("SDL_AUDIODRIVER", "").strip().lower()
    if driver in {"dummy", "disk"}:
        raise SystemExit(f"refusing non-real SDL audio driver: {driver}")
    if driver and driver != "pulseaudio":
        raise SystemExit(f"refusing unpinned SDL audio driver: {driver}")


def main() -> int:
    subprocess.run(["sha256sum", "--check", "--status", ".runtime.sha256"],
                   cwd=PROFILE, check=True)
    reject_nonreal_audio_environment(dict(os.environ))
    if any(OUTPUT.iterdir()):
        raise SystemExit(f"observer output directory is not fresh: {OUTPUT}")
    RUN.mkdir(exist_ok=True)
    for path in RUN.iterdir():
        if path.is_file():
            path.unlink()
    EVENTS.write_text("")
    ARTIFACTS.mkdir(exist_ok=True)
    for name in ("esp32-uart0.log", "stats.json", "final.ppm"):
        (ARTIFACTS / name).unlink(missing_ok=True)

    environment = dict(os.environ)
    environment.pop("BASH_ENV", None)
    environment.update(
        SDL_VIDEODRIVER="dummy",
        SDL_AUDIODRIVER="pulseaudio",
        LD_PRELOAD=str(PROFILE / "review-input.so"),
        W3V_REVIEW_EVENTS=str(EVENTS),
        W3V_REVIEW_VDP=str(PROFILE / "flexe-vdp.so"),
    )
    commands: list[dict] = []
    outcomes = {
        "startup": "not_started", "functional": "not_started",
        "window": "not_started", "finalization": "not_started",
        "cleanup": "not_started",
    }
    report: dict = {
        "schema": "wolf3d-audio-ring-session-v1",
        "scope": "host ring only; no event/sample/device/speaker attribution",
        "outcomes": outcomes,
        "commands": commands,
    }
    t0_ns = time.monotonic_ns()
    report["runner_t0_ns"] = t0_ns
    frontend_log = (RUN / "frontend.log").open("w")
    process = subprocess.Popen(
        ["./flexe-agon-emulator"], cwd=PROFILE, env=environment,
        stdout=frontend_log, stderr=subprocess.STDOUT, start_new_session=True,
    )
    forced = False
    cleanup_disposition = "not_needed"
    reader_returncode = None
    overlaps = False
    try:
        wait_text(process, lambda text: text.count(TITLE) >= 2, 40, t0_ns,
                  "second application title")
        outcomes["startup"] = "title_ready"
        for _ in range(4):
            key_pair(40, 0.10, commands, t0_ns)
            time.sleep(0.65)
        wait_text(process, ordered_witnesses, 80, t0_ns, "ordered loader witnesses")
        oracle = json.loads((PROFILE / "oracle.json").read_text())
        capture, readiness = capture_until_ready(process, commands, t0_ns, oracle)
        report["gameplay_capture_sha256"] = sha(capture)
        report["gameplay_readiness"] = readiness
        report["gameplay_ready_ns"] = time.monotonic_ns()
        outcomes["functional"] = "gameplay_ready"

        wait_until(t0_ns, 92, process)
        key_pair(44, 0.05, commands, t0_ns)
        shot = commands[-2:]
        report["shot_command_bracket_ns"] = [shot[0]["before_ns"], shot[-1]["after_ns"]]

        wait_until(t0_ns, 103, process)
        key_pair(41, 0.05, commands, t0_ns)
        text = wait_text(
            process,
            lambda value: "Thanks for playing Wolf3DOrig!" in value and "/wolf3d *" in value,
            150, t0_ns, "farewell and restored MOS prompt",
        )
        report["farewell_and_prompt"] = True
        append_command("quit", commands, t0_ns)
        process.wait(timeout=15)
        if process.returncode != 0:
            raise RuntimeError(f"frontend return code {process.returncode}")
        outcomes["cleanup"] = "normal_process_exit"

        summary_path = OUTPUT / "ring-summary.json"
        events_path = OUTPUT / "ring-events.csv"
        wait_observer_files(process, [summary_path, events_path], t0_ns)
        summary = json.loads(summary_path.read_text())
        shot_start, shot_end = report["shot_command_bracket_ns"]
        overlaps = shot_start < summary["window_end_ns"] and shot_end > summary["window_start_ns"]
        report["shot_command_overlaps_observer_window"] = overlaps
        report["observer_window_ns"] = [summary["window_start_ns"], summary["window_end_ns"]]
        report["observer_setup_origin_ns"] = summary["setup_origin_ns"]
        report["observer_window_after_ms"] = summary["window_after_ms"]
        if not overlaps:
            outcomes["window"] = "incomplete_no_command_overlap"
            raise RuntimeError("shot command did not overlap observer window")
        reader = run_reader(
            summary_path, events_path,
            min(READER_TIMEOUT_SECONDS, remaining(
                t0_ns, WHOLE_SESSION_SECONDS - OWNED_CLEANUP_RESERVE_SECONDS)),
        )
        reader_returncode = reader.returncode
        report["reader_returncode"] = reader_returncode
        report["reader"] = json.loads(reader.stdout)
        outcomes["window"] = "complete" if reader_returncode == 0 else "incomplete"
        outcomes["finalization"] = "complete" if reader_returncode in (0, 1) else "invalid"
        report["observer_summary_sha256"] = sha(summary_path)
        report["observer_events_sha256"] = sha(events_path)
        report["uart_sha256"] = sha(ARTIFACTS / "esp32-uart0.log")
    except Exception as error:
        report["error"] = f"{type(error).__name__}: {error}"
    finally:
        if process.poll() is None:
            forced = True
            cleanup_disposition = terminate_owned_process(process, t0_ns)
        frontend_log.close()
        if elapsed(t0_ns) > WHOLE_SESSION_SECONDS:
            outcomes["cleanup"] = "whole_session_ceiling_exceeded"
        elif forced:
            outcomes["cleanup"] = (
                "forced_owned_process_group_incomplete:" + cleanup_disposition
            )
        report["frontend_returncode"] = process.returncode
        report["elapsed_seconds"] = round(elapsed(t0_ns), 3)
        report["forced_cleanup"] = forced
        report["cleanup_disposition"] = cleanup_disposition
        report["session_passed"] = session_qualifies(
            outcomes, reader_returncode, overlaps, forced,
        )
        REPORT.write_text(json.dumps(report, indent=2) + "\n")
    return 0 if report["session_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
