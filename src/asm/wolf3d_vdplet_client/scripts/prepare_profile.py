#!/usr/bin/env python3
"""Prepare a fresh stopped release-firmware finite-client profile; never run it."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / 'tools'))
from wolf_firmware import DEFAULT_CACHE
from wolf_prepare import profile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--payload', type=Path, required=True,
                        help='verified finite-client payload from tools/wolf_prepare.py fixture')
    parser.add_argument('--profile', type=Path, required=True,
                        help='new output directory; existing accepted profiles are preserved')
    parser.add_argument('--frontend', type=Path, required=True)
    parser.add_argument('--backend', type=Path, required=True)
    parser.add_argument('--cache', type=Path, default=DEFAULT_CACHE)
    args = parser.parse_args()
    print(json.dumps(profile(args.payload,args.profile,args.frontend,args.backend,args.cache),indent=2))


if __name__ == '__main__':
    try:
        main()
    except (ValueError,KeyError,FileNotFoundError) as exc:
        raise SystemExit('Preparation refused: '+str(exc))
