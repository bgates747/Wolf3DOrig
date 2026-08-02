#!/usr/bin/env python3
"""Exercise a real E1L1 -> E1L2 load/reset through the production eZ80 app."""

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


HERE = Path(__file__).resolve().parent
_root_override = os.environ.get("W3D_STAGED_ROOT")
_installed_root = Path(__file__).resolve().parents[4]
STAGED_ROOT = Path(_root_override) if _root_override else _installed_root
RUNTIME_ROOT = Path(os.environ.get("W3D_RUNTIME_ROOT", _installed_root))
STAGED_SRC = STAGED_ROOT / "src/asm/wolf3d/src"
GENERATED = STAGED_ROOT / "agonport/assets/generated/wolf3d"
FAB = RUNTIME_ROOT / "agonport/emulator/fab-agon-emulator"
MOS = RUNTIME_ROOT / "agonport/emulator/mos_console8.bin"
VDP = RUNTIME_ROOT / "agonport/emulator/vdp_wolf3d.so"
RESULT_SIZE = 20

sys.path.insert(0, str(STAGED_ROOT / "agonport/tools/wolf3d_assets"))
from formats.level_package import parse_package  # noqa: E402


def run(command: list[str], *, cwd: Path | None = None) -> None:
    print("+", " ".join(command))
    subprocess.run(command, check=True, cwd=cwd)


def instrument(source: str, *, start_level: int, completion: str) -> str:
    source = source.replace(
        "mos_load:        equ 01h\n",
        "mos_load:        equ 01h\nmos_save:        equ 02h\n",
        1,
    )
    startup_markers = (
        ("w3d_main_body:\n", 10),
        ("@level_state_loaded:\n", 11),
        ("@assets_loaded:\n", 12),
        ("@sprites_loaded:\n", 13),
        ("@hud_loaded:\n", 14),
        ("@sfx_loaded:\n", 15),
    )
    for marker, phase in startup_markers:
        if source.count(marker) != 1:
            raise RuntimeError("production startup marker changed; update transition regression")
        source = source.replace(
            marker,
            marker
            + f"    ld a,{phase}\n"
            + "    call w3d_transition_regression_write_phase\n",
            1,
        )
    loader_failure = (
        "    call w3d_load_level_package\n"
        "    jr z,@level_state_loaded\n"
        "    call w3d_set_level_load_error\n"
        "    ret\n"
    )
    if source.count(loader_failure) != 1:
        raise RuntimeError("production loader-failure marker changed; update regression")
    source = source.replace(
        loader_failure,
        "    call w3d_load_level_package\n"
        "    jr z,@level_state_loaded\n"
        "    cp W3D_LEVEL_LOAD_BOUNDS_ERROR\n"
        "    ret z\n"
        "    add a,20\n"
        "    call w3d_transition_regression_write_phase\n"
        "    ret\n",
        1,
    )
    startup_load = (
        "    ld a,(w3d_requested_difficulty)\n"
        "    ld b,a\n"
        "    xor a\n"
        "    call w3d_load_level_package\n"
    )
    if source.count(startup_load) != 1:
        raise RuntimeError("production startup-level marker changed; update regression")
    source = source.replace(
        startup_load,
        "    ld a,(w3d_requested_difficulty)\n"
        "    ld b,a\n"
        f"    ld a,{start_level}\n"
        "    call w3d_load_level_package\n",
        1,
    )
    source = source.replace(
        "    call w3d_submit_level_reset\n"
        "    jp c,w3d_main_shutdown\n\n"
        "mainloop:\n",
        "    call w3d_submit_level_reset\n"
        "    jp c,w3d_main_shutdown\n"
        "; Regression-only persistent fields and forced normal completion.\n"
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
        "    ld a,1\n"
        "    call w3d_transition_regression_write_phase\n\n"
        "mainloop:\n",
        1,
    )
    source = source.replace(
        "    call w3d_transition_to_next_level\n"
        "    jr c,@shutdown\n"
        "    jp mainloop\n",
        "    call w3d_transition_to_next_level\n"
        "    jr c,@shutdown\n"
        "    call w3d_transition_regression_write_result\n"
        "    jp mainloop\n",
        1,
    )
    source += r'''

; Added only to the temporary regression source.
w3d_transition_regression_write_result:
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
    ld hl,w3d_transition_regression_filename
    ld de,w3d_transition_regression_result
    ld bc,20
    MOSCALL mos_save
    ret

w3d_transition_regression_filename:
    db "transition_result.bin",0
w3d_transition_regression_result:
    db "W3T1"
    ds 16

w3d_transition_regression_write_phase:
    ld (w3d_transition_regression_phase),a
    ld hl,w3d_transition_regression_phase_filename
    ld de,w3d_transition_regression_phase
    ld bc,8
    MOSCALL mos_save
    ret
w3d_transition_regression_phase_filename:
    db "transition_phase.bin",0
w3d_transition_regression_phase:
    ds 8
w3d_transition_regression_loader_stage:
    db 0
'''
    return source


def instrument_loader(source: str) -> str:
    validation_markers = (
        ("    VALIDATE_W3L_OFFSET W3L_DOORS_OFFSET\n", 1),
        ("    VALIDATE_W3L_OFFSET W3L_STATICS_OFFSET\n", 2),
        ("    VALIDATE_W3L_OFFSET W3L_ACTORS_OFFSET\n", 3),
        ("    VALIDATE_W3L_OFFSET W3L_BLOCKING_OFFSET\n", 4),
        ("    VALIDATE_W3L_OFFSET W3L_AREAS_OFFSET\n", 5),
        ("    VALIDATE_W3L_OFFSET W3L_PATHS_OFFSET\n", 6),
        ("    VALIDATE_W3L_OFFSET W3L_TILEMAP_OFFSET\n", 7),
        ("    ld de,@footer\n", 8),
        ("    ld de,0\n    ld a,(w3d_level_package+W3L_TOTAL_SIZE+0)\n", 9),
    )
    for marker, stage in validation_markers:
        if source.count(marker) != 1:
            raise RuntimeError("production validation marker changed; update regression")
        source = source.replace(
            marker,
            f"    ld a,{stage}\n"
            "    ld (w3d_transition_regression_loader_stage),a\n"
            + marker,
            1,
        )
    footer_marker = "    ld de,@footer\n"
    if source.count(footer_marker) != 1:
        raise RuntimeError("production footer marker changed; update transition regression")
    source = source.replace(
        footer_marker,
        "    ld (w3d_transition_regression_phase+1),hl\n"
        "    push hl\n"
        "    ld de,w3d_transition_regression_phase+4\n"
        "    ld bc,4\n"
        "    ldir\n"
        "    pop hl\n"
        + footer_marker,
        1,
    )
    bounds_handler = (
        "w3d_level_load_bounds_error:\n"
        "    ld a,W3D_LEVEL_LOAD_BOUNDS_ERROR\n"
        "    or a\n"
        "    ret\n"
    )
    if source.count(bounds_handler) != 1:
        raise RuntimeError("production bounds handler changed; update regression")
    source = source.replace(
        bounds_handler,
        "w3d_level_load_bounds_error:\n"
        "    ld a,(w3d_transition_regression_loader_stage)\n"
        "    add a,30\n"
        "    call w3d_transition_regression_write_phase\n"
        "    ld a,W3D_LEVEL_LOAD_BOUNDS_ERROR\n"
        "    or a\n"
        "    ret\n",
        1,
    )
    replacements = (
        (
            "w3d_transition_to_next_level:\n",
            "w3d_transition_to_next_level:\n"
            "    ld a,2\n"
            "    call w3d_transition_regression_write_phase\n",
        ),
        (
            "    call w3d_load_level_package\n"
            "    jr nz,@package_failed\n\n"
            "    ld de,w3d_level_tiles_filename\n",
            "    call w3d_load_level_package\n"
            "    jr nz,@package_failed\n"
            "    ld a,3\n"
            "    call w3d_transition_regression_write_phase\n\n"
            "    ld de,w3d_level_tiles_filename\n",
        ),
        (
            "    call agnb_load_images_with_callback\n"
            "    jr nz,@asset_failed\n"
            "    ld de,w3d_level_sprites_filename\n",
            "    call agnb_load_images_with_callback\n"
            "    jr nz,@asset_failed\n"
            "    ld a,4\n"
            "    call w3d_transition_regression_write_phase\n"
            "    ld de,w3d_level_sprites_filename\n",
        ),
        (
            "    call agnb_load_images_with_callback\n"
            "    jr nz,@asset_failed\n\n"
            "    ld hl,W3D_FIXTURE_TILEMAP_BUFFER_ID\n",
            "    call agnb_load_images_with_callback\n"
            "    jr nz,@asset_failed\n"
            "    ld a,5\n"
            "    call w3d_transition_regression_write_phase\n\n"
            "    ld hl,W3D_FIXTURE_TILEMAP_BUFFER_ID\n",
        ),
        (
            "    call w3d_submit_level_reset\n"
            "    ret\n\n"
            "@package_failed:\n",
            "    call w3d_submit_level_reset\n"
            "    ret c\n"
            "    ld a,6\n"
            "    call w3d_transition_regression_write_phase\n"
            "    or a\n"
            "    ret\n\n"
            "@package_failed:\n",
        ),
    )
    for old, new in replacements:
        if source.count(old) != 1:
            raise RuntimeError("production loader marker changed; update transition regression")
        source = source.replace(old, new, 1)
    return source


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timeout", type=float, default=240.0)
    parser.add_argument("--start-level", type=int, default=0, choices=range(10))
    parser.add_argument("--completion", choices=("normal", "secret"), default="normal")
    args = parser.parse_args()

    if args.completion == "secret":
        target_level = 9
    elif args.start_level == 9:
        target_level = 1
    else:
        target_level = args.start_level + 1

    work = Path(tempfile.mkdtemp(prefix="w3t"))
    atexit.register(shutil.rmtree, work, ignore_errors=True)
    source_root = work / "src"
    shutil.copytree(STAGED_SRC, source_root)
    source = (source_root / "wolf3d.asm").read_text()
    instrumented = instrument(
        source,
        start_level=args.start_level,
        completion=args.completion,
    )
    if instrumented == source or "w3d_transition_regression_write_result" not in instrumented:
        raise RuntimeError("production integration markers changed; update transition regression")
    (source_root / "wolf3d.asm").write_text(instrumented)
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

    shutil.copyfile(GENERATED / "hud/hud.agnb", app / "hud.agnb")
    # A missing SFX file is an accepted partial-container path and keeps this
    # state/asset transition regression focused and fast.
    for index in sorted({args.start_level, target_level}):
        level = GENERATED / "levels" / f"level_{index:02d}"
        shutil.copytree(level, app / level.name)

    result = app / "transition_result.bin"
    phase_result = app / "transition_phase.bin"
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
    try:
        deadline = time.monotonic() + args.timeout
        payload = b""
        while time.monotonic() < deadline:
            if process.poll() is not None:
                failure = f"emulator exited with {process.returncode}"
                break
            if result.exists():
                payload = result.read_bytes()
                if len(payload) == RESULT_SIZE and payload[:4] == b"W3T1":
                    break
            time.sleep(0.05)
        else:
            failure = "timed out waiting for production level transition"
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
        phase = phase_result.read_bytes().hex() if phase_result.exists() else "none"
        stdout_tail = stdout_path.read_text(errors="replace")[-4000:]
        stderr_tail = stderr_path.read_text(errors="replace")[-4000:]
        raise RuntimeError(
            f"{failure}; last phase={phase}\n"
            f"emulator stdout tail:\n{stdout_tail}\n"
            f"emulator stderr tail:\n{stderr_tail}"
        )

    target_package = parse_package(
        (
            GENERATED
            / "levels"
            / f"level_{target_level:02d}"
            / "state_medium.w3l"
        ).read_bytes()
    )
    expected = bytes(
        (
            target_level,
            2,
            target_package.door_count,
            target_package.actor_count,
            target_package.static_count & 0xFF,
            target_package.static_count >> 8,
            73,
            17,
            2,
            2,
            0,
            0,
            0,
            0,
            target_package.player_pose[2],
            target_package.player_pose[6],
        )
    )
    if payload[4:] != expected:
        print(f"FAIL: transition state {payload[4:].hex()} expected {expected.hex()}")
        return 1
    print(
        "PASS: production "
        f"level {args.start_level} {args.completion} -> level {target_level} "
        "load/reset preserved and cleared exact state"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
