#!/usr/bin/env python3
"""Device-free structural tests for the stopped Wolf audio-ring integration."""

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
spec = importlib.util.spec_from_file_location("audio_ring_runner", HERE / "runner.py")
runner = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(runner)


def ppm(path: Path, width: int, height: int, top: tuple[int, int, int],
        bottom: tuple[int, int, int]) -> None:
    pixels = bytearray()
    for y in range(height):
        colour = bottom if y >= 200 else top
        for x in range(width):
            if y < 200 and x % 7 == 0:
                pixels.extend(((x * 17) & 255, (y * 5) & 255, 85))
            elif y >= 200 and x % 10 == 0:
                pixels.extend((255, 255, 255))
            else:
                pixels.extend(colour)
    path.write_bytes(f"P6\n{width} {height}\n255\n".encode() + pixels)


class StoppedIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.oracle = json.loads((HERE / "oracle.json").read_text())

    def test_structural_gameplay_oracle_accepts_hud_and_playfield(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "frame.ppm"
            ppm(path, 320, 240, (85, 85, 85), (0, 0, 255))
            self.assertTrue(runner.gameplay_ready(path, self.oracle)["ready"])

    def test_structural_gameplay_oracle_rejects_blank_loader(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "frame.ppm"
            ppm(path, 320, 240, (0, 0, 0), (0, 0, 0))
            self.assertFalse(runner.gameplay_ready(path, self.oracle)["ready"])

    def test_loader_witnesses_must_be_ordered(self) -> None:
        text = "\n".join(runner.LOAD_WITNESSES)
        self.assertTrue(runner.ordered_witnesses(text))
        self.assertFalse(runner.ordered_witnesses("\n".join(reversed(runner.LOAD_WITNESSES))))

    def test_runner_preserves_real_audio(self) -> None:
        source = (HERE / "runner.py").read_text()
        self.assertNotIn('SDL_AUDIODRIVER="dummy"', source)
        self.assertIn('SDL_AUDIODRIVER="pulseaudio"', source)
        self.assertIn('SDL_VIDEODRIVER="dummy"', source)
        with self.assertRaises(SystemExit):
            runner.reject_nonreal_audio_environment({"SDL_AUDIODRIVER": "dummy"})
        runner.reject_nonreal_audio_environment({})
        runner.reject_nonreal_audio_environment({"SDL_AUDIODRIVER": "pulseaudio"})
        with self.assertRaises(SystemExit):
            runner.reject_nonreal_audio_environment({"SDL_AUDIODRIVER": "alsa"})

    def test_runner_is_finite_and_has_no_retry(self) -> None:
        source = (HERE / "runner.py").read_text()
        self.assertIn("WHOLE_SESSION_SECONDS = 180", source)
        self.assertNotIn("retry", source.lower())
        self.assertIn('wait_until(t0_ns, 92', source)
        self.assertIn('wait_until(t0_ns, 103', source)

    def test_late_gameplay_capture_is_rejected(self) -> None:
        late_t0 = time.monotonic_ns() - 86_000_000_000
        with self.assertRaises(TimeoutError):
            runner.capture_until_ready(None, [], late_t0, self.oracle)

    def test_stuck_reader_is_killed_by_timeout(self) -> None:
        started = time.monotonic()
        with self.assertRaises(subprocess.TimeoutExpired):
            runner.run_bounded_subprocess(
                [sys.executable, "-c", "import time; time.sleep(60)"], 0.05,
            )
        self.assertLess(time.monotonic() - started, 1)

    def test_missing_final_files_have_a_real_timeout(self) -> None:
        class Exited:
            @staticmethod
            def poll():
                return 0

        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / "missing"
            started = time.monotonic()
            with mock.patch.object(runner, "FINALIZATION_TIMEOUT_SECONDS", 0.05):
                with self.assertRaises(TimeoutError):
                    runner.wait_observer_files(
                        Exited(), [missing], time.monotonic_ns(),
                    )
            self.assertLess(time.monotonic() - started, 1)

    def test_owned_process_group_cleanup_is_bounded(self) -> None:
        process = subprocess.Popen(
            [sys.executable, "-c", "import time; time.sleep(60)"],
            start_new_session=True,
        )
        disposition = runner.terminate_owned_process(
            process, time.monotonic_ns(), term_timeout=0.1, kill_timeout=0.1,
        )
        self.assertIn(disposition, {"terminated", "killed"})
        self.assertIsNotNone(process.poll())

    def test_reader_success_cannot_override_failed_functional_outcome(self) -> None:
        outcomes = {
            "startup": "title_ready",
            "functional": "not_started",
            "window": "complete",
            "finalization": "complete",
            "cleanup": "normal_process_exit",
        }
        self.assertFalse(runner.session_qualifies(outcomes, 0, True, False))
        outcomes["functional"] = "gameplay_ready"
        self.assertTrue(runner.session_qualifies(outcomes, 0, True, False))
        self.assertFalse(runner.session_qualifies(outcomes, 0, True, True))

    def test_stager_never_launches_or_reserves(self) -> None:
        source = (HERE / "stage_oryx.py").read_text()
        self.assertNotIn("oryx_lease", source)
        self.assertNotIn('["./flexe-agon-emulator"]', source)
        self.assertNotIn("Popen", source)


if __name__ == "__main__":
    unittest.main()
