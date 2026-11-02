#!/usr/bin/env python3
"""Device-free tests for the stopped Wolf STARTUP ring preparation."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock


HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("startup_ring_runner", HERE / "runner.py")
runner = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(runner)


def summary() -> dict:
    return {
        "setup_origin_ns": 100,
        "window_after_ms": 0,
        "window_start_ns": 100,
        "window_end_ns": 10_000_000_100,
        "cap_hit": False,
        "arithmetic_error": False,
    }


def reader_result() -> dict:
    return {"schema_valid": True, "window_complete": True}


def initial_event() -> dict:
    return {"produced_before": "0", "before": "0"}


def shot_after_window() -> list[int]:
    return [92_000_000_000, 92_050_000_000]


class StartupEligibilityTests(unittest.TestCase):
    def test_valid_startup_window_requires_true_nonoverlap(self) -> None:
        result = runner.startup_window_eligibility(
            summary(), reader_result(), initial_event(), shot_after_window(),
        )
        self.assertTrue(result["eligible"])
        self.assertFalse(result["shot_overlap"])
        self.assertEqual(result["first_produced_before"], 0)
        self.assertEqual(result["first_depth_before"], 0)

    def test_missing_or_wrong_initial_history_is_ineligible(self) -> None:
        missing = runner.startup_window_eligibility(
            summary(), reader_result(), None, shot_after_window(),
        )
        self.assertFalse(missing["eligible"])
        self.assertIn("missing_first_event", missing["reasons"])
        produced = initial_event()
        produced["produced_before"] = "64"
        wrong_produced = runner.startup_window_eligibility(
            summary(), reader_result(), produced, shot_after_window(),
        )
        self.assertIn("unknown_initial_production_history", wrong_produced["reasons"])
        depth = initial_event()
        depth["before"] = "1"
        wrong_depth = runner.startup_window_eligibility(
            summary(), reader_result(), depth, shot_after_window(),
        )
        self.assertIn("unknown_initial_depth_history", wrong_depth["reasons"])

    def test_wrong_window_or_incomplete_reader_is_ineligible(self) -> None:
        bad_summary = summary()
        bad_summary["window_after_ms"] = 90_000
        bad_summary["window_start_ns"] = 90_000_000_100
        bad_summary["window_end_ns"] = 100_000_000_100
        wrong = runner.startup_window_eligibility(
            bad_summary, reader_result(), initial_event(), shot_after_window(),
        )
        self.assertFalse(wrong["eligible"])
        self.assertIn("wrong_window_offset", wrong["reasons"])
        incomplete = runner.startup_window_eligibility(
            summary(), {"schema_valid": True, "window_complete": False},
            initial_event(), shot_after_window(),
        )
        self.assertIn("incomplete_reader_window", incomplete["reasons"])

    def test_unexpected_overlap_and_observer_failure_are_ineligible(self) -> None:
        bad_summary = summary()
        bad_summary["cap_hit"] = True
        result = runner.startup_window_eligibility(
            bad_summary, reader_result(), initial_event(), [5_000, 6_000],
        )
        self.assertFalse(result["eligible"])
        self.assertIn("observer_invalid", result["reasons"])
        self.assertIn("unexpected_shot_overlap", result["reasons"])

    def test_functional_reader_and_cleanup_failures_remain_terminal(self) -> None:
        outcomes = {
            "startup": "title_ready",
            "functional": "gameplay_ready",
            "window": "complete_startup",
            "finalization": "complete",
            "cleanup": "normal_process_exit",
        }
        eligibility = runner.startup_window_eligibility(
            summary(), reader_result(), initial_event(), shot_after_window(),
        )
        self.assertTrue(runner.session_qualifies(outcomes, 0, eligibility, False))
        for field, failure in (
            ("functional", "not_started"),
            ("window", "incomplete_startup"),
            ("finalization", "invalid"),
            ("cleanup", "forced_owned_process_group_incomplete:killed"),
        ):
            changed = dict(outcomes)
            changed[field] = failure
            self.assertFalse(runner.session_qualifies(changed, 0, eligibility, False))
        self.assertFalse(runner.session_qualifies(outcomes, 1, eligibility, False))
        self.assertFalse(runner.session_qualifies(outcomes, 0, eligibility, True))


class PreservedSupervisionTests(unittest.TestCase):
    def test_base_runner_is_the_accepted_finite_implementation(self) -> None:
        self.assertEqual(
            hashlib.sha256(runner.BASE_SOURCE.read_bytes()).hexdigest(),
            "f0ffe79892f9a93edc41f590bb02551583580e899b7232545253b1141962ca98",
        )
        self.assertEqual(runner.base.WHOLE_SESSION_SECONDS, 180)
        self.assertEqual(runner.base.GAMEPLAY_READY_SECONDS, 85)

    def test_real_audio_policy_is_preserved(self) -> None:
        runner.base.reject_nonreal_audio_environment({})
        runner.base.reject_nonreal_audio_environment({"SDL_AUDIODRIVER": "pulseaudio"})
        for driver in ("dummy", "disk", "alsa"):
            with self.assertRaises(SystemExit):
                runner.base.reject_nonreal_audio_environment({"SDL_AUDIODRIVER": driver})

    def test_late_gameplay_capture_is_rejected(self) -> None:
        oracle = json.loads((HERE / "oracle.json").read_text())
        late_t0 = time.monotonic_ns() - 86_000_000_000
        with self.assertRaises(TimeoutError):
            runner.base.capture_until_ready(None, [], late_t0, oracle)

    def test_stuck_reader_and_missing_final_files_are_bounded(self) -> None:
        with self.assertRaises(subprocess.TimeoutExpired):
            runner.base.run_bounded_subprocess(
                [sys.executable, "-c", "import time; time.sleep(60)"], 0.05,
            )

        class Exited:
            @staticmethod
            def poll():
                return 0

        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / "missing"
            with mock.patch.object(runner.base, "FINALIZATION_TIMEOUT_SECONDS", 0.05):
                with self.assertRaises(TimeoutError):
                    runner.base.wait_observer_files(
                        Exited(), [missing], time.monotonic_ns(),
                    )

    def test_owned_process_group_cleanup_is_bounded(self) -> None:
        process = subprocess.Popen(
            [sys.executable, "-c", "import time; time.sleep(60)"],
            start_new_session=True,
        )
        disposition = runner.base.terminate_owned_process(
            process, time.monotonic_ns(), term_timeout=0.1, kill_timeout=0.1,
        )
        self.assertIn(disposition, {"terminated", "killed"})
        self.assertIsNotNone(process.poll())

    def test_stager_has_no_launch_or_reservation_path(self) -> None:
        source = (HERE / "stage_oryx.py").read_text()
        self.assertNotIn("oryx_lease", source)
        self.assertNotIn("Popen", source)
        self.assertNotIn('["./flexe-agon-emulator"]', source)


if __name__ == "__main__":
    unittest.main()
