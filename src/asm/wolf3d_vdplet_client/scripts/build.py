#!/usr/bin/env python3
"""Build the finite production-client/copy-pixel integration fixture."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile


HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent
REPO = HERE.parents[3]
PRODUCTION = REPO / "src/asm/wolf3d/src"
QUALIFICATION = REPO / "agonport/vdplet/qualification/build"
REVIEW_PACKAGE = REPO / "agonport/vdplet/review/build/package"
TARGET = PROJECT / "tgt/pinned"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--assembler",
        type=Path,
        default=REPO / "src/asm/wolf3d/tgt/.tools/ez80asm",
    )
    args = parser.parse_args()
    assembler = args.assembler.expanduser().resolve()
    required = {
        "module": QUALIFICATION / "wolf3d_scene.vdpl",
        "workspace": QUALIFICATION / "fixture/workspace.bin",
        "map": QUALIFICATION / "fixture/map.bin",
        "textures": QUALIFICATION / "fixture/textures.bin",
        "config": QUALIFICATION / "fixture/config.bin",
        "client": PRODUCTION / "wolf3d_vdplet_client.inc",
        "entry": PROJECT / "src/client_regression.asm",
        "assembler": assembler,
        "reference_ppm": REVIEW_PACKAGE / "reference.ppm",
        "reference_png": REVIEW_PACKAGE / "reference.png",
    }
    missing = [str(path) for path in required.values() if not path.is_file()]
    if missing:
        raise SystemExit("missing client fixture inputs:\n" + "\n".join(missing))

    TARGET.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="wolf-vdpl-client-") as name:
        build = Path(name)
        shutil.copyfile(required["entry"], build / "client_regression.asm")
        shutil.copyfile(required["client"], build / "wolf3d_vdplet_client.inc")
        (build / "wolf3d_vdplet_package.inc").write_text(
            f"W3D_VDPLET_PACKAGE_BYTES: equ {required['module'].stat().st_size}\n"
        )
        storage_bytes = max(4096, *(required[key].stat().st_size
                            for key in ("module", "workspace", "map", "textures", "config")))
        (build / "fixture_storage.bin").write_bytes(bytes(storage_bytes))
        (build / "fixture_sizes.inc").write_text(
            "\n".join(
                (
                    f"W3D_FIXTURE_STORAGE_BYTES: equ {storage_bytes}",
                    f"W3D_FIXTURE_WORKSPACE_BYTES: equ {required['workspace'].stat().st_size}",
                    f"W3D_FIXTURE_MAP_BYTES: equ {required['map'].stat().st_size}",
                    f"W3D_FIXTURE_TEXTURE_BYTES: equ {required['textures'].stat().st_size}",
                    f"W3D_FIXTURE_CONFIG_BYTES: equ {required['config'].stat().st_size}",
                )
            ) + "\n"
        )
        output = build / "client.bin"
        subprocess.run(
            [str(assembler), "client_regression.asm", str(output), "-l", "-c"],
            cwd=build,
            check=True,
        )
        shutil.copyfile(output, TARGET / "client.bin")
        listing = build / "client_regression.lst"
        if listing.is_file():
            import re
            raw = output.read_bytes()
            labels = {}
            for label in ('fixture_package_storage', 'fixture_package_storage_end'):
                values = re.findall(r'^([0-9A-F]{6})[^\n]*\b'+label+r':', listing.read_text(), re.M)
                if len(values) != 1:
                    raise SystemExit('Missing fixture storage label: '+label)
                labels[label] = int(values[0], 16)
            start, end = labels.values()
            if end-start != storage_bytes or not 0x40000 <= start < end == 0x40000+len(raw) < 0xa0000:
                raise SystemExit(f'Fixture staging extent invalid: {start:#x}..{end:#x}, '
                                 f'{storage_bytes} bytes, linked end {0x40000+len(raw):#x}')
            if raw[start-0x40000:end-0x40000] != bytes(storage_bytes):
                raise SystemExit('Fixture scratch contains live code/data')
            shutil.copyfile(listing, TARGET / "client.lst")
            shutil.copyfile(build / "fixture_storage.bin", TARGET / "fixture_storage.bin")
        else:
            raise SystemExit('Fixture package storage needs an actual listing')

    for key in ("module", "workspace", "map", "textures", "config"):
        destination = TARGET / (
            "wolf3d.vdpl" if key == "module" else required[key].name
        )
        shutil.copyfile(required[key], destination)

    receipt = {
        "scope": "stopped copied-pixel production-client integration fixture",
        "package_storage": dict(start=start, end=end, bytes=storage_bytes),
        "client": {
            "bytes": (TARGET / "client.bin").stat().st_size,
            "sha256": sha256(TARGET / "client.bin"),
        },
        "inputs": {
            key: {
                "bytes": (TARGET / ("wolf3d.vdpl" if key == "module" else required[key].name)).stat().st_size,
                "sha256": sha256(TARGET / ("wolf3d.vdpl" if key == "module" else required[key].name)),
            }
            for key in ("module", "workspace", "map", "textures", "config")
        },
    }

    package = TARGET / "package"
    shutil.rmtree(package, ignore_errors=True)
    (package / "source").mkdir(parents=True)
    package_inputs = {
        "client.bin": TARGET / "client.bin",
        "wolf3d.vdpl": TARGET / "wolf3d.vdpl",
        "workspace.bin": TARGET / "workspace.bin",
        "map.bin": TARGET / "map.bin",
        "textures.bin": TARGET / "textures.bin",
        "config.bin": TARGET / "config.bin",
        "reference.ppm": required["reference_ppm"],
        "reference.png": required["reference_png"],
        "README.md": PROJECT / "README.md",
        "gen31-failure-amendment.md": PROJECT / "gen31-failure-amendment.md",
        "readiness-addendum-r2.md": PROJECT / "readiness-addendum-r2.md",
        "gen33-unload-amendment.md": PROJECT / "gen33-unload-amendment.md",
        "gen33-diagnosis-r2.md": PROJECT / "gen33-diagnosis-r2.md",
        "readiness-addendum-r3.md": PROJECT / "readiness-addendum-r3.md",
        "readiness-addendum-r3-flag-audit.md": PROJECT / "readiness-addendum-r3-flag-audit.md",
        "readiness-addendum-r4.md": PROJECT / "readiness-addendum-r4.md",
        "source/client_regression.asm": required["entry"],
        "source/wolf3d_vdplet_client.inc": required["client"],
        "source/fixture_storage.bin": TARGET / "fixture_storage.bin",
    }
    for relative, source in package_inputs.items():
        destination = package / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
    receipt["package_files"] = {
        relative: {
            "bytes": (package / relative).stat().st_size,
            "sha256": sha256(package / relative),
        }
        for relative in sorted(package_inputs)
    }
    (package / "expected.json").write_text(json.dumps(receipt, indent=2) + "\n")
    (TARGET / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
