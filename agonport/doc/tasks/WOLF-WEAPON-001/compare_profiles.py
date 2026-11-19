"""Report ordered presentation rates for the matched uncapped timing arms."""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "src/asm/wolf3d/scripts"))
from decode_profile import decode, delta, summary  # noqa: E402


def describe(path):
    report = decode(path.read_bytes())
    frames = report["frames"]
    if sum(frame["session_start"] for frame in frames) != 1:
        raise ValueError(f"Expected one completed demo in {path}")
    if report["discarded_attempts"] or any(block["status"] for block in report["complete_blocks"]):
        raise ValueError(f"The recorded demo did not complete cleanly in {path}")
    starts = block_starts(report["complete_blocks"], frames[0]["id"])
    intervals = []
    poses = 0
    for previous, current in zip(frames, frames[1:]):
        if current["id"] != previous["id"] + 1:
            raise ValueError(f"Gap in frame IDs in {path}")
        if (current["purpose"] or previous["purpose"] or
                current["logging_cue"] or previous["logging_cue"] or
                current["id"] in starts):
            continue
        intervals.append(delta(current["fence"], previous["fence"]))
        poses += any(previous[key] != current[key] for key in ("x", "y", "angle"))
    elapsed = sum(intervals)
    if not elapsed:
        raise ValueError(f"No comparable steady-state intervals in {path}")
    return {"ordered_presentation_fps": 1000 * len(intervals) / elapsed,
            "camera_pose_change_rate": 1000 * poses / elapsed,
            "interval_ms": summary(intervals), "recorded_frames": len(frames),
            "profile_sha256": report["sha256"]}


def block_starts(blocks, first):
    ids = set()
    for block in blocks:
        ids.add(first)
        first += block["frames"]
    return ids


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline", type=Path)
    parser.add_argument("cropped", type=Path)
    args = parser.parse_args()
    baseline, cropped = describe(args.baseline), describe(args.cropped)
    ratio = cropped["ordered_presentation_fps"] / baseline["ordered_presentation_fps"]
    print(json.dumps({"baseline": baseline, "cropped": cropped,
                      "fps_delta_percent": 100 * (ratio - 1),
                      "timing": "ordered C3 fences, nominal PRT milliseconds, outside SD logging gaps"},
                     indent=2))


if __name__ == "__main__":
    main()
