"""Read the existing weapon frames from verified local game payloads."""

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "agonport/tools/wolf3d_assets/scripts"))
from view_agnb import parse_container  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("payload", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    payload = json.loads((args.payload / "payload.json").read_text())
    assets = {}
    sources = {}
    weapon_ids = range(416, 436)  # The four five-frame blocks in player_combat.inc.
    wanted = {0x2000 + shape for shape in weapon_ids}
    for level in range(10):
        relative = f"level_{level:02d}/sprites.agnb"
        data, records = parse_container(args.payload / relative)
        digest = hashlib.sha256(data).hexdigest()
        if digest != payload["files"][relative]["sha256"]:
            raise ValueError(f"Payload hash differs for {relative}")
        sources[relative] = digest
        matching = {record.bufferId for record in records} & wanted
        if matching != wanted:
            raise ValueError(f"Incomplete weapon inventory in {relative}")
        for record in records:
            if record.bufferId not in wanted:
                continue
            if (record.width, record.height) != (64, 64):
                raise ValueError(f"Unexpected shape size for {record.bufferId:#x}")
            start = record.dataOffset
            pixels = data[start:start + record.dataSize]
            if assets.setdefault(record.bufferId, pixels) != pixels:
                raise ValueError(f"Weapon frame differs in {relative}")

    args.output.write_bytes(b"".join(assets[0x2000 + shape] for shape in weapon_ids))
    print(json.dumps({"shapes": list(weapon_ids), "inputs": sources,
                      "frames_sha256": hashlib.sha256(args.output.read_bytes()).hexdigest()},
                     indent=2))


if __name__ == "__main__":
    main()
