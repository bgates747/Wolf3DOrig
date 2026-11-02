#!/usr/bin/env python3
"""Finite runner for one separately authorized STARTUP host-ring observation."""

from __future__ import annotations

import csv
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import time


PROFILE = Path(__file__).resolve().parent
BASE_SOURCE = PROFILE / "runner_base.py"
if not BASE_SOURCE.is_file():
    BASE_SOURCE = PROFILE.parent / "audio-ring" / "runner.py"
spec = importlib.util.spec_from_file_location("wolf_ring_runner_base", BASE_SOURCE)
base = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(base)

OUTPUT = PROFILE / "ring-output-startup"
RUN = PROFILE / "audio-ring-startup-run"
EVENTS = RUN / "events.txt"
REPORT = RUN / "session.json"
ARTIFACTS = PROFILE / "last-run"

# The imported finite helpers refer to module globals. Bind them to the new,
# isolated paths while retaining the accepted supervision implementation.
base.PROFILE = PROFILE
base.OUTPUT = OUTPUT
base.RUN = RUN
base.EVENTS = EVENTS
base.REPORT = REPORT
base.ARTIFACTS = ARTIFACTS


def first_event(path: Path) -> dict | None:
    with path.open(newline="") as stream:
        return next(csv.DictReader(stream), None)


def startup_window_eligibility(summary: dict, reader: dict,
                               event: dict | None,
                               shot_bracket: list[int]) -> dict:
    shot_start, shot_end = shot_bracket
    window_start = int(summary.get("window_start_ns", -1))
    window_end = int(summary.get("window_end_ns", -1))
    setup_origin = int(summary.get("setup_origin_ns", -2))
    overlap = shot_start < window_end and shot_end > window_start
    result = {
        "mode": "startup",
        "shot_overlap": overlap,
        "expected_shot_overlap": False,
        "first_event_present": event is not None,
        "first_produced_before": None,
        "first_depth_before": None,
        "reasons": [],
    }
    if event is not None:
        try:
            result["first_produced_before"] = int(event["produced_before"])
            result["first_depth_before"] = int(event["before"])
        except (KeyError, TypeError, ValueError):
            result["reasons"].append("invalid_first_event")
    else:
        result["reasons"].append("missing_first_event")
    if result["first_produced_before"] != 0:
        result["reasons"].append("unknown_initial_production_history")
    if result["first_depth_before"] != 0:
        result["reasons"].append("unknown_initial_depth_history")
    if int(summary.get("window_after_ms", -1)) != 0:
        result["reasons"].append("wrong_window_offset")
    if window_start != setup_origin or window_end - window_start != 10_000_000_000:
        result["reasons"].append("wrong_actual_window")
    if not reader.get("schema_valid") or not reader.get("window_complete"):
        result["reasons"].append("incomplete_reader_window")
    if summary.get("cap_hit") or summary.get("arithmetic_error"):
        result["reasons"].append("observer_invalid")
    if overlap:
        result["reasons"].append("unexpected_shot_overlap")
    result["eligible"] = not result["reasons"]
    return result


def session_qualifies(outcomes: dict, reader_returncode: int | None,
                      eligibility: dict | None,
                      forced_cleanup: bool) -> bool:
    return (
        outcomes.get("startup") == "title_ready"
        and outcomes.get("functional") == "gameplay_ready"
        and outcomes.get("window") == "complete_startup"
        and outcomes.get("finalization") == "complete"
        and outcomes.get("cleanup") == "normal_process_exit"
        and reader_returncode == 0
        and eligibility is not None
        and eligibility.get("eligible") is True
        and eligibility.get("shot_overlap") is False
        and not forced_cleanup
    )


def main() -> int:
    subprocess.run(["sha256sum", "--check", "--status", ".runtime.sha256"],
                   cwd=PROFILE, check=True)
    base.reject_nonreal_audio_environment(dict(os.environ))
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
        "schema": "wolf3d-audio-ring-startup-session-v1",
        "measurement_mode": "startup",
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
    eligibility = None
    try:
        base.wait_text(process, lambda text: text.count(base.TITLE) >= 2,
                       40, t0_ns, "second application title")
        outcomes["startup"] = "title_ready"
        for _ in range(4):
            base.key_pair(40, 0.10, commands, t0_ns)
            time.sleep(0.65)
        base.wait_text(process, base.ordered_witnesses, 80, t0_ns,
                       "ordered loader witnesses")
        oracle = json.loads((PROFILE / "oracle.json").read_text())
        capture, readiness = base.capture_until_ready(
            process, commands, t0_ns, oracle,
        )
        report["gameplay_capture_sha256"] = base.sha(capture)
        report["gameplay_readiness"] = readiness
        report["gameplay_ready_ns"] = time.monotonic_ns()
        outcomes["functional"] = "gameplay_ready"

        base.wait_until(t0_ns, 92, process)
        base.key_pair(44, 0.05, commands, t0_ns)
        shot = commands[-2:]
        report["shot_command_bracket_ns"] = [
            shot[0]["before_ns"], shot[-1]["after_ns"],
        ]

        base.wait_until(t0_ns, 103, process)
        base.key_pair(41, 0.05, commands, t0_ns)
        base.wait_text(
            process,
            lambda value: "Thanks for playing Wolf3DOrig!" in value and "/wolf3d *" in value,
            150, t0_ns, "farewell and restored MOS prompt",
        )
        report["farewell_and_prompt"] = True
        base.append_command("quit", commands, t0_ns)
        process.wait(timeout=15)
        if process.returncode != 0:
            raise RuntimeError(f"frontend return code {process.returncode}")
        outcomes["cleanup"] = "normal_process_exit"

        summary_path = OUTPUT / "ring-summary.json"
        events_path = OUTPUT / "ring-events.csv"
        base.wait_observer_files(process, [summary_path, events_path], t0_ns)
        summary = json.loads(summary_path.read_text())
        reader_process = base.run_reader(
            summary_path, events_path,
            min(base.READER_TIMEOUT_SECONDS, base.remaining(
                t0_ns, base.WHOLE_SESSION_SECONDS - base.OWNED_CLEANUP_RESERVE_SECONDS,
            )),
        )
        reader_returncode = reader_process.returncode
        report["reader_returncode"] = reader_returncode
        reader = json.loads(reader_process.stdout)
        report["reader"] = reader
        report["observer_window_ns"] = [
            summary["window_start_ns"], summary["window_end_ns"],
        ]
        report["observer_setup_origin_ns"] = summary["setup_origin_ns"]
        report["observer_window_after_ms"] = summary["window_after_ms"]
        eligibility = startup_window_eligibility(
            summary, reader, first_event(events_path),
            report["shot_command_bracket_ns"],
        )
        report["startup_eligibility"] = eligibility
        report["shot_command_overlaps_observer_window"] = eligibility["shot_overlap"]
        outcomes["window"] = (
            "complete_startup" if reader_returncode == 0 and eligibility["eligible"]
            else "incomplete_startup"
        )
        outcomes["finalization"] = (
            "complete" if reader_returncode in (0, 1) else "invalid"
        )
        report["observer_summary_sha256"] = base.sha(summary_path)
        report["observer_events_sha256"] = base.sha(events_path)
        report["uart_sha256"] = base.sha(ARTIFACTS / "esp32-uart0.log")
    except Exception as error:
        report["error"] = f"{type(error).__name__}: {error}"
    finally:
        if process.poll() is None:
            forced = True
            cleanup_disposition = base.terminate_owned_process(process, t0_ns)
        frontend_log.close()
        if base.elapsed(t0_ns) > base.WHOLE_SESSION_SECONDS:
            outcomes["cleanup"] = "whole_session_ceiling_exceeded"
        elif forced:
            outcomes["cleanup"] = (
                "forced_owned_process_group_incomplete:" + cleanup_disposition
            )
        report["frontend_returncode"] = process.returncode
        report["elapsed_seconds"] = round(base.elapsed(t0_ns), 3)
        report["forced_cleanup"] = forced
        report["cleanup_disposition"] = cleanup_disposition
        report["session_passed"] = session_qualifies(
            outcomes, reader_returncode, eligibility, forced,
        )
        REPORT.write_text(json.dumps(report, indent=2) + "\n")
    return 0 if report["session_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
