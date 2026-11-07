#!/usr/bin/env python3
"""Decode optional full-game WOLFPROF.BIN records; never call fences scanout."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import statistics
import struct

MODULUS = 1 << 24
RECORD_BYTES = 64
HEADER_BYTES = 32


class ProfileError(ValueError):
    pass


def u24(data: bytes, at: int) -> int:
    return int.from_bytes(data[at:at + 3], "little")


def delta(end: int, start: int) -> int:
    value = (end - start) % MODULUS
    if value >= MODULUS // 2:
        raise ProfileError("ambiguous/reversed 24-bit clock interval")
    return value


def summary(values: list[int | float]) -> dict:
    if not values:
        return {"count": 0}
    ordered = sorted(values)
    return {"count": len(values), "mean": statistics.mean(values),
            "median": statistics.median(values),
            "p95": ordered[min(len(ordered) - 1, (len(ordered) * 95 - 1) // 100)],
            "max": max(values)}


def decode(data: bytes, *, salvage: bool = False) -> dict:
    blocks, frames, gaps, warnings = [], [], [], []
    at, expected_block = 0, 0
    stages = {k: [] for k in ("prepare_submit_ms", "prepare_callback_ms",
                             "callback_consume_ms", "presentation_fence_ms",
                             "prepare_fence_ms", "input_service_gap_ms")}
    draw, scope, dispatch, intervals = [], [], [], []
    wall_intervals = []
    previous = None
    while at < len(data):
        try:
            if len(data) - at < HEADER_BYTES:
                raise ProfileError("truncated block header")
            h = data[at:at + HEADER_BYTES]
            if h[:4] != b"WPF1" or h[4] != 1:
                raise ProfileError("unknown profile magic/version")
            if h[5] not in (0, 1) or h[6] != 1 or h[7] & 0x0e:
                raise ProfileError("unsupported backend/clock/header flags")
            count, size, number = struct.unpack_from("<HHI", h, 8)
            if not 0 < count <= 128 or size != RECORD_BYTES or number != expected_block:
                raise ProfileError("invalid count/record size/block sequence")
            end = at + HEADER_BYTES + count * size
            if end > len(data):
                raise ProfileError("truncated record block")
            gap = None
            if number:
                g = struct.unpack_from("<IIII", h, 16)
                if any(v >= MODULUS for v in g):
                    raise ProfileError("logging gap timestamps exceed 24 bits")
                gap = {"start": g[0], "end": g[1], "io_start": g[2],
                       "io_end": g[3], "total_ms": delta(g[1], g[0]),
                       "disk_ms": delta(g[3], g[2])}
            batch = []
            for i in range(count):
                r = data[at + HEADER_BYTES + i * size:at + HEADER_BYTES + (i + 1) * size]
                flags = r[42]
                if r[43] or flags & ~0x3f or flags & 0x1c != 0x1c:
                    raise ProfileError("unknown flags or incomplete frame record")
                if r[44] != h[5] or r[59] != i:
                    raise ProfileError("backend/native index join failed")
                native = bool(flags & 2)
                if native != bool(h[7] & 1):
                    raise ProfileError("native availability differs from header")
                t = [u24(r, pos) for pos in (3, 6, 9, 12, 15, 18)]
                # IRQ completion may precede return from the synchronous sender.
                # Do not demand submitted <= callback for a very short render.
                for a, b in ((1, 0), (2, 0), (3, 1), (3, 2), (4, 3), (5, 4)):
                    delta(t[a], t[b])
                angle = int.from_bytes(r[46:48], "little")
                if angle >= 360 or not u24(r, 0):
                    raise ProfileError("invalid pose angle/frame identity")
                f = {"id": u24(r, 0), "prepare": t[0], "submitted": t[1],
                     "callback": t[2], "consumed": t[3], "present_send_return": t[4],
                     "fence": t[5], "logging_cue": bool(flags & 1),
                     "session_start": bool(flags & 0x20),
                     "max_input_service_gap_ms": u24(r, 21),
                     "cumulative_input_simulation_ms": u24(r, 24),
                     "simulation_credit_ticks": u24(r, 27), "purpose": r[45],
                     "angle": angle, "x": struct.unpack_from("<i", r, 48)[0],
                     "y": struct.unpack_from("<i", r, 52)[0],
                     "discarded_attempts": u24(r, 56), "native": None}
                if native:
                    c = struct.unpack_from("<III", r, 30)
                    if not c[0] or c[1] < c[0] or c[2] < c[1]:
                        raise ProfileError("invalid nested native timing intervals")
                    f["native"] = {"render_cycles": c[0], "scope_cycles": c[1],
                                   "dispatch_cycles": c[2],
                                   "prid": struct.unpack_from("<I", r, 60)[0]}
                elif any(r[30:42]) or any(r[60:64]):
                    raise ProfileError("unavailable native fields are not zero")
                batch.append(f)
            prior = previous
            for f in batch:
                if prior and not f["session_start"]:
                    delta(f["fence"], prior["fence"])
                prior = f
            # Publish only complete, validated blocks when salvaging a torn tail.
            for i, f in enumerate(batch):
                stages["prepare_submit_ms"].append(delta(f["submitted"], f["prepare"]))
                stages["prepare_callback_ms"].append(delta(f["callback"], f["prepare"]))
                stages["callback_consume_ms"].append(delta(f["consumed"], f["callback"]))
                stages["input_service_gap_ms"].append(f["max_input_service_gap_ms"])
                if not f["logging_cue"]:
                    stages["presentation_fence_ms"].append(delta(f["fence"], f["consumed"]))
                    stages["prepare_fence_ms"].append(delta(f["fence"], f["prepare"]))
                if f["native"]:
                    draw.append(f["native"]["render_cycles"] / 240000)
                    scope.append(f["native"]["scope_cycles"] / 240000)
                    dispatch.append(f["native"]["dispatch_cycles"] / 240000)
                if previous and not f["session_start"]:
                    wall = delta(f["fence"], previous["fence"])
                    wall_intervals.append(wall)
                    # Never bridge a flush, cue, failed attempt or game session.
                    if i and not (previous["logging_cue"] or f["logging_cue"]) and (
                            f["id"] - previous["id"]) % MODULUS == 1:
                        intervals.append(wall)
                previous = f
            if gap:
                gaps.append(gap)
            blocks.append({"number": number, "frames": count, "status": h[7] >> 4})
            frames.extend(batch)
            at, expected_block = end, expected_block + 1
        except ProfileError as exc:
            if not salvage:
                raise ProfileError(f"at byte {at}: {exc}") from exc
            warnings.append(f"Stopped at byte {at}: {exc}; incomplete block excluded")
            break
    if not frames:
        raise ProfileError("no complete profile blocks")
    def rate(samples):
        return len(samples) * 1000 / sum(samples) if samples and sum(samples) else None
    return {"format": "WPF1", "complete_blocks": blocks, "completed_frame_records": len(frames),
            "stage_nominal_ms": {k: summary(v) for k, v in stages.items()},
            "native_at_nominal_240MHz_ms": {"draw": summary(draw), "scope": summary(scope),
                                           "dispatch": summary(dispatch)},
            "logging_excluded_fence_intervals_ms": summary(intervals),
            "logging_excluded_fence_rate": rate(intervals),
            "observed_fence_intervals_including_logging_ms": summary(wall_intervals),
            "observed_fence_rate_including_logging": rate(wall_intervals),
            "closed_logging_gaps": gaps, "terminal_logging_gap": "end not yet in a subsequent block",
            "discarded_attempts": max(f["discarded_attempts"] for f in frames),
            "warnings": warnings, "sha256": hashlib.sha256(data).hexdigest(),
            "limits": "Nominal 1ms interrupt clock; native cycles include preemption. "
                      "Ordered fence completions, not optical frame/scanout timestamps. "
                      "Instrumented throughput includes timer/hook/fence overhead. "
                      "Logging-excluded rate uses only contiguous within-block intervals; "
                      "logging still affects play and subsequent catch-up/cache behavior.",
            "frames": frames}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", type=Path)
    parser.add_argument("--salvage", action="store_true",
                        help="report only complete blocks before a torn/corrupt tail")
    parser.add_argument("--frames", action="store_true", help="include individual frame records")
    args = parser.parse_args()
    try:
        result = decode(args.file.read_bytes(), salvage=args.salvage)
    except (OSError, ProfileError) as exc:
        parser.exit(2, f"profile decode failed: {exc}\n")
    if not args.frames:
        result.pop("frames")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
