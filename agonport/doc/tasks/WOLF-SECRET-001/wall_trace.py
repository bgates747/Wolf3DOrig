"""Report pushwall records in an Alexe MOS-to-VDP capture."""
import argparse
import json
from pathlib import Path
import struct


def pushwall_records(wire):
    at = 0
    while (at := wire.find(b"W3DU\x02\x10", at)) >= 0:
        start = at
        at += 6
        if len(wire) - start < 16:
            break
        flags, size, count, generation, reserved = struct.unpack_from("<5H", wire, at)
        if not (16 <= size <= 7168 and flags <= 1 and generation and reserved == 0):
            continue
        end = start + size
        cursor = start + 16
        candidates = []
        for _ in range(count):
            if cursor + 2 > end:
                break
            kind, length = wire[cursor:cursor + 2]
            payload = wire[cursor + 2:cursor + 2 + length]
            if len(payload) == 89 and kind == 9:
                candidates.append({
                    "generation": generation,
                    "status": payload[0],
                    "origin": list(payload[1:3]),
                    "current": list(payload[3:5]),
                    "direction": payload[5],
                    "fraction": payload[6],
                    "texture": payload[7],
                    "completed_count": payload[8],
                })
            cursor += 2 + length
        else:
            if cursor == end and end <= len(wire):
                yield from candidates
                at = end


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("capture", type=Path)
    args = p.parse_args()
    print(json.dumps(list(pushwall_records(args.capture.read_bytes())), indent=2))
