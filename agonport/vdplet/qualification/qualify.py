#!/usr/bin/env python3
"""Run the bounded Wolf scene through an actual uploaded Xtensa VDPlet."""

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
CONFIG_ID = 0x7103


def rgb222_frame(values: bytes) -> bytes:
    output = bytearray(len(values) * 3)
    at = 0
    for value in values:
        output[at] = (value & 3) * 85
        output[at + 1] = ((value >> 2) & 3) * 85
        output[at + 2] = ((value >> 4) & 3) * 85
        at += 3
    return bytes(output)


def ppm(path: Path, width: int, height: int, pixels: bytes) -> None:
    path.write_bytes(f"P6\n{width} {height}\n255\n".encode() + pixels)


def qualify(engine: str, firmware: Path, backend: Path, timeout: float) -> dict:
    output = BUILD / f"target-{engine}"
    target = Target(engine, output, backend, firmware, timeout)
    report = {
        "scope": "actual uploaded Xtensa module and decoded VGA; no physical claim",
        "engine": engine,
        "firmware_sha256": sha(firmware),
        "firmware_elf_sha256": sha(firmware.with_suffix(".elf")),
        "adapter_sha256": sha(backend),
        "module_sha256": sha(MODULE),
        "checks": [],
        "passed": False,
    }
    handle = 0
    try:
        capabilities = target.transaction(4, word(1), 4)
        if capabilities & 17 != 17:
            raise AssertionError(f"runtime capabilities {capabilities} lack mask17")
        report["capabilities"] = capabilities
        report["checks"].append("capability subset17")

        target.send(bytes((22, 136, 23, 1, 0, 23, 0, 192, 0, 26, 12)))
        target.barrier()
        width, height, baseline = target.capture()
        if (width, height) != (320, 240):
            raise AssertionError((width, height))

        handle = target.load(MODULE)
        for key, name in (
            (0x7100, "workspace.bin"),
            (0x7101, "map.bin"),
            (0x7102, "textures.bin"),
            (0x7103, "config.bin"),
        ):
            target.send(upload(key, (FIXTURE / name).read_bytes()))
        report["checks"].append("92160-byte consolidated workspace and scene upload")

        stack_before = target.transaction(4, word(17), 4)
        target.run(handle, 0, CONFIG_ID)
        cycles_before = target.lib.flexe_vdp_cycles()
        started = time.monotonic()
        target.run(handle, 1, CONFIG_ID)
        elapsed = time.monotonic() - started
        cycles_after = target.lib.flexe_vdp_cycles()
        stack_after = target.transaction(4, word(17), 4)

        if target.capture()[2] != baseline:
            raise AssertionError("hidden drawing surface became visible before C3")
        target.send(bytes((23, 0, 195)))
        actual_width, actual_height, actual = target.capture()
        expected = rgb222_frame((BUILD / "oracle-frame.bin").read_bytes())
        if (actual_width, actual_height) != (320, 240) or actual != expected:
            mismatch = next(
                (index // 3 for index, pair in enumerate(zip(actual, expected))
                 if pair[0] != pair[1]),
                -1,
            )
            raise AssertionError(f"decoded frame mismatch at pixel {mismatch}")
        ppm(output / "wolf3d-scene.ppm", 320, 240, actual)
        report["checks"].append("full hidden RGB222 frame, DONE fence, C3 and 76800-pixel parity")

        target.unload(handle)
        stale = handle
        handle = 0
        target.run(stale, 1, CONFIG_ID, expected=8)
        second = target.load(MODULE)
        target.unload(second)
        slot = target.transaction(4, word(2), 4, 0)
        report["checks"].append("unload, stale handle rejection, reload and empty slot")

        report.update(
            passed=True,
            frame_sha256=sha(BUILD / "oracle-frame.bin"),
            frame_pixels=76800,
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
        (BUILD / f"target-{engine}-evidence.json").write_text(
            json.dumps(report, indent=2) + "\n"
        )
        if report["passed"] and any(
            stats.get(key) for key in ("failed", "unhandled", "unregistered", "unmapped")
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
            "passed", "engine", "render_reply_seconds", "render_vdp_cycles",
            "stack_free_after", "elapsed_seconds"
        )
    }, indent=2))
