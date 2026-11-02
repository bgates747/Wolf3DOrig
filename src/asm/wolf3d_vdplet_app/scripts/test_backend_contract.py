#!/usr/bin/env python3
"""Structural invariants for the production game/VDPlet adapter."""

from pathlib import Path
import unittest


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
SOURCE = REPO / "src/asm/wolf3d/src"


class BackendContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.backend = (SOURCE / "wolf3d_vdplet_backend.inc").read_text()
        cls.client = (SOURCE / "wolf3d_vdplet_client.inc").read_text()
        cls.main = (SOURCE / "wolf3d.asm").read_text()
        cls.selector = (SOURCE / "wolf3d_backend.inc").read_text()
        cls.death = (SOURCE / "wolf3d_death.inc").read_text()
        cls.packager = (HERE / "prepare_package.py").read_text()
        cls.profiler = (HERE / "prepare_profile.py").read_text()
        cls.observer_stage = (HERE / "stage_observer_oryx.py").read_text()
        cls.observer_readiness = (
            HERE / "prepare_observer_readiness.py"
        ).read_text()

    def test_standalone_remains_tracked_default(self) -> None:
        self.assertIn(
            "W3D_RENDER_BACKEND:            equ W3D_RENDER_BACKEND_STANDALONE",
            self.selector,
        )

    def test_callback_brackets_runtime_lifetime(self) -> None:
        startup = self.main.index("call w3d_install_render_callback")
        runtime_open = self.main.index("call w3d_vdplet_backend_open")
        runtime_close = self.main.index("call w3d_vdplet_backend_close")
        callback_remove = self.main.rindex("call w3d_remove_render_callback")
        self.assertLess(startup, runtime_open)
        self.assertLess(runtime_close, callback_remove)

    def test_physical_startup_failure_preserves_stage_and_status(self) -> None:
        self.assertIn("W3D_VDPLET_STAGE_DISCOVER", self.client)
        self.assertIn("W3D_VDPLET_STAGE_LOAD_MODULE", self.client)
        self.assertIn("W3D_VDPLET_STAGE_RENDER", self.client)
        self.assertIn("w3d_vdplet_select_failure_message", self.backend)
        self.assertIn("stage=", self.backend)
        self.assertIn("status=", self.backend)
        self.assertIn("value=", self.backend)
        self.assertIn("callback=", self.backend)

    def test_workspace_streams_one_reused_zero_page(self) -> None:
        self.assertIn("w3d_vdplet_create_zero_buffer:", self.client)
        self.assertIn("ld hl,W3D_VDPLET_PACKAGE_ADDRESS", self.client)
        self.assertIn("ld bc,(w3d_vdplet_upload_chunk)", self.client)
        self.assertIn("@zero_finish_id:\n    dw 0\n    db 14", self.client)
        self.assertNotIn("ds W3P_WORKSPACE_BYTES", self.client)

    def test_run_arms_owner_before_send_and_consumes_snapshot_after(self) -> None:
        body = self.backend.split("w3d_vdplet_submit_dirty_world_render:", 1)[1]
        self.assertLess(body.index("call w3d_mark_render_submitted"),
                        body.index("call w3d_vdplet_send_run"))
        self.assertLess(body.index("call w3d_vdplet_send_run"),
                        body.index("call w3d_vdplet_batch_mark_submitted"))

    def test_done_commits_before_presentation(self) -> None:
        body = self.backend.split("w3d_vdplet_consume_render_completion:", 1)[1]
        self.assertLess(body.index("call w3d_vdplet_batch_accept_success"),
                        body.index("jp w3d_publish_render_completion"))

    def test_native_error_preserves_exact_retry_without_presentation(self) -> None:
        body = self.backend.split("@failed:", 1)[1].split("@fatal:", 1)[0]
        self.assertIn("call w3d_vdplet_batch_accept_failure", body)
        self.assertIn("ld (w3d_next_render_purpose),a", body)
        self.assertIn("ld (w3d_world_dirty),a", body)
        self.assertNotIn("w3d_vdu_present", body)

    def test_fizzle_deferral_is_explicit_and_finite(self) -> None:
        body = self.death.split("w3d_death_begin_fizzle:", 1)[1]
        self.assertIn("Production module release 1 deliberately reports fizzle unsupported", body)
        self.assertIn("ld a,W3D_DEATH_PHASE_HOLD", body)

    def test_package_rebuilds_standard_level_states(self) -> None:
        self.assertIn('ASSET_SCRIPTS / "build_level_packages.py"', self.packager)
        self.assertNotIn('"--diagnostic-e1l1-elevator-start"', self.packager)

    def test_profile_verifies_old_identity_before_replacement(self) -> None:
        self.assertIn("def retire_verified_profile_identity", self.profiler)
        self.assertLess(
            self.profiler.index("retire_verified_profile_identity(profile)"),
            self.profiler.index("canonical = load_canonical()"),
        )
        body = self.profiler.split("def retire_verified_profile_identity", 1)[1]
        self.assertLess(body.index("verify(profile / name, expected)"),
                        body.index("launcher.unlink()"))

    def test_observer_uses_separate_profile_and_exact_frontend(self) -> None:
        self.assertIn("wolf3d-vdplet-app-observed-r01", self.observer_stage)
        self.assertIn(
            "7e7d0e1bc89af72bde7ffbd6c06446aaefda4d1803f89eb1faf3167307ee1e01",
            self.observer_stage,
        )
        self.assertIn("--observer-output", self.observer_stage)
        self.assertIn("FLEXE_UART_OBSERVER_OUTPUT", self.profiler)
        self.assertIn(
            "observer output requires a separate diagnostic profile",
            self.profiler,
        )

    def test_observer_stage_never_launches_emulator(self) -> None:
        self.assertNotIn("./flexe-agon-emulator", self.observer_stage)
        self.assertNotIn("subprocess.Popen", self.observer_stage)
        self.assertIn("never run it", self.observer_stage)

    def test_observer_readiness_is_offline_and_freezes_transport_policy(self) -> None:
        self.assertNotIn('"ssh"', self.observer_readiness)
        self.assertIn('"oryx_contacted": False', self.observer_readiness)
        self.assertIn('"emulator_run": False', self.observer_readiness)
        self.assertIn('"stall_ms": 50_000', self.observer_readiness)
        self.assertIn('"sample_offsets_ms": [0, 250, 500]', self.observer_readiness)
        self.assertIn(
            "no timeout, chunk-size, pacing, firmware, backend, payload or consumer change",
            self.observer_readiness,
        )


if __name__ == "__main__":
    unittest.main()
