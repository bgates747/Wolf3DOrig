#!/usr/bin/env python3
"""Build and package the complete production-VDPlet Wolf3D application."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[3]
GAME = PROJECT / "src/asm/wolf3d"
PRODUCTION = PROJECT / "agonport/vdplet/production/build"
GENERATED = PROJECT / "agonport/assets/generated/wolf3d"
ASSET_SCRIPTS = PROJECT / "agonport/tools/wolf3d_assets/scripts"
TARGET = HERE.parent / "tgt/package"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(path: Path) -> Path:
    if not path.is_file() or path.stat().st_size == 0:
        raise SystemExit(f"missing or empty required file: {path}")
    return path


def main() -> None:
    # The generated level-state tree is mutable and has historically been
    # rebuilt with a diagnostic E1L1 elevator spawn.  A production package
    # must never inherit that ambient experiment, so always regenerate the
    # ten standard map/difficulty states with the builder's default contract.
    subprocess.run(
        [sys.executable, str(ASSET_SCRIPTS / "build_level_packages.py")],
        cwd=PROJECT,
        check=True,
    )
    module = require(PRODUCTION / "wolf3d_production.vdpl")
    subprocess.run(
        [
            sys.executable,
            str(GAME / "scripts/build.py"),
            "--backend", "vdplet-direct",
            "--module", str(module),
        ],
        cwd=PROJECT,
        check=True,
    )

    sources: list[tuple[Path, Path]] = [
        (require(GAME / "tgt/wolf3d-vdplet-direct.bin"), Path("wolf3d.bin")),
        (require(GAME / "tgt/wolf3d.vdpl"), Path("wolf3d.vdpl")),
        (require(GENERATED / "hud/hud.agnb"), Path("hud.agnb")),
        (require(GENERATED / "audio/sfx.agnb"), Path("sfx.agnb")),
        (require(GENERATED / "shell/shell.agnb"), Path("shell.agnb")),
        (require(GENERATED / "shell/help.agnb"), Path("help.agnb")),
        (require(GENERATED / "shell/end.agnb"), Path("end.agnb")),
    ]
    level_names = (
        "tiles.agnb", "sprites.agnb", "state_baby.w3l", "state_easy.w3l",
        "state_medium.w3l", "state_hard.w3l",
    )
    for index in range(10):
        source = GENERATED / f"levels/level_{index:02d}"
        for name in level_names:
            sources.append((require(source / name), Path(source.name) / name))

    TARGET.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="wolf3d-vdplet-package-",
                                     dir=TARGET.parent) as temporary_name:
        temporary = Path(temporary_name)
        for source, relative in sources:
            destination = temporary / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
        receipt = {
            "scope": "complete stopped Wolf3DOrig production-VDPlet payload",
            "backend": "vdplet-direct",
            "module_sha256": sha(temporary / "wolf3d.vdpl"),
            "application_sha256": sha(temporary / "wolf3d.bin"),
            "files": {
                str(path.relative_to(temporary)): {
                    "bytes": path.stat().st_size,
                    "sha256": sha(path),
                }
                for path in sorted(temporary.rglob("*")) if path.is_file()
            },
        }
        (temporary / "expected.json").write_text(
            json.dumps(receipt, indent=2) + "\n"
        )
        if TARGET.exists():
            shutil.rmtree(TARGET)
        temporary.rename(TARGET)

    print(json.dumps({
        "package": str(TARGET),
        "files": len(sources) + 1,
        "bytes": sum(path.stat().st_size for path in TARGET.rglob("*")
                     if path.is_file()),
        "application_sha256": sha(TARGET / "wolf3d.bin"),
        "module_sha256": sha(TARGET / "wolf3d.vdpl"),
    }, indent=2))


if __name__ == "__main__":
    main()
