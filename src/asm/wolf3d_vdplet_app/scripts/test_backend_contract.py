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
        cls.start_selector = (SOURCE / "wolf3d_start.inc").read_text()
        cls.death = (SOURCE / "wolf3d_death.inc").read_text()
        cls.intermission = (SOURCE / "wolf3d_intermission.inc").read_text()
        cls.level_loader = (SOURCE / "wolf3d_level_loader.inc").read_text()
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
        self.assertIn(
            "W3D_DIAGNOSTIC_INVULNERABLE:   equ 0",
            self.selector,
        )

    def test_production_start_floor_remains_tracked_default(self) -> None:
        self.assertIn("W3D_INITIAL_LEVEL: equ 0", self.start_selector)
        self.assertIn("ld a,W3D_INITIAL_LEVEL", self.main)
        self.assertIn(".if W3D_INITIAL_LEVEL", self.main)
        self.assertIn("xor a", self.main)

    def test_callback_brackets_runtime_lifetime(self) -> None:
        startup = self.main.index("call w3d_install_render_callback")
        runtime_open = self.main.index("call w3d_vdplet_backend_open")
        runtime_close = self.main.index("call w3d_vdplet_backend_close")
        callback_remove = self.main.rindex("call w3d_remove_render_callback")
        self.assertLess(startup, runtime_open)
        self.assertLess(runtime_close, callback_remove)

    def test_application_lifetime_display_is_acquired_before_assets(self) -> None:
        main = self.main.index("\nmain:\n")
        display = self.main.index("call w3d_enter_gameplay_display", main)
        audio = self.main.index("call w3d_audio_initialize", display)
        body = self.main.index("call w3d_main_body", audio)
        self.assertLess(display, audio)
        self.assertLess(audio, body)
        enter = self.main.split("w3d_enter_gameplay_display:", 1)[1]
        enter = enter.split("w3d_display_acquired:", 1)[0]
        arm = enter.index("call w3d_arm_gameplay_mode_fence")
        send = enter.index("rst.lil 18h")
        fence = enter.index("call w3d_wait_for_gameplay_mode")
        self.assertLess(arm, send)
        self.assertLess(send, fence)
        self.assertIn("w3d_display_mode_command", enter)
        self.assertIn("w3d_display_post_mode_setup", enter)
        self.assertIn("MOSCALL mos_clearvdpflags", self.main)
        self.assertIn("MOSCALL mos_waitforvdpflags", self.main)
        self.assertIn("W3D_MODE_FENCE_WAIT_PASSES:     equ 10", self.main)
        fence_body = self.main.split("w3d_wait_for_gameplay_mode:", 1)[1]
        fence_body = fence_body.split("w3d_mode_fence_error_msg:", 1)[0]
        self.assertIn("ld c,vdp_pflag_mode", fence_body)
        self.assertIn("djnz @wait", fence_body)
        self.assertIn("jp c,@restore_screen", self.main)

    def test_exit_mode_restore_is_fenced_before_returning_to_mos(self) -> None:
        restore = self.main.split("w3d_restore_original_screen_mode:", 1)[1]
        restore = restore.split("w3d_restore_mode_command:", 1)[0]
        arm = restore.index("call w3d_arm_gameplay_mode_fence")
        send = restore.index("rst.lil 18h")
        wait = restore.index("call w3d_wait_for_gameplay_mode")
        self.assertLess(arm, send)
        self.assertLess(send, wait)

    def test_floor_transition_reuses_acquired_display_before_vdplet_reset(self) -> None:
        loader = (SOURCE / "wolf3d_level_loader.inc").read_text()
        ingress = loader.index("call w3d_audio_wait_for_vdp_ingress")
        display = loader.index("call w3d_enter_gameplay_display", ingress)
        seed = loader.index("call w3d_seed_level_transition_state", display)
        reset = loader.index("call w3d_submit_level_reset", seed)
        self.assertLess(ingress, display)
        self.assertLess(display, seed)
        self.assertLess(seed, reset)
        guarded = loader[ingress:seed]
        self.assertNotIn("w3d_display_mode_command", guarded)
        self.assertNotIn("w3d_arm_gameplay_mode_fence", guarded)
        self.assertIn("ret c", guarded)

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
        render = self.backend.split(
            "w3d_vdplet_consume_render_completion:", 1
        )[1]
        body = render.split("@failed:", 1)[1].split("@fatal:", 1)[0]
        self.assertIn("W3D_VDPLET_RENDER_RETRY_LIMIT: equ 1", self.backend)
        self.assertIn("cp W3D_VDPLET_RENDER_RETRY_LIMIT", body)
        self.assertIn("jr nc,@fatal", body)
        self.assertIn("call w3d_vdplet_batch_accept_failure", body)
        self.assertIn("ld (w3d_next_render_purpose),a", body)
        self.assertIn("ld (w3d_world_dirty),a", body)
        self.assertNotIn("w3d_vdu_present", body)

    def test_success_rearms_bounded_native_retry(self) -> None:
        body = self.backend.split(
            "w3d_vdplet_consume_render_completion:", 1
        )[1].split("@failed:", 1)[0]
        self.assertIn("ld (w3d_vdplet_render_retry_count),a", body)

    def test_audio_command_install_is_ordered_and_finite(self) -> None:
        audio = (SOURCE / "wolf3d_audio.inc").read_text()
        install = audio.split(
            "w3d_audio_install_available_command_buffers:", 1
        )[1].split("w3d_audio_install_command_buffer:", 1)[0]
        fence = audio.split("w3d_audio_wait_for_vdp_ingress:", 1)[1].split(
            "w3d_audio_install_command_buffer:", 1
        )[0]
        self.assertGreaterEqual(
            install.count("call w3d_audio_wait_for_vdp_ingress"), 2
        )
        self.assertIn("MOSCALL W3D_AUDIO_MOS_CLEARVDPFLAGS", fence)
        self.assertIn("db 23,0,086h", fence)
        self.assertIn("MOSCALL W3D_AUDIO_MOS_WAITFORVDPFLAGS", fence)
        self.assertIn("jr nz,@timeout", fence)
        self.assertIn("jp w3d_gameplay_fatal_before_runtime", self.main)

    def test_transition_images_share_the_ordered_ingress_fence(self) -> None:
        setup = self.main.index("ld hl,w3d_audio_wait_for_vdp_ingress")
        install = self.main.index(
            "call w3d_intermission_set_ingress_fence_hook", setup
        )
        self.assertLess(setup, install)
        tick = self.intermission.split("w3d_intermission_loading_tick:", 1)[1]
        tick = tick.split("w3d_intermission_finish:", 1)[0]
        self.assertIn("call w3d_intermission_run_ingress_fence", tick)
        self.assertIn("ld a,W3D_INTERMISSION_RESULT_INGRESS", tick)
        self.assertIn("ld (w3d_intermission_ingress_failed),a", tick)
        transition = self.level_loader.split("w3d_transition_to_next_level:", 1)[1]
        transition = transition.split("w3d_level_state_filename_table:", 1)[0]
        self.assertGreaterEqual(
            transition.count("ld hl,w3d_intermission_loading_tick"), 2
        )
        self.assertIn("jp c,@asset_failed", transition)
        self.assertIn("jr c,@asset_failed", transition)

    def test_fizzle_is_app_paced_finite_and_surface_synchronized(self) -> None:
        body = self.death.split("w3d_death_begin_fizzle:", 1)[1]
        self.assertIn("ld a,W3P_FIZZLE_DISPLAY_FRAMES", body)
        self.assertIn("ld a,W3D_DEATH_PHASE_WAIT_FIZZLE", body)
        self.assertIn("jp w3d_death_pump_vdplet_fizzle", body)
        pump = self.death.split("w3d_death_pump_vdplet_fizzle:", 1)[1]
        pump = pump.split("w3d_death_accept_render_purpose:", 1)[0]
        self.assertIn("ld a,(w3d_exit_requested)", pump)
        self.assertIn("call w3d_vdplet_submit_fizzle_begin", pump)
        self.assertIn("call w3d_vdplet_submit_fizzle_display", pump)
        self.assertIn("call w3d_vdplet_submit_fizzle_sync", pump)
        consume = self.backend.split(
            "w3d_vdplet_consume_fizzle_completion:", 1
        )[1].split("w3d_vdplet_submit_dirty_world_render:", 1)[0]
        self.assertIn("cp W3D_VDPLET_FIZZLE_OP_DISPLAY", consume)
        self.assertEqual(consume.count("call z,w3d_vdu_present"), 1)
        self.assertIn("call w3d_death_accept_vdplet_fizzle_completion", consume)
        self.assertIn("W3D_VDPLET_STAGE_FIZZLE", self.client)

    def test_package_rebuilds_standard_level_states(self) -> None:
        self.assertIn('ASSET_SCRIPTS / "build_level_packages.py"', self.packager)
        self.assertNotIn('"--diagnostic-e1l1-elevator-start"', self.packager)
        self.assertIn('GENERATED / "shell/end.agnb"', self.packager)

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
