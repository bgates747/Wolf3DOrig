#!/usr/bin/env python3
"""Exercise production floor routing and Episode 1 victory in Fab Agon."""

from __future__ import annotations

import argparse
import atexit
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time


_root_override = os.environ.get("W3D_STAGED_ROOT")
_installed_root = Path(__file__).resolve().parents[4]
STAGED_ROOT = Path(_root_override) if _root_override else _installed_root
RUNTIME_ROOT = Path(os.environ.get("W3D_RUNTIME_ROOT", _installed_root))
STAGED_SRC = STAGED_ROOT / "src/asm/wolf3d/src"
GENERATED = STAGED_ROOT / "agonport/assets/generated/wolf3d"
FAB = RUNTIME_ROOT / "agonport/emulator/fab-agon-emulator"
MOS = RUNTIME_ROOT / "agonport/emulator/mos_console8.bin"
VDP = RUNTIME_ROOT / "agonport/emulator/vdp_wolf3d.so"
RESULT_SIZE = 48

sys.path.insert(0, str(STAGED_ROOT / "agonport/tools/wolf3d_assets"))
from formats.level_package import parse_package  # noqa: E402


def run(command: list[str], *, cwd: Path | None = None) -> None:
    print("+", " ".join(command))
    subprocess.run(command, check=True, cwd=cwd)


def replace_once(source: str, old: str, new: str, description: str) -> str:
    count = source.count(old)
    if count != 1:
        raise RuntimeError(
            f"production {description} marker changed: expected once, found {count}"
        )
    return source.replace(old, new, 1)


def instrument(
    source: str, *, start_level: int, completion: str, difficulty: int
) -> str:
    source = replace_once(
        source,
        "mos_load:        equ 01h\n",
        "mos_load:        equ 01h\nmos_save:        equ 02h\n",
        "MOS API",
    )

    # Keep production's application-level route, but replace the blocking
    # title/menu input with one deterministic NEW_GAME result. Victory must
    # still return through that route and reach its shell-resume call site.
    source = replace_once(
        source,
        "    call w3d_shell_run\n",
        f"    ld a,{difficulty}\n"
        "    ld (w3d_requested_difficulty),a\n"
        "    ld a,W3D_SHELL_RESULT_NEW_GAME\n",
        "initial shell",
    )
    source = replace_once(
        source,
        "    call w3d_shell_resume_after_victory\n",
        "    call w3d_transition_regression_shell_resume\n",
        "victory shell re-entry",
    )

    # Replace only the production begin call in the temporary copy with a
    # nonblocking recorder.  The loader instrumentation below substitutes the
    # matching loading-tick callbacks and finish call, preserving the complete
    # begin -> load -> finish lifecycle without waiting for keyboard input.
    source = replace_once(
        source,
        "    call w3d_intermission_begin\n"
        "    call w3d_transition_to_next_level\n",
        "    call w3d_transition_regression_intermission_begin\n"
        "    call w3d_transition_to_next_level\n",
        "intermission begin lifecycle",
    )

    startup_load = (
        "    ld a,(w3d_requested_difficulty)\n"
        "    ld b,a\n"
        "    xor a\n"
        "    call w3d_load_level_package\n"
    )
    source = replace_once(
        source,
        startup_load,
        "    ld a,(w3d_requested_difficulty)\n"
        "    ld b,a\n"
        f"    ld a,{start_level}\n"
        "    call w3d_load_level_package\n",
        "gameplay-session initial level",
    )

    # Force completion only after the production session has submitted its
    # initial full render. The foreground must consume that real callback
    # before either loading another floor or returning victory to the shell.
    initial_submit = (
        "    call w3d_submit_level_reset\n"
        "    jp c,w3d_gameplay_fatal_shutdown\n\n"
        "mainloop:\n"
    )
    source = replace_once(
        source,
        initial_submit,
        "    call w3d_submit_level_reset\n"
        "    jp c,w3d_gameplay_fatal_shutdown\n"
        "; Regression-only persistent and per-level sentinels.\n"
        "    ld a,73\n"
        "    ld (w3d_player_health),a\n"
        "    ld a,17\n"
        "    ld (w3d_player_ammo),a\n"
        "    ld a,2\n"
        "    ld (w3d_player_weapon),a\n"
        "    ld (w3d_player_best_weapon),a\n"
        "    ld (w3d_player_chosen_weapon),a\n"
        "    ld (w3d_player_lives),a\n"
        "    ld a,15\n"
        "    ld (w3d_player_key_flags),a\n"
        "    ld a,9\n"
        "    ld (w3d_player_treasure_count+0),a\n"
        "    xor a\n"
        "    ld (w3d_player_treasure_count+1),a\n"
        f"    ld a,W3D_LEVEL_COMPLETION_{completion.upper()}\n"
        "    ld (w3d_level_completion),a\n\n"
        "mainloop:\n",
        "initial reset submission",
    )

    # An ordinary transition records immediately after the destination reset
    # was accepted. Victory bypasses this call and records only after the
    # gameplay session returned W3D_GAMEPLAY_RESULT_VICTORY to the shell route.
    transition_call = (
        "    call w3d_transition_to_next_level\n"
        "    jr nc,@transition_ready\n"
        "    call w3d_shell_query_exit_request\n"
        "    jp nz,w3d_gameplay_exit_shutdown\n"
        "    jr @fatal_shutdown\n"
        "@transition_ready:\n"
        "    jp mainloop\n"
    )
    source = replace_once(
        source,
        transition_call,
        "    call w3d_transition_to_next_level\n"
        "    jr nc,@transition_ready\n"
        "    call w3d_shell_query_exit_request\n"
        "    jp nz,w3d_gameplay_exit_shutdown\n"
        "    jr @fatal_shutdown\n"
        "@transition_ready:\n"
        "    xor a\n"
        "    call w3d_transition_regression_write_result\n"
        "    jp mainloop\n",
        "ordinary transition",
    )

    source += r'''

; Added only to the temporary production-regression source.
w3d_transition_regression_shell_resume:
    ld hl,w3d_transition_regression_shell_resume_count
    inc (hl)
    ld a,W3D_GAMEPLAY_RESULT_VICTORY
    ld (w3d_gameplay_result),a
    ld a,1
    call w3d_transition_regression_write_result
; QUIT makes the production @route_shell_result return instead of entering a
; keyboard-driven menu. Reaching here already proves its victory re-entry seam.
    ld a,W3D_SHELL_RESULT_QUIT
    ret

w3d_transition_regression_count_package_load:
    push af
    push hl
    ld hl,w3d_transition_regression_package_load_count
    inc (hl)
; The second package load is the destination. Capture the lifecycle phase at
; its exact entry, then mark all subsequent ticks as destination-loading work.
    ld a,(hl)
    cp 2
    jr nz,@done
    ld a,(w3d_transition_regression_intermission_phase)
    ld (w3d_transition_regression_destination_package_phase),a
    cp 1
    jr nz,@mark_loading
    ld a,1
    ld (w3d_transition_regression_begin_before_package),a
@mark_loading:
    ld a,2
    ld (w3d_transition_regression_intermission_phase),a
@done:
    pop hl
    pop af
    ret

w3d_transition_regression_count_transition:
    ld hl,w3d_transition_regression_transition_count
    inc (hl)
    ret

w3d_transition_regression_count_tilemap_replace:
    ld hl,w3d_transition_regression_tilemap_replace_count
    inc (hl)
    ret

; Substitute for the production nonblocking begin in this headless lifecycle
; fixture. Capture the still-authoritative source floor and prove that the
; prior asynchronous producer has drained before UI ownership begins.
w3d_transition_regression_intermission_begin:
; Preserve the production mode-8 single-buffered side effect while skipping
; its drawing. This makes the later restoration exercise the real single ->
; double transition instead of redundantly setting an already-double mode.
    call w3d_shell_setup
    ld hl,w3d_transition_regression_intermission_count
    inc (hl)
    ld a,(w3d_transition_regression_intermission_phase)
    ld (w3d_transition_regression_begin_phase),a
    ld a,(w3d_transition_regression_package_load_count)
    ld (w3d_transition_regression_begin_package_count),a
    ld a,(w3d_level_requested_index)
    ld (w3d_transition_regression_intermission_source),a
    ld a,(w3d_level_completion)
    ld (w3d_transition_regression_intermission_completion),a
    ld a,(w3d_async_owner)
    ld (w3d_transition_regression_intermission_owner),a
    ld a,1
    ld (w3d_transition_regression_intermission_phase),a
    xor a
    ret

; Substitute for every explicit loading tick. The callback-specific wrapper
; below proves that AGNB finalized at least one destination image rather than
; merely observing the three explicit W3L/tilemap boundary ticks.
w3d_transition_regression_intermission_loading_tick:
    ld a,(w3d_transition_regression_intermission_phase)
    cp 2
    jr nz,@continue
    ld a,1
    ld (w3d_transition_regression_tick_during_load),a
@continue:
    xor a
    ret

w3d_transition_regression_intermission_image_callback:
    ld a,1
    ld (w3d_transition_regression_callback_tick_seen),a
    jp w3d_transition_regression_intermission_loading_tick

; Finish is deliberately immediate in the headless fixture. Snapshot both
; destination loading milestones, then advance the phase so display-restore
; instrumentation can prove this seam was crossed first.
w3d_transition_regression_intermission_finish:
    ld hl,w3d_transition_regression_finish_count
    inc (hl)
    ld a,(w3d_transition_regression_package_load_count)
    cp 2
    jr nz,@not_ready
    ld a,(w3d_transition_regression_tilemap_replace_count)
    cp 2
    jr nz,@not_ready
    ld a,1
    ld (w3d_transition_regression_finish_ready),a
@not_ready:
    ld a,(w3d_async_owner)
    ld (w3d_transition_regression_finish_owner),a
    ld a,3
    ld (w3d_transition_regression_intermission_phase),a
    xor a
    ret

w3d_transition_regression_count_display_setup:
    ld hl,w3d_transition_regression_display_setup_count
    inc (hl)
    ld a,(w3d_transition_regression_intermission_phase)
    ld (w3d_transition_regression_display_phase),a
    ld a,(w3d_transition_regression_finish_count)
    ld (w3d_transition_regression_display_finish_count),a
    ld a,1
    ld (w3d_transition_regression_display_setup_ready),a
    ret

; Called at the exact production destination-reset submission seam. A value of
; one proves mode 8+128 was restored before the renderer acquired ownership;
; owner zero proves no stale render/fizzle overlapped that restoration.
w3d_transition_regression_capture_pre_reset:
    ld a,(w3d_transition_regression_display_setup_ready)
    ld (w3d_transition_regression_display_ready_before_reset),a
    ld a,(w3d_async_owner)
    ld (w3d_transition_regression_display_owner_before_reset),a
    ret

; A=result kind: 0 successful destination reset, 1 victory/shell return.
w3d_transition_regression_write_result:
    ld (w3d_transition_regression_result+25),a
    ld a,(w3d_level_requested_index)
    ld (w3d_transition_regression_result+4),a
    ld a,(w3d_game_difficulty)
    ld (w3d_transition_regression_result+5),a
    ld a,(w3d_level_door_count)
    ld (w3d_transition_regression_result+6),a
    ld a,(w3d_level_actor_count)
    ld (w3d_transition_regression_result+7),a
    ld a,(w3d_level_static_count+0)
    ld (w3d_transition_regression_result+8),a
    ld a,(w3d_level_static_count+1)
    ld (w3d_transition_regression_result+9),a
    ld a,(w3d_player_health)
    ld (w3d_transition_regression_result+10),a
    ld a,(w3d_player_ammo)
    ld (w3d_transition_regression_result+11),a
    ld a,(w3d_player_weapon)
    ld (w3d_transition_regression_result+12),a
    ld a,(w3d_player_lives)
    ld (w3d_transition_regression_result+13),a
    ld a,(w3d_player_key_flags)
    ld (w3d_transition_regression_result+14),a
    ld a,(w3d_level_completion)
    ld (w3d_transition_regression_result+15),a
    ld a,(w3d_player_treasure_count+0)
    ld (w3d_transition_regression_result+16),a
    ld a,(w3d_player_treasure_count+1)
    ld (w3d_transition_regression_result+17),a
    ld a,(w3d_player_pose+2)
    ld (w3d_transition_regression_result+18),a
    ld a,(w3d_player_pose+6)
    ld (w3d_transition_regression_result+19),a
    ld a,(w3d_async_owner)
    ld (w3d_transition_regression_result+20),a
    ld a,(w3d_gameplay_result)
    ld (w3d_transition_regression_result+21),a
    ld a,(w3d_transition_regression_shell_resume_count)
    ld (w3d_transition_regression_result+22),a
    ld a,(w3d_transition_regression_package_load_count)
    ld (w3d_transition_regression_result+23),a
    ld a,(w3d_transition_regression_transition_count)
    ld (w3d_transition_regression_result+24),a
    ld a,(w3d_callback_error)
    ld (w3d_transition_regression_result+26),a
    ld a,(w3d_exit_requested)
    ld (w3d_transition_regression_result+27),a
    ld a,(w3d_transition_regression_tilemap_replace_count)
    ld (w3d_transition_regression_result+28),a
    ld a,(w3d_transition_regression_intermission_count)
    ld (w3d_transition_regression_result+29),a
    ld a,(w3d_transition_regression_intermission_source)
    ld (w3d_transition_regression_result+30),a
    ld a,(w3d_transition_regression_intermission_completion)
    ld (w3d_transition_regression_result+31),a
    ld a,(w3d_transition_regression_intermission_owner)
    ld (w3d_transition_regression_result+32),a
    ld a,(w3d_transition_regression_display_setup_count)
    ld (w3d_transition_regression_result+33),a
    ld a,(w3d_transition_regression_display_ready_before_reset)
    ld (w3d_transition_regression_result+34),a
    ld a,(w3d_transition_regression_display_owner_before_reset)
    ld (w3d_transition_regression_result+35),a
    ld a,(w3d_transition_regression_begin_package_count)
    ld (w3d_transition_regression_result+36),a
    ld a,(w3d_transition_regression_begin_phase)
    ld (w3d_transition_regression_result+37),a
    ld a,(w3d_transition_regression_destination_package_phase)
    ld (w3d_transition_regression_result+38),a
    ld a,(w3d_transition_regression_tick_during_load)
    ld (w3d_transition_regression_result+39),a
    ld a,(w3d_transition_regression_callback_tick_seen)
    ld (w3d_transition_regression_result+40),a
    ld a,(w3d_transition_regression_finish_count)
    ld (w3d_transition_regression_result+41),a
    ld a,(w3d_transition_regression_finish_ready)
    ld (w3d_transition_regression_result+42),a
    ld a,(w3d_transition_regression_finish_owner)
    ld (w3d_transition_regression_result+43),a
    ld a,(w3d_transition_regression_display_phase)
    ld (w3d_transition_regression_result+44),a
    ld a,(w3d_transition_regression_display_finish_count)
    ld (w3d_transition_regression_result+45),a
    ld a,(w3d_transition_regression_begin_before_package)
    ld (w3d_transition_regression_result+46),a
    ld hl,w3d_transition_regression_filename
    ld de,w3d_transition_regression_result
    ld bc,48
    MOSCALL mos_save
    ret

w3d_transition_regression_filename:
    db "transition_result.bin",0
w3d_transition_regression_result:
    db "W3T4"
    db 0,0,0,0,0,0,0,0,0,0,0,0,0,0
    db 0,0,0,0,0,0,0,0,0,0,0,0,0,0
    db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
w3d_transition_regression_shell_resume_count: db 0
w3d_transition_regression_package_load_count: db 0
w3d_transition_regression_transition_count: db 0
w3d_transition_regression_tilemap_replace_count: db 0
w3d_transition_regression_intermission_count: db 0
w3d_transition_regression_intermission_source: db 0
w3d_transition_regression_intermission_completion: db 0
w3d_transition_regression_intermission_owner: db 0
w3d_transition_regression_display_setup_count: db 0
w3d_transition_regression_display_setup_ready: db 0
w3d_transition_regression_display_ready_before_reset: db 0
w3d_transition_regression_display_owner_before_reset: db 0
w3d_transition_regression_intermission_phase: db 0
w3d_transition_regression_begin_package_count: db 0
w3d_transition_regression_begin_phase: db 0
w3d_transition_regression_destination_package_phase: db 0
w3d_transition_regression_tick_during_load: db 0
w3d_transition_regression_callback_tick_seen: db 0
w3d_transition_regression_finish_count: db 0
w3d_transition_regression_finish_ready: db 0
w3d_transition_regression_finish_owner: db 0
w3d_transition_regression_display_phase: db 0
w3d_transition_regression_display_finish_count: db 0
w3d_transition_regression_begin_before_package: db 0
'''
    return source


def instrument_loader(source: str) -> str:
    source = replace_once(
        source,
        "w3d_load_level_package:\n",
        "w3d_load_level_package:\n"
        "    call w3d_transition_regression_count_package_load\n",
        "level-package loader",
    )
    source = replace_once(
        source,
        "w3d_transition_to_next_level:\n",
        "w3d_transition_to_next_level:\n"
        "    call w3d_transition_regression_count_transition\n",
        "level-transition entry",
    )
    explicit_tick_count = source.count("    call w3d_intermission_loading_tick\n")
    if explicit_tick_count != 3:
        raise RuntimeError(
            "production explicit intermission loading-tick markers changed: "
            f"expected three, found {explicit_tick_count}"
        )
    source = source.replace(
        "    call w3d_intermission_loading_tick\n",
        "    call w3d_transition_regression_intermission_loading_tick\n",
    )
    callback_count = source.count("    ld hl,w3d_intermission_loading_tick\n")
    if callback_count != 2:
        raise RuntimeError(
            "production intermission image callback marker changed: "
            f"expected twice, found {callback_count}"
        )
    source = source.replace(
        "    ld hl,w3d_intermission_loading_tick\n",
        "    ld hl,w3d_transition_regression_intermission_image_callback\n",
    )
    source = replace_once(
        source,
        "    call w3d_intermission_finish\n",
        "    call w3d_transition_regression_intermission_finish\n",
        "intermission finish lifecycle",
    )
    # The production transition sits close to the eZ80 JR displacement limit.
    # Temporary recorder calls add a few bytes, so widen only its terminal
    # error/abort branches; this does not change their control-flow contract.
    for target in (
        "@user_aborted",
        "@package_aborted",
        "@package_failed",
        "@asset_failed",
    ):
        source = source.replace(f"    jr c,{target}\n", f"    jp c,{target}\n")
        source = source.replace(f"    jr nz,{target}\n", f"    jp nz,{target}\n")
        source = source.replace(f"    jr {target}\n", f"    jp {target}\n")
    display_contract = (
        "    ld hl,w3d_display_setup\n"
        "    ld bc,w3d_display_setup_end-w3d_display_setup\n"
        "    rst.lil 18h\n"
        "    call w3d_seed_level_transition_state\n"
    )
    source = replace_once(
        source,
        display_contract,
        display_contract.replace(
            "    call w3d_seed_level_transition_state\n",
            "    call w3d_transition_regression_count_display_setup\n"
            "    call w3d_seed_level_transition_state\n",
        ),
        "destination display restoration order",
    )
    reset_contract = (
        "    call w3d_initialize_control_clock\n"
        "    call w3d_death_prepare_next_render\n"
        "    call w3d_submit_level_reset\n"
    )
    source = replace_once(
        source,
        reset_contract,
        "    call w3d_initialize_control_clock\n"
        "    call w3d_death_prepare_next_render\n"
        "    call w3d_transition_regression_capture_pre_reset\n"
        "    call w3d_submit_level_reset\n",
        "destination reset submission order",
    )
    # This exact marker makes the wire-level replacement contract part of the
    # production regression: stock BUFFERED_WRITE appends blocks, so clearing
    # buffer 2 must precede every 4096-byte tilemap upload.
    replacement = (
        "w3d_replace_level_tilemap_buffer:\n"
        "    ld hl,W3D_FIXTURE_TILEMAP_BUFFER_ID\n"
        "    call vdu_clear_buffer\n"
        "    ld hl,W3D_FIXTURE_TILEMAP_BUFFER_ID\n"
        "    ld bc,W3D_MAP_BYTES\n"
        "    ld de,(w3d_level_tilemap_ptr)\n"
        "    jp vdu_load_buffer\n"
    )
    return replace_once(
        source,
        replacement,
        "w3d_replace_level_tilemap_buffer:\n"
        "    call w3d_transition_regression_count_tilemap_replace\n"
        + replacement.removeprefix("w3d_replace_level_tilemap_buffer:\n"),
        "clear-before-write tilemap replacement",
    )


def target_level(start_level: int, completion: str) -> int | None:
    if completion == "victory" or (completion == "normal" and start_level == 8):
        return None
    if completion == "secret":
        return 9
    if start_level == 9:
        return 1
    return start_level + 1


def expected_payload(
    *, start_level: int, completion: str, target: int | None, difficulty: int
) -> bytes:
    victory = target is None
    observed_level = start_level if victory else target
    package = parse_package(
        (
            GENERATED
            / "levels"
            / f"level_{observed_level:02d}"
            / f"state_{('baby', 'easy', 'medium', 'hard')[difficulty]}.w3l"
        ).read_bytes()
    )
    payload = bytearray(RESULT_SIZE)
    payload[:4] = b"W3T4"
    payload[4:20] = bytes(
        (
            observed_level,
            difficulty,
            package.door_count,
            package.actor_count,
            package.static_count & 0xFF,
            package.static_count >> 8,
            73,
            17,
            2,
            2,
            15 if victory else 0,
            3 if victory else 0,
            9 if victory else 0,
            0,
            package.player_pose[2],
            package.player_pose[6],
        )
    )
    payload[20] = 0 if victory else 1  # none after victory; reset render in flight otherwise
    payload[21] = 1 if victory else 0  # W3D_GAMEPLAY_RESULT_VICTORY / default EXIT
    payload[22] = 1 if victory else 0  # shell-resume seam reached exactly once
    payload[23] = 1 if victory else 2  # initial package only / initial + destination
    payload[24] = 0 if victory else 1  # generic transition must be bypassed for victory
    payload[25] = 1 if victory else 0  # result kind
    # callback_error and exit_requested remain zero. Startup replaces one map;
    # an ordinary transition replaces the destination map a second time.
    payload[28] = 1 if victory else 2
    if not victory:
        payload[29] = 1  # one source-floor intermission
        payload[30] = start_level
        payload[31] = {"normal": 1, "secret": 2}[completion]
        payload[32] = 0  # W3D_ASYNC_OWNER_NONE at intermission entry
        payload[33] = 1  # one destination display restoration
        payload[34] = 1  # restoration happened before reset submission
        payload[35] = 0  # no owner before destination reset acquired it
        payload[36] = 1  # begin followed exactly the initial package load
        payload[37] = 0  # begin was the first intermission lifecycle event
        payload[38] = 1  # destination package entered after begin
        payload[39] = 1  # a tick occurred while destination loading was live
        payload[40] = 1  # at least one finalized AGNB image invoked callback
        payload[41] = 1  # finish ran exactly once
        payload[42] = 1  # package and tilemap were ready at finish
        payload[43] = 0  # no asynchronous owner at finish
        payload[44] = 3  # display restoration observed post-finish phase
        payload[45] = 1  # exactly one finish preceded display restoration
        payload[46] = 1  # begin was observed before destination package entry
    # Reserved tail remains zero; victory bypasses every intermission field.
    return bytes(payload)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timeout", type=float, default=240.0)
    parser.add_argument("--start-level", type=int, default=0, choices=range(10))
    parser.add_argument(
        "--completion", choices=("normal", "secret", "victory"), default="normal"
    )
    parser.add_argument("--difficulty", type=int, default=2, choices=range(4))
    args = parser.parse_args()
    target = target_level(args.start_level, args.completion)

    work = Path(tempfile.mkdtemp(prefix="w3t"))
    atexit.register(shutil.rmtree, work, ignore_errors=True)
    source_root = work / "src"
    shutil.copytree(STAGED_SRC, source_root)
    # Lifecycle work may be qualified while the presentation module is being
    # developed in parallel. The temporary source replaces its only production
    # call with the recorder above, so an empty include is sufficient until the
    # real module exists. Never create or modify this placeholder in the repo.
    intermission_path = source_root / "wolf3d_intermission.inc"
    if not intermission_path.exists():
        intermission_path.write_text("; transition-regression placeholder\n")
    source_path = source_root / "wolf3d.asm"
    source_path.write_text(
        instrument(
            source_path.read_text(),
            start_level=args.start_level,
            completion=args.completion,
            difficulty=args.difficulty,
        )
    )
    loader_path = source_root / "wolf3d_level_loader.inc"
    loader_path.write_text(instrument_loader(loader_path.read_text()))

    sdcard = work / "sdcard"
    app = sdcard / "wolf3d"
    app.mkdir(parents=True)
    binary = app / "wolf3d.bin"
    run(["ez80asm", "wolf3d.asm", str(binary)], cwd=source_root)
    (sdcard / "autoexec.txt").write_bytes(
        b"SET KEYBOARD 1\r\ncd wolf3d\r\nload wolf3d.bin\r\nrun\r\n"
    )

    shutil.copyfile(GENERATED / "shell/shell.agnb", app / "shell.agnb")
    shutil.copyfile(GENERATED / "hud/hud.agnb", app / "hud.agnb")
    staged_levels = {args.start_level}
    if target is not None:
        staged_levels.add(target)
    for index in sorted(staged_levels):
        level = GENERATED / "levels" / f"level_{index:02d}"
        shutil.copytree(level, app / level.name)
    if target is None and (app / "level_09").exists():
        raise RuntimeError("victory fixture must not stage level_09")

    result = app / "transition_result.bin"
    environment = os.environ.copy()
    environment["SDL_VIDEODRIVER"] = "dummy"
    environment["SDL_AUDIODRIVER"] = "dummy"
    local_lib = str(Path.home() / ".local/lib")
    environment["LD_LIBRARY_PATH"] = local_lib + (
        ":" + environment["LD_LIBRARY_PATH"]
        if environment.get("LD_LIBRARY_PATH")
        else ""
    )
    emulator = [
        str(FAB.resolve()),
        "--renderer",
        "sw",
        "--firmware",
        "console8",
        "--mos",
        str(MOS.resolve()),
        "--vdp",
        str(VDP.resolve()),
        "--sdcard",
        str(sdcard),
        "--zero",
    ]
    print("+", " ".join(emulator))
    stdout_path = work / "emulator.stdout.log"
    stderr_path = work / "emulator.stderr.log"
    stdout_stream = stdout_path.open("wb")
    stderr_stream = stderr_path.open("wb")
    process = subprocess.Popen(
        emulator,
        cwd=work,
        env=environment,
        stdout=stdout_stream,
        stderr=stderr_stream,
    )
    failure: str | None = None
    payload = b""
    try:
        deadline = time.monotonic() + args.timeout
        while time.monotonic() < deadline:
            if process.poll() is not None:
                failure = f"emulator exited with {process.returncode}"
                break
            if result.exists():
                payload = result.read_bytes()
                if len(payload) == RESULT_SIZE and payload[:4] == b"W3T4":
                    break
            time.sleep(0.05)
        else:
            failure = "timed out waiting for production lifecycle result"
    finally:
        process.terminate()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        stdout_stream.close()
        stderr_stream.close()

    if failure:
        stdout_tail = stdout_path.read_text(errors="replace")[-4000:]
        stderr_tail = stderr_path.read_text(errors="replace")[-4000:]
        raise RuntimeError(
            f"{failure}\nemulator stdout tail:\n{stdout_tail}\n"
            f"emulator stderr tail:\n{stderr_tail}"
        )

    expected = expected_payload(
        start_level=args.start_level,
        completion=args.completion,
        target=target,
        difficulty=args.difficulty,
    )
    if payload != expected:
        print(f"FAIL: lifecycle state {payload.hex()} expected {expected.hex()}")
        return 1
    if target is None:
        if (app / "level_09").exists():
            print("FAIL: victory run unexpectedly acquired a level_09 directory")
            return 1
        print(
            "PASS: production "
            f"level {args.start_level} {args.completion} -> victory "
            "drained async ownership, bypassed level loading, and re-entered shell"
        )
    else:
        print(
            "PASS: production "
            f"level {args.start_level} {args.completion} -> level {target} "
            "load/reset preserved and cleared exact state"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
