#!/usr/bin/env python3
"""Offline checks for custody-only corrected late profile staging."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
import unittest


HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("late_target_prepare", HERE / "prepare_profile.py")
prepare = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(prepare)


class TargetStagingTests(unittest.TestCase):
    def test_launcher_rewrite_changes_only_private_output_path(self) -> None:
        old = "/profile-r02/ring-output"
        new = "/profile-corrected/ring-output-late-corrected"
        source = (
            "#!/bin/bash\n"
            f'export FLEXE_RING_OBSERVER_DIR="{old}"\n'
            'export FLEXE_RING_WINDOW_AFTER_MS="90000"\n'
            'vdp_name="flexe-vdp.so"\n'
        )
        rewritten = prepare.rewrite_launcher(source, old, new)
        self.assertEqual(
            rewritten,
            source.replace(old, new),
        )
        self.assertEqual(rewritten.count('FLEXE_RING_WINDOW_AFTER_MS="90000"'), 1)

    def test_launcher_rewrite_rejects_path_or_offset_drift(self) -> None:
        with self.assertRaises(ValueError):
            prepare.rewrite_launcher(
                'export FLEXE_RING_WINDOW_AFTER_MS="90000"\n', "missing", "new",
            )
        with self.assertRaises(ValueError):
            prepare.rewrite_launcher(
                'export FLEXE_RING_OBSERVER_DIR="old"\n'
                'export FLEXE_RING_WINDOW_AFTER_MS="0"\n', "old", "new",
            )

    def test_runtime_manifest_parser_preserves_exact_members(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            profile = Path(directory)
            (profile / ".runtime.sha256").write_text(
                "a" * 64 + "  flexe-agon-emulator\n"
                + "b" * 64 + "  flexe-vdp.so\n"
                + "c" * 64 + "  runner.py\n"
            )
            self.assertEqual(
                prepare.runtime_map(profile),
                {
                    "flexe-agon-emulator": "a" * 64,
                    "flexe-vdp.so": "b" * 64,
                    "runner.py": "c" * 64,
                },
            )

    def test_stager_requires_live_lease_before_target_contact(self) -> None:
        source = (HERE / "stage_oryx.py").read_text()
        assert_owner = source.index('"assert-owner"')
        first_ssh = source.index('["ssh"')
        self.assertLess(assert_owner, first_ssh)
        self.assertIn('parser.add_argument("--lease", required=True)', source)

    def test_target_tooling_contains_no_build_or_launch(self) -> None:
        prepare_source = (HERE / "prepare_profile.py").read_text()
        stage_source = (HERE / "stage_oryx.py").read_text()
        self.assertNotIn("compile_command", prepare_source)
        self.assertNotIn("pkg-config", prepare_source)
        self.assertNotIn("shutil.which", prepare_source)
        self.assertNotIn("Popen", prepare_source + stage_source)
        self.assertNotIn('["./flexe-agon-emulator"]', prepare_source + stage_source)

    def test_exact_selected_pins_are_frozen(self) -> None:
        self.assertEqual(
            prepare.PINS["backend"],
            "943f432fecb96689f3a0d2ae80c72d08e20903dfe2a58a00ba88d8c7727ad400",
        )
        self.assertEqual(
            prepare.PINS["runner"],
            "f0ffe79892f9a93edc41f590bb02551583580e899b7232545253b1141962ca98",
        )
        self.assertEqual(
            prepare.PINS["oracle"],
            "ea4f7e644d3fb8ba21ab2545007e12f501113f22c980205d8fe4963d060f0b8d",
        )


if __name__ == "__main__":
    unittest.main()
