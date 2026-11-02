#!/usr/bin/env python3
"""Device-free checks for corrected late-window Pi preparation."""

from __future__ import annotations

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
OLD = HERE.parent / "audio-ring"
STARTUP = HERE.parent / "audio-ring-startup"
spec = importlib.util.spec_from_file_location("accepted_late_runner", OLD / "runner.py")
runner = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(runner)


def complete_outcomes() -> dict:
    return {
        "startup": "title_ready",
        "functional": "gameplay_ready",
        "window": "complete",
        "finalization": "complete",
        "cleanup": "normal_process_exit",
    }


class CorrectedLatePreparationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.preparation = json.loads((HERE / "preparation.json").read_text())

    def test_offline_verifier_accepts_exact_retained_selection(self) -> None:
        result = subprocess.run(
            [sys.executable, str(HERE / "verify_preparation.py")],
            check=True, text=True, stdout=subprocess.PIPE,
        )
        receipt = json.loads(result.stdout)
        self.assertEqual(receipt["status"], "verified-pi-device-free")
        self.assertFalse(receipt["target_contact"])

    def test_original_late_overlap_and_failure_semantics_remain(self) -> None:
        outcomes = complete_outcomes()
        self.assertTrue(runner.session_qualifies(outcomes, 0, True, False))
        self.assertFalse(runner.session_qualifies(outcomes, 0, False, False))
        self.assertFalse(runner.session_qualifies(outcomes, 1, True, False))
        self.assertFalse(runner.session_qualifies(outcomes, 0, True, True))
        for field, failure in (
            ("functional", "not_started"),
            ("window", "incomplete_no_command_overlap"),
            ("finalization", "invalid"),
            ("cleanup", "forced_owned_process_group_incomplete:killed"),
        ):
            changed = dict(outcomes)
            changed[field] = failure
            self.assertFalse(runner.session_qualifies(changed, 0, True, False))

    def test_late_eligibility_has_no_startup_history_gate(self) -> None:
        # The accepted late runner's qualification contract takes only the
        # functional outcomes, reader status, actual overlap and cleanup state.
        # No initial production/depth witness is accepted or required.
        self.assertTrue(
            runner.session_qualifies(complete_outcomes(), 0, True, False)
        )
        measurement = self.preparation["measurement"]
        self.assertEqual(measurement["observer_window_after_ms"], 90000)
        self.assertTrue(measurement["shot_overlap_required"])
        self.assertFalse(measurement["initial_empty_history_required"])
        self.assertTrue(measurement["preserve_censoring"])

    def test_original_gameplay_oracle_fields_are_unchanged(self) -> None:
        old = json.loads((OLD / "oracle.json").read_text())
        startup = json.loads((STARTUP / "oracle.json").read_text())
        fields = (
            "width", "height", "hud_y", "hud_height", "hud_agnb_sha256",
            "minimum_hud_blue_fraction", "minimum_hud_bright_fraction",
            "minimum_playfield_nonblack_fraction",
            "minimum_playfield_distinct_colours",
        )
        self.assertEqual({key: old[key] for key in fields},
                         {key: startup[key] for key in fields})

    def test_real_audio_and_finite_supervision_are_unchanged(self) -> None:
        runner.reject_nonreal_audio_environment({})
        runner.reject_nonreal_audio_environment({"SDL_AUDIODRIVER": "pulseaudio"})
        for driver in ("dummy", "disk", "alsa"):
            with self.assertRaises(SystemExit):
                runner.reject_nonreal_audio_environment({"SDL_AUDIODRIVER": driver})
        self.assertEqual(runner.GAMEPLAY_READY_SECONDS, 85)
        self.assertEqual(runner.WHOLE_SESSION_SECONDS, 180)
        invocation = self.preparation["finite_invocation"]
        self.assertEqual(invocation["shot_seconds"], 92)
        self.assertEqual(invocation["escape_seconds"], 103)
        self.assertEqual(invocation["farewell_seconds"], 150)
        self.assertFalse(invocation["retry"])

    def test_reader_finalization_and_owned_cleanup_remain_bounded(self) -> None:
        with self.assertRaises(subprocess.TimeoutExpired):
            runner.run_bounded_subprocess(
                [sys.executable, "-c", "import time; time.sleep(60)"], 0.05,
            )

        class Exited:
            @staticmethod
            def poll():
                return 0

        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / "missing"
            with mock.patch.object(runner, "FINALIZATION_TIMEOUT_SECONDS", 0.05):
                with self.assertRaises(TimeoutError):
                    runner.wait_observer_files(
                        Exited(), [missing], time.monotonic_ns(),
                    )
        process = subprocess.Popen(
            [sys.executable, "-c", "import time; time.sleep(60)"],
            start_new_session=True,
        )
        disposition = runner.terminate_owned_process(
            process, time.monotonic_ns(), term_timeout=0.1, kill_timeout=0.1,
        )
        self.assertIn(disposition, {"terminated", "killed"})
        self.assertIsNotNone(process.poll())

    def test_preparation_records_no_target_side_effect(self) -> None:
        self.assertTrue(all(self.preparation["not_performed"].values()))
        self.assertFalse((HERE / "stage_oryx.py").exists())
        self.assertFalse((HERE / "prepare_profile.py").exists())
        self.assertFalse(self.preparation["physical_priority_conflict"])


if __name__ == "__main__":
    unittest.main()
