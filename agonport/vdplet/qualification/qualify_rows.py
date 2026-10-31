#!/usr/bin/env python3
"""Finite matched copied/direct Wolf colour-row target qualifier.

Importing this file never starts a backend. Each invocation owns one engine
process and requires the central Oryx lease before it may be executed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import statistics
import struct
import time

from target import Target, sha, upload, word


HERE = Path(__file__).resolve().parent
BUILD = HERE / "build"
FIXTURE = BUILD / "fixture"
COPIED_MODULE = BUILD / "wolf3d_scene.vdpl"
DIRECT_MODULE = BUILD / "wolf3d_scene_rows.vdpl"
ORACLE_FRAME = BUILD / "oracle-frame.bin"
ORACLE_GEOMETRY = BUILD / "oracle-geometry.bin"

WORKSPACE_ID = 0x7100
MAP_ID = 0x7101
TEXTURE_ID = 0x7102
CONFIG_ID = 0x7103
MODULE_ID = 60023

COPIED_WORKSPACE_BYTES = 92160
DIRECT_WORKSPACE_BYTES = 11552
COPIED_GEOMETRY_OFFSET = 76800
DIRECT_GEOMETRY_OFFSET = 960
GEOMETRY_BYTES = 1792
EXPECTED_CAPABILITY_MASK = 273

PINS = {
    "firmware": "8d980025f891484cf7e6cc5f2992cf517cb80e0123ff7de712ae8d7f2dc1c807",
    "firmware_elf": "1a7c44482d4ba8c5bfb49976c0bd664b9a9c2a635c7027b30954929ca567f814",
    "backend": "0866265bd6f3d73ad572f31dc1bb954f308ed9a5d857efa9414d37e1ade13374",
    "copied_module": "57b635fc1807d9108e576cfff4c79c7f57ade48164fc5be97d75a3562e54b1be",
    "direct_module": "c32381bc659b6e1fcc479eef22168a77eea22da310202da794234f172ccab670",
    "oracle_frame": "6b569190c057996d4c50c1cc182c5b210a05a5e8c6fc7f9e60059d892363bf93",
    "oracle_geometry": "2a15866957fa06d34f72067b2b1ff42325b3c3d0f02403059d43dc9a6812d820",
}


def verify(path: Path, expected: str) -> None:
    actual = sha(path)
    if actual != expected:
        raise AssertionError(f"pin mismatch {path}: {actual} != {expected}")


def rgb222_frame(values: bytes) -> bytes:
    output = bytearray(len(values) * 3)
    at = 0
    for value in values:
        output[at] = (value & 3) * 85
        output[at + 1] = ((value >> 2) & 3) * 85
        output[at + 2] = ((value >> 4) & 3) * 85
        at += 3
    return bytes(output)


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def summary(values: list[float]) -> dict:
    if not values:
        raise AssertionError("empty timing sample set")
    return {
        "count": len(values),
        "minimum": min(values),
        "median": statistics.median(values),
        "p90": percentile(values, 0.90),
        "maximum": max(values),
        "mean": statistics.fmean(values),
    }


def read_buffer(target: Target, buffer_id: int, offset: int, size: int) -> bytes:
    if size & 1:
        raise ValueError("READ16 size must be even")
    return b"".join(
        word(target.transaction(5, struct.pack("<HI", buffer_id, offset + at), 4))
        for at in range(0, size, 2)
    )


def resources(target: Target) -> dict:
    def wide(selector: int) -> int:
        return (target.transaction(4, word(selector), 4) |
                (target.transaction(4, word(selector + 1), 4) << 16))

    return {
        "command_stack_free_bytes": target.transaction(4, word(17), 4),
        "internal_free_bytes": wide(13),
        "internal_largest_block": wide(15),
        "spiram_free_bytes": wide(18),
        "spiram_largest_block": wide(20),
        "audio_stack_free_bytes": target.transaction(4, word(22), 4),
        "task_count": target.transaction(4, word(23), 4),
    }


def reset_surface(target: Target) -> bytes:
    target.send(bytes((22, 136, 23, 1, 0, 23, 0, 192, 0, 26, 12)))
    target.barrier()
    width, height, baseline = target.capture()
    if (width, height) != (320, 240):
        raise AssertionError((width, height))
    return baseline


def upload_scene(target: Target, workspace: bytes, config: bytes,
                 tilemap: bytes, textures: bytes) -> None:
    for buffer_id, payload in (
        (WORKSPACE_ID, workspace),
        (MAP_ID, tilemap),
        (TEXTURE_ID, textures),
        (CONFIG_ID, config),
    ):
        target.send(upload(buffer_id, payload))


def verify_hidden_and_present(target: Target, baseline: bytes,
                              expected: bytes) -> None:
    width, height, hidden = target.capture()
    if (width, height) != (320, 240) or hidden != baseline:
        raise AssertionError("render became visible before host C3")
    target.send(bytes((23, 0, 195)))
    width, height, visible = target.capture()
    if (width, height) != (320, 240) or visible != expected:
        mismatch = next(
            (index // 3 for index, pair in enumerate(zip(visible, expected))
             if pair[0] != pair[1]),
            -1,
        )
        raise AssertionError(f"presented frame mismatch at pixel {mismatch}")


def arm_spec(name: str, fixture_workspace: bytes) -> dict:
    if name == "copied":
        return {
            "name": name,
            "module": COPIED_MODULE,
            "workspace": fixture_workspace[:COPIED_WORKSPACE_BYTES],
            "geometry_offset": COPIED_GEOMETRY_OFFSET,
        }
    return {
        "name": name,
        "module": DIRECT_MODULE,
        "workspace": fixture_workspace[:DIRECT_WORKSPACE_BYTES],
        "geometry_offset": DIRECT_GEOMETRY_OFFSET,
    }


def correctness_arm(target: Target, arm: dict, fixture: dict,
                    expected_frame: bytes, expected_geometry: bytes) -> dict:
    baseline = reset_surface(target)
    upload_scene(target, arm["workspace"], fixture["config"],
                 fixture["map"], fixture["textures"])
    handle = target.load(arm["module"], MODULE_ID)
    try:
        target.run(handle, 1, CONFIG_ID, expected=12)
        target.run(handle, 0x7fff, CONFIG_ID, expected=9)
        target.run(handle, 0, CONFIG_ID)

        failures = []
        for buffer_id, full, required, label in (
            (WORKSPACE_ID, arm["workspace"], len(arm["workspace"]), "workspace"),
            (MAP_ID, fixture["map"], len(fixture["map"]), "map"),
            (TEXTURE_ID, fixture["textures"], len(fixture["textures"]), "textures"),
        ):
            target.send(upload(buffer_id, full[:required - 1]))
            target.run(handle, 1, CONFIG_ID, expected=3)
            failures.append(f"short {label}")
            target.send(upload(buffer_id, full))

        target.run(handle, 1, CONFIG_ID)
        invalid = bytearray(fixture["config"])
        invalid[:4] = b"\0\0\0\0"
        target.send(upload(CONFIG_ID, invalid))
        target.run(handle, 0, CONFIG_ID, expected=1)
        target.send(upload(CONFIG_ID, fixture["config"]))
        target.run(handle, 1, CONFIG_ID)

        actual_geometry = read_buffer(
            target, WORKSPACE_ID, arm["geometry_offset"], GEOMETRY_BYTES
        )
        if actual_geometry != expected_geometry:
            raise AssertionError(f"{arm['name']} geometry mismatch")
        verify_hidden_and_present(target, baseline, expected_frame)
    finally:
        target.unload(handle)

    stale = handle
    target.run(stale, 1, CONFIG_ID, expected=8)
    second = target.load(arm["module"], MODULE_ID)
    target.unload(second)
    if target.transaction(4, word(2), 4, 0) != 0:
        raise AssertionError("module slot not empty")
    return {
        "failures_recovered": failures,
        "geometry_bytes": len(actual_geometry),
        "frame_pixels": 320 * 240,
        "stale_handle": stale,
        "forgotten_end_diagnostic": "not exposed by primary package",
    }


def timed_arm(target: Target, arm: dict, fixture: dict, expected_frame: bytes,
              runs: int) -> dict:
    baseline = reset_surface(target)
    upload_scene(target, arm["workspace"], fixture["config"],
                 fixture["map"], fixture["textures"])
    handle = target.load(arm["module"], MODULE_ID)
    seconds = []
    cycles = []
    try:
        target.run(handle, 0, CONFIG_ID)
        target.run(handle, 1, CONFIG_ID)  # Untimed warm-up.
        for _ in range(runs):
            before_cycles = target.lib.flexe_vdp_cycles()
            started = time.monotonic_ns()
            target.run(handle, 1, CONFIG_ID)
            seconds.append((time.monotonic_ns() - started) / 1_000_000_000)
            cycles.append(target.lib.flexe_vdp_cycles() - before_cycles)
        verify_hidden_and_present(target, baseline, expected_frame)
    finally:
        target.unload(handle)
    return {"seconds": seconds, "cycles": cycles}


def qualify(arguments: argparse.Namespace) -> dict:
    verify(arguments.firmware, PINS["firmware"])
    verify(arguments.firmware.with_suffix(".elf"), PINS["firmware_elf"])
    verify(arguments.backend, PINS["backend"])
    verify(COPIED_MODULE, PINS["copied_module"])
    verify(DIRECT_MODULE, PINS["direct_module"])
    verify(ORACLE_FRAME, PINS["oracle_frame"])
    verify(ORACLE_GEOMETRY, PINS["oracle_geometry"])

    fixture = {
        "workspace": (FIXTURE / "workspace.bin").read_bytes(),
        "map": (FIXTURE / "map.bin").read_bytes(),
        "textures": (FIXTURE / "textures.bin").read_bytes(),
        "config": (FIXTURE / "config.bin").read_bytes(),
    }
    arms = [arm_spec("copied", fixture["workspace"]),
            arm_spec("direct", fixture["workspace"])]
    expected_frame = rgb222_frame(ORACLE_FRAME.read_bytes())
    expected_geometry = ORACLE_GEOMETRY.read_bytes()
    output = arguments.output.resolve()
    if output.exists() and any(output.iterdir()):
        raise SystemExit(
            f"refusing to overwrite target evidence directory: {output}"
        )
    output.mkdir(parents=True, exist_ok=True)
    report = {
        "scope": (
            "actual uploaded copied/direct Xtensa packages, decoded VGA, "
            "READ16 geometry and foreground RUN-reply timing; no physical, "
            "isolated-renderer, human-review or publication claim"
        ),
        "engine": arguments.engine,
        "pins": {name: value for name, value in PINS.items()},
        "timing_contract": (
            "time.monotonic_ns and flexe_vdp_cycles around requested RENDER "
            "RUN transaction only; includes wire/runtime dispatch and reply, "
            "excludes load/config/readback/capture/C3/unload"
        ),
        "timing_rounds": arguments.rounds,
        "runs_per_arm_per_round": arguments.runs,
        "correctness": {},
        "timing_samples": {"copied": {"seconds": [], "cycles": []},
                           "direct": {"seconds": [], "cycles": []}},
        "passed": False,
    }
    target = None
    started = time.monotonic()
    try:
        target = Target(arguments.engine, output, arguments.backend,
                        arguments.firmware, arguments.timeout)
        capabilities = target.transaction(4, word(1), 4)
        if capabilities & EXPECTED_CAPABILITY_MASK != EXPECTED_CAPABILITY_MASK:
            raise AssertionError(
                f"runtime capabilities {capabilities} lack mask "
                f"{EXPECTED_CAPABILITY_MASK}"
            )
        report["capabilities"] = capabilities
        report["resources_before"] = resources(target)

        for arm in arms:
            report["correctness"][arm["name"]] = correctness_arm(
                target, arm, fixture, expected_frame, expected_geometry
            )

        for _ in range(arguments.rounds):
            for arm in arms:
                samples = timed_arm(
                    target, arm, fixture, expected_frame, arguments.runs
                )
                for unit in ("seconds", "cycles"):
                    report["timing_samples"][arm["name"]][unit].extend(
                        samples[unit]
                    )

        report["timing_summary"] = {}
        for arm in arms:
            name = arm["name"]
            report["timing_summary"][name] = {
                "seconds": summary(report["timing_samples"][name]["seconds"]),
                "cycles": summary(report["timing_samples"][name]["cycles"]),
            }
        report["resources_after"] = resources(target)
        if target.transaction(4, word(2), 4, 0) != 0:
            raise AssertionError("final module slot not empty")
        report["passed"] = True
    except BaseException as error:
        report["failure"] = f"{type(error).__name__}: {error}"
        raise
    finally:
        if target is not None:
            try:
                stats = target.close()
                report["execution_stats"] = stats
                if report["passed"] and any(
                    stats.get(key) for key in
                    ("failed", "unhandled", "unregistered", "unmapped")
                ):
                    report["passed"] = False
                    report["failure"] = f"backend fault counters: {stats}"
            except BaseException as close_error:
                report["passed"] = False
                report["close_failure"] = (
                    f"{type(close_error).__name__}: {close_error}"
                )
            report["outbound_bytes"] = target.sent
            report["reply_bytes"] = len(target.observed)
        report["elapsed_seconds"] = round(time.monotonic() - started, 3)
        report["qualifier_sha256"] = hashlib.sha256(
            Path(__file__).read_bytes()
        ).hexdigest()
        (output / "evidence.json").write_text(
            json.dumps(report, indent=2) + "\n"
        )
    if not report["passed"]:
        raise RuntimeError(report.get("failure", report.get("close_failure")))
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine", choices=("jit", "interp"), required=True)
    parser.add_argument("--firmware", type=Path, required=True)
    parser.add_argument("--backend", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--rounds", type=int, default=6)
    parser.add_argument("--runs", type=int, default=5)
    parser.add_argument("--timeout", type=float, default=600)
    arguments = parser.parse_args()
    if arguments.rounds <= 0 or arguments.runs <= 0:
        parser.error("rounds and runs must be positive")
    result = qualify(arguments)
    print(json.dumps({
        "passed": result["passed"],
        "engine": result["engine"],
        "capabilities": result["capabilities"],
        "timing_summary": result["timing_summary"],
        "elapsed_seconds": result["elapsed_seconds"],
    }, indent=2))


if __name__ == "__main__":
    main()
