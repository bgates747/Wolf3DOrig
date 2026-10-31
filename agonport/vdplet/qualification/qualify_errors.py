#!/usr/bin/env python3
"""Run bounded Wolf error/cleanup paths through an uploaded Xtensa VDPlet."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import struct
import time

from target import Target, sha, upload, word


HERE = Path(__file__).resolve().parent
BUILD = HERE / "build"
FIXTURE = BUILD / "fixture"
MODULE = BUILD / "wolf3d_scene.vdpl"

WORKSPACE_ID = 0x7100
MAP_ID = 0x7101
TEXTURE_ID = 0x7102
CONFIG_ID = 0x7103

VDPL_E_ARGUMENT = 1
VDPL_E_BUFFER = 2
VDPL_E_BOUNDS = 3
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


def send_buffer(target: Target, key: int, payload: bytes) -> None:
    target.send(upload(key, payload))


def qualify(engine: str, firmware: Path, backend: Path, timeout: float) -> dict:
    output = BUILD / f"target-errors-{engine}"
    target = Target(engine, output, backend, firmware, timeout)
    report = {
        "scope": (
            "actual uploaded Xtensa bounded-scene error and lease-cleanup paths; "
            "no full-game, physical or publication claim"
        ),
        "engine": engine,
        "firmware_sha256": sha(firmware),
        "firmware_elf_sha256": sha(firmware.with_suffix(".elf")),
        "adapter_sha256": sha(backend),
        "module_sha256": sha(MODULE),
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
        handle = target.load(MODULE)

        # The runtime validates the argument-buffer handle before dispatching
        # RUN, even for module entries which ignore their arguments. Supply a
        # valid, retained argument buffer so these first two cases exercise
        # the module's own unconfigured/unsupported-entry decisions.
        config = (FIXTURE / "config.bin").read_bytes()
        send_buffer(target, CONFIG_ID, config)

        def expected(entry: int, arguments: int, error: int, label: str) -> None:
            target.run(handle, entry, arguments, expected=error)
            report["expected_errors"].append({"case": label, "error": error})

        expected(1, CONFIG_ID, VDPL_E_INIT, "render before CONFIG")
        expected(0x7fff, CONFIG_ID, VDPL_E_UNSUPPORTED, "unsupported entry")

        send_buffer(target, CONFIG_ID, config[:-1])
        expected(0, CONFIG_ID, VDPL_E_ARGUMENT, "short CONFIG")
        invalid = bytearray(config)
        invalid[:4] = b"\0\0\0\0"
        send_buffer(target, CONFIG_ID, bytes(invalid))
        expected(0, CONFIG_ID, VDPL_E_ARGUMENT, "bad CONFIG magic")

        send_buffer(target, CONFIG_ID, config)
        target.run(handle, 0, CONFIG_ID)
        expected(1, CONFIG_ID, VDPL_E_BUFFER, "missing workspace")

        send_buffer(target, WORKSPACE_ID, b"\0")
        expected(1, CONFIG_ID, VDPL_E_BOUNDS, "short workspace")
        send_buffer(target, WORKSPACE_ID, (FIXTURE / "workspace.bin").read_bytes())
        expected(1, CONFIG_ID, VDPL_E_BUFFER, "missing map after workspace lease")

        send_buffer(target, MAP_ID, b"\0")
        expected(1, CONFIG_ID, VDPL_E_BOUNDS, "short map after workspace lease")
        send_buffer(target, MAP_ID, (FIXTURE / "map.bin").read_bytes())
        expected(1, CONFIG_ID, VDPL_E_BUFFER,
                 "missing textures after workspace/map leases")

        send_buffer(target, TEXTURE_ID, b"\0")
        expected(1, CONFIG_ID, VDPL_E_BOUNDS,
                 "short textures after workspace/map leases")
        send_buffer(target, TEXTURE_ID, (FIXTURE / "textures.bin").read_bytes())
        target.run(handle, 1, CONFIG_ID)
        report["checks"].append(
            "successful render after each missing/short-resource failure proves lease cleanup"
        )

        send_buffer(target, CONFIG_ID, bytes(invalid))
        expected(0, CONFIG_ID, VDPL_E_ARGUMENT, "invalid reconfigure")
        target.run(handle, 1, CONFIG_ID)
        report["checks"].append(
            "invalid reconfigure preserves the last complete valid mirror"
        )

        target.send(bytes((23, 0, 195)))
        width, height, actual = target.capture()
        oracle = (BUILD / "oracle-frame.bin").read_bytes()
        expected_frame = rgb222_frame(oracle)
        if (width, height) != (320, 240) or actual != expected_frame:
            mismatch = next(
                (index // 3 for index, pair in enumerate(zip(actual, expected_frame))
                 if pair[0] != pair[1]),
                -1,
            )
            raise AssertionError(f"post-error frame mismatch at pixel {mismatch}")
        report["checks"].append(
            "post-error render and C3 match all 76800 oracle pixels"
        )

        target.unload(handle)
        handle = 0
        slot = target.transaction(4, word(2), 4, 0)
        report["checks"].append("normal unload leaves the module slot empty")
        report.update(
            passed=True,
            frame_sha256=sha(BUILD / "oracle-frame.bin"),
            expected_error_count=len(report["expected_errors"]),
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
        evidence = BUILD / f"target-errors-{engine}-evidence.json"
        evidence.write_text(json.dumps(report, indent=2) + "\n")
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
    parser.add_argument("--timeout", type=float, default=600)
    arguments = parser.parse_args()
    result = qualify(
        arguments.engine, arguments.firmware.resolve(),
        arguments.backend.resolve(), arguments.timeout,
    )
    print(json.dumps({
        key: result[key] for key in (
            "passed", "engine", "expected_error_count", "slot_after_teardown",
            "elapsed_seconds",
        )
    }, indent=2))
