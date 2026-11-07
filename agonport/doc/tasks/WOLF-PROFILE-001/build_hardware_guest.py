"""Build ONE actual native full-game profiling guest; no target contact."""
from pathlib import Path
import argparse
import importlib.util
import json
import shutil
import subprocess

T = Path(__file__).resolve().parent
ROOT = T.parents[3]
spec = importlib.util.spec_from_file_location("profile_builder", ROOT / "src/asm/wolf3d/scripts/build.py")
b = importlib.util.module_from_spec(spec)
spec.loader.exec_module(b)


def once(text, old, new):
    assert text.count(old) == 1, old
    return text.replace(old, new)


def main(revision="hardware-guest01"):
    assert revision in ("hardware-guest01", "hardware-guest02")
    out = T / "build" / revision
    src = out / "source"
    assert not out.exists(), "Preserve the frozen guest; select a new revision"
    shutil.copytree(b.SOURCE, src)
    module = ROOT / "agonport/doc/tasks/WOLF-PERF-021/results/build01/candidate/module/wolf_perf.vdpl"
    assert b.sha256(module) in b.PROFILE_NATIVE_MODULES
    b.select_backend(src / "wolf3d_backend.inc", "vdplet-direct")
    b.select_profile(src / "wolf3d_backend.inc", True, True)
    b.select_package(src / "wolf3d_vdplet_package.inc", module.stat().st_size)
    p = src / "wolf3d.asm"
    s = p.read_text()
    s = once(s, "    call w3d_main_body\n", "    call wp_test\n")
    s = once(s, "    call w3d_poll_keys\n", "    call w3d_poll_keys\n    call wp_test_steer\n")
    s = once(s, "    W3D_PROFILE_CALL w3d_profile_finish\n", "    W3D_PROFILE_CALL w3d_profile_finish\n    call wp_test_result\n")
    s = once(s, "    W3D_PROFILE_CALL w3d_profile_game_open\n", "    W3D_PROFILE_CALL w3d_profile_game_open\n    ld de,wp_test_report+24\n    call wp_hw_stack\n")
    s = once(s, "    W3D_PROFILE_CALL w3d_profile_game_close\n", "    W3D_PROFILE_CALL w3d_profile_game_close\n    ld de,wp_test_report+28\n    call wp_hw_stack\n")
    s += '\nWPT_FULL_GAME: equ 1\nWPT_NATIVE_MOCK: equ 0\nWPT_FRAMES: equ 250\n    include "selftest.inc"\n'
    s += '''
; Existing INFO17 framing, queried only at the two selected idle boundaries.
wp_hw_stack:
    ld (wp_hw_destination),de
    ld a,(w3d_callback_error)
    or a
    ret nz
    ld a,(w3d_vdplet_transaction_pending)
    or a
    ret nz
    ld a,W3D_VDPL_REPLY_VALUE
    ld hl,wp_hw_stack_token
    call w3d_vdplet_arm_request
    jp c,wp_protocol_failed
    ld hl,wp_hw_stack_packet
    ld bc,wp_hw_stack_packet_end-wp_hw_stack_packet
    rst.lil 18h
    call w3d_vdplet_wait_reply
    jp c,wp_protocol_failed
    ld de,(wp_hw_destination)
    ld a,l
    ld (de),a
    inc de
    ld a,h
    ld (de),a
    inc de
    xor a
    ld (de),a
    inc de
    ld (de),a
    ld de,512
    or a
    sbc hl,de
    jp c,wp_protocol_failed
    ret
wp_hw_stack_packet:
    db 23,0,W3D_VDPL_SELECTOR
    dw 8
    db W3D_VDPL_PROTOCOL,W3D_VDPL_OP_INFO
wp_hw_stack_token: dw 0
    db 1,0
    dw 17
wp_hw_stack_packet_end:
wp_hw_destination: dl 0
'''
    p.write_text(s)
    shutil.copyfile(T / "selftest.inc", src / "selftest.inc")
    with (out / "assemble.log").open("w") as log:
        subprocess.run([str(b.resolve_assembler(None)), "wolf3d.asm", "profile.bin", "-l", "-c"], cwd=src,
                       stdout=log, stderr=subprocess.STDOUT, check=True, timeout=120)
    binary = src / "profile.bin"
    listing = src / "wolf3d.lst"
    assert 0x40000 + binary.stat().st_size < 0xa0000
    receipt = {"guest": str(binary), "guest_bytes": binary.stat().st_size,
               "guest_sha256": b.sha256(binary), "listing": str(listing),
               "listing_sha256": b.sha256(listing), "module": str(module),
               "module_sha256": b.sha256(module), "package_bytes": module.stat().st_size,
               "package_limit": 0x20000, "frames": 250,
               "native_mock": False, "extra_cue_hold": False, "info17": 2, "info_operation": 4,
               "inputs": {str(p.resolve()): b.sha256(p) for p in src.iterdir() if p.suffix in (".inc", ".asm")}}
    (out / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({k: v for k, v in receipt.items() if k != "inputs"}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--revision', default='hardware-guest01')
    main(parser.parse_args().revision)
