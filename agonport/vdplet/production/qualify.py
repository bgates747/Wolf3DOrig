#!/usr/bin/env python3
"""Qualify the exact production Wolf3D VDPlet package in the real runtime."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "qualification"))

from target import Target, command, sha, upload, word  # noqa: E402


BUILD = HERE / "build"
FIXTURE = BUILD / "target-fixture"
MODULE = BUILD / "wolf3d_production.vdpl"

WORKSPACE_ID = 0x7100
UPDATE_ID = 0x7101
ARGUMENT_ID = 0x7102
TILEMAP_ID = 0x0002
STATUS_BAR_ID = 0x4062

ENTRY_CONFIG = 0
ENTRY_APPLY_AND_RENDER = 1
ENTRY_FIZZLE_BEGIN = 2
ENTRY_RESET = 4

VDPL_E_ARGUMENT = 1
VDPL_E_BUFFER = 2
VDPL_E_HANDLE = 8
VDPL_E_UNSUPPORTED = 9
VDPL_E_INIT = 12


def rgb222_frame(values: bytes) -> bytes:
    output = bytearray(len(values) * 3)
    at = 0
    for value in values:
        output[at] = (value & 3) * 85
        output[at + 1] = ((value >> 2) & 3) * 85
        output[at + 2] = ((value >> 4) & 3) * 85
        at += 3
    return bytes(output)


def ppm(path: Path, pixels: bytes) -> None:
    path.write_bytes(b"P6\n320 240\n255\n" + pixels)


def asset_files() -> list[tuple[int, Path]]:
    assets = []
    for line in (FIXTURE / "assets.txt").read_text().splitlines():
        key, declared, filename = line.split()
        path = FIXTURE / filename
        if path.stat().st_size != int(declared):
            raise AssertionError(f"asset size drift: {line}")
        assets.append((int(key, 0), path))
    if STATUS_BAR_ID not in {key for key, _ in assets}:
        raise AssertionError("retry asset is absent from fixture")
    return assets


def compare_capture(target: Target, expected: bytes, label: str) -> bytes:
    width, height, actual = target.capture()
    decoded = rgb222_frame(expected)
    if (width, height) != (320, 240) or actual != decoded:
        mismatch = next(
            (index // 3 for index, pair in enumerate(zip(actual, decoded))
             if pair[0] != pair[1]),
            -1,
        )
        raise AssertionError(f"{label} mismatch at pixel {mismatch}")
    return actual


def qualify(engine: str, firmware: Path, backend: Path, output: Path,
            timeout: float) -> dict:
    if output.exists():
        raise FileExistsError(f"refusing to overwrite evidence: {output}")
    assets = asset_files()
    expected_full = (FIXTURE / "expected-full.bin").read_bytes()
    expected_retry = (FIXTURE / "expected-retry.bin").read_bytes()
    if len(expected_full) != 76800 or len(expected_retry) != 76800:
        raise AssertionError("expected frame size drift")

    target = Target(engine, output, backend, firmware, timeout)
    report = {
        "scope": (
            "exact production Xtensa package, native retry and lifecycle in "
            "runtime emulator; no gameplay or physical claim"
        ),
        "engine": engine,
        "firmware_sha256": sha(firmware),
        "firmware_elf_sha256": sha(firmware.with_suffix(".elf")),
        "adapter_sha256": sha(backend),
        "module_sha256": sha(MODULE),
        "fixture_files": 7 + len(assets),
        "fixture_asset_buffers": len(assets),
        "checks": [],
        "expected_errors": [],
        "passed": False,
    }
    handle = 0
    try:
        capabilities = target.transaction(4, word(1), 4)
        if capabilities & 17 != 17:
            raise AssertionError(f"runtime capabilities {capabilities} lack mask17")
        report["capabilities"] = capabilities

        target.send(bytes((22, 136, 23, 1, 0, 23, 0, 192, 0, 26, 12)))
        target.barrier()
        width, height, baseline = target.capture()
        if (width, height) != (320, 240):
            raise AssertionError((width, height))

        handle = target.load(MODULE)
        fixed = (
            (WORKSPACE_ID, "workspace.bin"),
            (UPDATE_ID, "update-full.bin"),
            (ARGUMENT_ID, "argument.bin"),
            (TILEMAP_ID, "tilemap.bin"),
        )
        for key, filename in fixed:
            target.send(upload(key, (FIXTURE / filename).read_bytes()))
        for key, path in assets:
            target.send(upload(key, path.read_bytes()))
        report["checks"].append(
            "exact generated workspace, descriptor, full batch, map and assets uploaded"
        )

        stack_before = target.transaction(4, word(17), 4)
        target.run(handle, ENTRY_CONFIG, ARGUMENT_ID)
        cycles_before = target.lib.flexe_vdp_cycles()
        started = time.monotonic()
        target.run(handle, ENTRY_APPLY_AND_RENDER, ARGUMENT_ID)
        elapsed = time.monotonic() - started
        cycles_after = target.lib.flexe_vdp_cycles()

        if target.capture()[2] != baseline:
            raise AssertionError("first hidden frame became visible before C3")
        target.send(bytes((23, 0, 195)))
        full_rgb = compare_capture(target, expected_full, "full frame")
        ppm(output / "production-full.ppm", full_rgb)
        report["checks"].append(
            "full batch, DONE fence, hidden-before-C3 and 76800-pixel oracle parity"
        )

        retry_update = (FIXTURE / "update-retry.bin").read_bytes()
        target.send(upload(UPDATE_ID, retry_update))
        target.send(command(STATUS_BAR_ID, 2))
        target.run(handle, ENTRY_APPLY_AND_RENDER, ARGUMENT_ID,
                   expected=VDPL_E_BUFFER)
        report["expected_errors"].append(
            {"case": "missing HUD asset after update application", "error": VDPL_E_BUFFER}
        )

        altered = bytearray(retry_update)
        if len(altered) < 26 or altered[16] != 7 or altered[17] != 12:
            raise AssertionError("retry HUD batch layout drift")
        altered[22] ^= 1
        target.send(upload(UPDATE_ID, bytes(altered)))
        target.run(handle, ENTRY_APPLY_AND_RENDER, ARGUMENT_ID,
                   expected=VDPL_E_ARGUMENT)
        report["expected_errors"].append(
            {"case": "altered same-generation retry", "error": VDPL_E_ARGUMENT}
        )

        status_bar = dict(assets)[STATUS_BAR_ID]
        target.send(upload(STATUS_BAR_ID, status_bar.read_bytes()))
        target.send(upload(UPDATE_ID, retry_update))
        target.run(handle, ENTRY_APPLY_AND_RENDER, ARGUMENT_ID)
        if target.capture()[2] != full_rgb:
            raise AssertionError("retried hidden frame became visible before C3")
        target.send(bytes((23, 0, 195)))
        retry_rgb = compare_capture(target, expected_retry, "retry frame")
        ppm(output / "production-retry.ppm", retry_rgb)
        report["checks"].append(
            "native missing-asset error, altered refusal, exact retry and second oracle frame"
        )

        target.run(handle, ENTRY_FIZZLE_BEGIN, ARGUMENT_ID,
                   expected=VDPL_E_UNSUPPORTED)
        report["expected_errors"].append(
            {"case": "deferred fizzle entry", "error": VDPL_E_UNSUPPORTED}
        )
        target.run(handle, ENTRY_RESET, ARGUMENT_ID)
        target.run(handle, ENTRY_APPLY_AND_RENDER, ARGUMENT_ID,
                   expected=VDPL_E_INIT)
        report["expected_errors"].append(
            {"case": "render after RESET", "error": VDPL_E_INIT}
        )
        stack_after = target.transaction(4, word(17), 4)

        target.unload(handle)
        stale = handle
        handle = 0
        target.run(stale, ENTRY_APPLY_AND_RENDER, ARGUMENT_ID,
                   expected=VDPL_E_HANDLE)
        second = target.load(MODULE)
        target.unload(second)
        slot = target.transaction(4, word(2), 4, 0)
        report["checks"].append(
            "RESET, FINI via unload, stale-handle rejection, reload and empty slot"
        )

        report.update(
            passed=True,
            full_frame_sha256=sha(FIXTURE / "expected-full.bin"),
            retry_frame_sha256=sha(FIXTURE / "expected-retry.bin"),
            expected_error_count=len(report["expected_errors"]),
            render_reply_seconds=round(elapsed, 6),
            render_vdp_cycles=cycles_after - cycles_before,
            stack_free_before=stack_before,
            stack_free_after=stack_after,
            stack_minimum_free_bytes_after_exercised_path=stack_after,
            slot_after_teardown=slot,
        )
    except BaseException as error:
        report["failure"] = f"{type(error).__name__}: {error}"
        raise
    finally:
        if handle:
            try:
                target.unload(handle)
            except BaseException:
                pass
        stats = target.close()
        report["execution_stats"] = stats
        report["outbound_bytes"] = target.sent
        report["reply_bytes"] = len(target.observed)
        report["elapsed_seconds"] = round(time.monotonic() - target.start, 3)
        (output / "evidence.json").write_text(json.dumps(report, indent=2) + "\n")
        if report["passed"] and any(
            stats.get(key) for key in
            ("failed", "unhandled", "unregistered", "unmapped")
        ):
            raise AssertionError(stats)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine", choices=("jit", "interp"), default="jit")
    parser.add_argument("--firmware", type=Path, required=True)
    parser.add_argument("--backend", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout", type=float, default=600)
    arguments = parser.parse_args()
    result = qualify(
        arguments.engine, arguments.firmware.resolve(),
        arguments.backend.resolve(), arguments.output.resolve(),
        arguments.timeout,
    )
    print(json.dumps({
        key: result[key] for key in (
            "passed", "engine", "expected_error_count", "render_reply_seconds",
            "render_vdp_cycles", "stack_free_after", "slot_after_teardown",
            "elapsed_seconds",
        )
    }, indent=2))
