#!/usr/bin/env python3
"""Run the finite original-parity direct-eZ80 emulator batch sequentially."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
PRODUCTION = ROOT / "src/asm/wolf3d/src"

RUNNERS = (
    ROOT / "src/asm/wolf3d_shell/scripts/run_shell_emulator_regression.py",
    ROOT / "src/asm/wolf3d_highscores/scripts/run_highscores_emulator_regression.py",
    ROOT / "src/asm/wolf3d_intermission/scripts/run_intermission_emulator_regression.py",
    ROOT / "src/asm/wolf3d_gameplay/scripts/run_victory_emulator_regression.py",
    ROOT / "src/asm/wolf3d_save/scripts/run_save_emulator_regression.py",
    ROOT / "src/asm/wolf3d_demo/scripts/run_demo_emulator_regression.py",
)


def tree_hash(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        relative = path.relative_to(root).as_posix().encode()
        digest.update(len(relative).to_bytes(4, "little"))
        digest.update(relative)
        payload = path.read_bytes()
        digest.update(len(payload).to_bytes(8, "little"))
        digest.update(payload)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timeout", type=float, default=45.0)
    parser.add_argument("--result", type=Path, default=Path("batch-result.json"))
    args = parser.parse_args()

    missing = [path for path in (PRODUCTION, *RUNNERS) if not path.exists()]
    if missing:
        raise FileNotFoundError(f"missing staged parity inputs: {missing}")

    receipt: dict[str, object] = {
        "schema": "wolf3d-original-parity-direct-batch-v1",
        "started": datetime.now(timezone.utc).isoformat(),
        "root": str(ROOT),
        "production_source_sha256": tree_hash(PRODUCTION),
        "tests": [],
    }
    failed = False
    tests = receipt["tests"]
    assert isinstance(tests, list)
    for runner in RUNNERS:
        command = [sys.executable, str(runner), "--timeout", str(args.timeout)]
        print("+", " ".join(command), flush=True)
        completed = subprocess.run(command, text=True, capture_output=True)
        if completed.stdout:
            print(completed.stdout, end="")
        if completed.stderr:
            print(completed.stderr, end="", file=sys.stderr)
        tests.append({
            "runner": str(runner.relative_to(ROOT)),
            "runner_sha256": hashlib.sha256(runner.read_bytes()).hexdigest(),
            "command": command,
            "returncode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        })
        failed |= completed.returncode != 0

    receipt["finished"] = datetime.now(timezone.utc).isoformat()
    receipt["passed"] = not failed
    args.result.write_text(json.dumps(receipt, indent=2) + "\n")
    print(f"{'PASS' if not failed else 'FAIL'}: receipt {args.result}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
