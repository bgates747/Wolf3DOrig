#!/usr/bin/env python3
"""Proportional host regressions for the Wolf production VDPlet client.

These tests do not emulate eZ80 instructions.  They pin the assembled wire
templates and exercise a deliberately small model of the ownership/mailbox
rules that the assembly implements.  The finite Oryx fixture remains the
target-level proof.
"""

from __future__ import annotations

from dataclasses import dataclass
import importlib.util
from pathlib import Path
import unittest


HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent
REPO = HERE.parents[3]
CLIENT_BINARY = PROJECT / "tgt/client.bin"
CLIENT_SOURCE = REPO / "src/asm/wolf3d/src/wolf3d_vdplet_client.inc"
FIXTURE_SOURCE = PROJECT / "src/client_regression.asm"
REHEARSE_SOURCE = HERE / "rehearse.py"

VDPL = b"VDPL"
PROTOCOL = 1
IDENT = 1
LOADED = 2
DONE = 3
VALUE = 4
ERROR = 5
COPIED_PIXEL_CAPS = 0x0011


def reply(kind: int, token: int, value: int = 0, *, protocol: int = PROTOCOL) -> bytes:
    return VDPL + bytes((protocol, kind)) + token.to_bytes(2, "little") + value.to_bytes(2, "little")


@dataclass
class ClientModel:
    """Minimal ownership model matching the assembly's conservative rules."""

    token: int = 0
    expected_kind: int = 0
    pending: bool = False
    handle: int = 0
    status: str = "ok"
    native_error: int = 0
    callback_alive: bool = True
    buffers_alive: bool = True
    exit_requested: bool = False

    def discover(self, capabilities: int | None) -> bool:
        if capabilities is None:
            self.pending = True
            self.expected_kind = IDENT
            self.status = "timeout"
            return False
        if capabilities & COPIED_PIXEL_CAPS != COPIED_PIXEL_CAPS:
            self.status = "incompatible"
            return False
        return True

    def arm(self, kind: int) -> int:
        if self.pending:
            self.status = "protocol"
            raise RuntimeError("transaction already pending")
        if self.token == 0xFFFF:
            self.status = "token"
            raise RuntimeError("token space exhausted")
        self.token += 1
        self.expected_kind = kind
        self.pending = True
        return self.token

    def accept(self, packet: bytes) -> str:
        if len(packet) != 10 or packet[:4] != VDPL or packet[4] != PROTOCOL:
            self.status = "protocol"
            return "malformed"
        kind = packet[5]
        token = int.from_bytes(packet[6:8], "little")
        value = int.from_bytes(packet[8:10], "little")
        if token != self.token:
            return "stale"
        self.pending = False
        if kind == ERROR:
            self.status = "runtime"
            self.native_error = value
            return "error"
        if kind != self.expected_kind:
            self.status = "protocol"
            return "wrong-kind"
        self.status = "ok"
        if kind == LOADED:
            if value == 0:
                self.status = "protocol"
                return "zero-handle"
            self.handle = value
        elif value != 0:
            self.status = "runtime"
            return "nonzero-done"
        return "success"

    def timeout(self) -> None:
        self.status = "timeout"
        # Timeout is detection, not cancellation.  Ownership remains live.

    def request_exit(self) -> None:
        self.exit_requested = True

    def may_schedule_run(self) -> bool:
        return not self.exit_requested and not self.pending and self.handle != 0

    def unload_error_slot(self, slot: int, native_error: int) -> str:
        self.status = "runtime"
        self.native_error = native_error
        if slot == 0:
            self.handle = 0
            return "released-with-error"
        if slot == self.handle:
            return "still-installed"
        self.status = "protocol"
        return "ownership-ambiguous"

    def cleanup(self) -> bool:
        if self.pending or self.handle:
            return False
        self.buffers_alive = False
        self.callback_alive = False
        return True


class AssembledWireTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not CLIENT_BINARY.is_file():
            raise AssertionError(
                "build the fixture first with scripts/build.py"
            )
        cls.binary = CLIENT_BINARY.read_bytes()
        cls.source = CLIENT_SOURCE.read_text()
        cls.fixture_source = FIXTURE_SOURCE.read_text()

    def assert_unique_template(self, payload: bytes) -> None:
        self.assertEqual(self.binary.count(payload), 1, payload.hex(" "))

    def test_operand_free_discovery_is_exact(self) -> None:
        self.assert_unique_template(bytes((23, 0, 0xD9)))

    def test_framed_templates_have_frozen_full_lengths(self) -> None:
        info0 = bytes((23, 0, 0xD8, 8, 0, 1, 4, 0, 0, 1, 0, 0, 0))
        load = bytes((23, 0, 0xD8, 14, 0, 1, 1, 0, 0, 1, 0, 0x77, 0xEA))
        run = bytes((23, 0, 0xD8, 12, 0, 1, 2, 0, 0, 1, 0))
        unload = bytes((23, 0, 0xD8, 8, 0, 1, 3, 0, 0, 1, 0))
        self.assertIn(info0, self.binary)
        self.assertIn(load, self.binary)
        self.assertIn(run, self.binary)
        self.assertIn(unload, self.binary)
        self.assertEqual((len(info0), 19, 17, 13), (13, 19, 17, 13))

    def test_upload_uses_stock_clear_write_and_consolidate(self) -> None:
        self.assertIn(bytes((23, 0, 0xA0, 0, 0, 2)), self.binary)
        self.assertIn(bytes((23, 0, 0xA0, 0, 0, 0, 0, 0)), self.binary)
        self.assertIn(bytes((23, 0, 0xA0, 0, 0, 14)), self.binary)

    def test_large_zero_buffer_reuses_one_package_staging_page(self) -> None:
        expected = """\
w3d_vdplet_create_zero_buffer:
    ld a,c
    ld (@zero_clear_id+0),a"""
        self.assertIn(expected, self.source)
        self.assertIn("ld hl,W3D_VDPLET_PACKAGE_ADDRESS\n"
                      "    ld bc,(w3d_vdplet_upload_chunk)\n"
                      "    rst.lil 18h", self.source)
        self.assertIn("@zero_finish_id:\n    dw 0\n    db 14", self.source)

    def test_source_pins_direct_row_capability_subset(self) -> None:
        self.assertIn("W3D_VDPLET_REQUIRED_CAPS:      equ 0101h", self.source)
        self.assertIn("and e", self.source)
        self.assertIn("and d", self.source)

    def test_u16_reply_is_zero_extended_before_adl_comparison(self) -> None:
        expected = """\
    ld hl,0
    ld a,(w3d_vdplet_snapshot+8)
    ld (w3d_vdplet_last_value+0),a
    ld l,a"""
        self.assertIn(expected, self.source)

    def test_success_return_zero_extends_mos_status(self) -> None:
        expected = """\
    ld a,(fixture_result_code)
; MOS receives a 24-bit HL return status in ADL mode. Zero HLU as well as H so
; a successful result cannot inherit a false error from mos_save.
    ld hl,0
    ld l,a"""
        self.assertIn(expected, self.fixture_source)

    def test_unload_patches_original_high_byte_before_zero_test(self) -> None:
        expected = """\
    ld a,(w3d_vdplet_handle+1)
    ld (@handle+1),a
    or b
    ret z"""
        self.assertIn(expected, self.source)

    def test_close_reasserts_failure_carry_for_retained_handle(self) -> None:
        expected = """\
    ld a,(w3d_vdplet_handle+1)
    or b
    jr z,@clear_released_error
; A live handle means storage and callback ownership remain unresolved. The
; bytewise nonzero test cleared carry, so explicitly restore the failure flag.
    scf
    ret
@clear_released_error:"""
        self.assertIn(expected, self.source)

    def test_fixture_routes_retained_handle_to_ambiguity_hold(self) -> None:
        expected = """\
    ld a,(w3d_vdplet_handle+1)
    or b
    jr nz,fixture_ambiguous"""
        self.assertIn(expected, self.fixture_source)


class MailboxAndOwnershipTests(unittest.TestCase):
    def test_unavailable_runtime_preserves_pending_ownership(self) -> None:
        client = ClientModel()
        self.assertFalse(client.discover(None))
        self.assertTrue(client.pending)
        self.assertFalse(client.cleanup())
        self.assertTrue(client.callback_alive)
        self.assertTrue(client.buffers_alive)

    def test_capability_superset_passes_and_missing_bit_fails(self) -> None:
        self.assertTrue(ClientModel().discover(0xFFFF))
        missing_pixels = ClientModel()
        self.assertFalse(missing_pixels.discover(0x0001))
        self.assertEqual(missing_pixels.status, "incompatible")

    def test_load_rejection_never_publishes_handle(self) -> None:
        client = ClientModel()
        token = client.arm(LOADED)
        self.assertEqual(client.accept(reply(ERROR, token, 7)), "error")
        self.assertEqual(client.handle, 0)
        self.assertFalse(client.pending)

    def test_only_fresh_nonzero_loaded_reply_publishes_handle(self) -> None:
        client = ClientModel()
        token = client.arm(LOADED)
        self.assertEqual(client.accept(reply(LOADED, token, 0x2345)), "success")
        self.assertEqual(client.handle, 0x2345)
        self.assertFalse(client.pending)

    def test_unrelated_key_and_stale_token_do_not_complete_run(self) -> None:
        client = ClientModel(handle=0x1234)
        token = client.arm(DONE)
        ordinary_key = b"w"
        self.assertNotEqual(ordinary_key[:4], VDPL)
        self.assertEqual(client.accept(reply(DONE, token - 1)), "stale")
        self.assertTrue(client.pending)
        self.assertEqual(client.accept(reply(DONE, token)), "success")

    def test_malformed_reply_is_not_cleanup_authority(self) -> None:
        client = ClientModel(handle=0x1234)
        client.arm(DONE)
        malformed = reply(DONE, client.token, protocol=2)
        self.assertEqual(client.accept(malformed), "malformed")
        self.assertTrue(client.pending)
        self.assertFalse(client.cleanup())

    def test_native_run_error_completes_matching_transaction(self) -> None:
        client = ClientModel(handle=0x1234)
        token = client.arm(DONE)
        self.assertEqual(client.accept(reply(ERROR, token, 8)), "error")
        self.assertFalse(client.pending)
        self.assertEqual((client.status, client.native_error), ("runtime", 8))

    def test_timeout_does_not_cancel_or_release_storage(self) -> None:
        client = ClientModel(handle=0x1234)
        client.arm(DONE)
        client.timeout()
        self.assertTrue(client.pending)
        self.assertEqual(client.handle, 0x1234)
        self.assertFalse(client.cleanup())

    def test_escape_drains_run_before_unload_and_cleanup(self) -> None:
        client = ClientModel(handle=0x1234)
        token = client.arm(DONE)
        client.request_exit()
        self.assertFalse(client.may_schedule_run())
        self.assertFalse(client.cleanup())
        self.assertEqual(client.accept(reply(DONE, token)), "success")
        unload = client.arm(DONE)
        self.assertEqual(client.accept(reply(DONE, unload)), "success")
        client.handle = 0  # successful requested UNLOAD proves release
        self.assertTrue(client.cleanup())

    def test_unload_error_uses_info2_to_establish_release(self) -> None:
        released = ClientModel(handle=0x1234)
        self.assertEqual(released.unload_error_slot(0, 9), "released-with-error")
        self.assertEqual(released.handle, 0)
        self.assertTrue(released.cleanup())

        retained = ClientModel(handle=0x1234)
        self.assertEqual(retained.unload_error_slot(0x1234, 9), "still-installed")
        self.assertEqual(retained.handle, 0x1234)
        self.assertFalse(retained.cleanup())

        foreign = ClientModel(handle=0x1234)
        self.assertEqual(foreign.unload_error_slot(0x5678, 9), "ownership-ambiguous")
        self.assertEqual(foreign.handle, 0x1234)
        self.assertEqual(foreign.status, "protocol")
        self.assertFalse(foreign.cleanup())

    def test_clean_mos_return_requires_no_pending_or_owned_handle(self) -> None:
        client = ClientModel()
        self.assertTrue(client.cleanup())
        self.assertFalse(client.callback_alive)
        self.assertFalse(client.buffers_alive)

    def test_generation33_tuple_is_rejected_by_exact_verifier(self) -> None:
        spec = importlib.util.spec_from_file_location("wolf_client_rehearse", REHEARSE_SOURCE)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        observed = bytes.fromhex(
            "57 56 50 43 00 03 00 00 01 00 08 00 08 00 01 00"
        )
        with self.assertRaises(AssertionError):
            module.verify_result(observed)


if __name__ == "__main__":
    unittest.main()
