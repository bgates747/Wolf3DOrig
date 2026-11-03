#!/usr/bin/env python3
"""Assemble a named Wolf3D renderer backend without editing tracked source."""

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
SOURCE = PROJECT / "src"
TARGET = PROJECT / "tgt"
SELECTOR = "W3D_RENDER_BACKEND:"
START_SELECTOR = "W3D_INITIAL_LEVEL:"
INVULNERABLE_SELECTOR = "W3D_DIAGNOSTIC_INVULNERABLE:"
HIGHSCORE_SELECTOR = "W3D_DIAGNOSTIC_HIGHSCORE_MODE:"
START_HEALTH_SELECTOR = "W3D_DIAGNOSTIC_START_HEALTH:"
START_LIVES_SELECTOR = "W3D_DIAGNOSTIC_START_LIVES:"
HIGHSCORE_MODES = {"none": 0, "qualifying": 1, "nonqualifying": 2}
BACKENDS = {
    "standalone": "W3D_RENDER_BACKEND_STANDALONE",
    "vdplet-direct": "W3D_RENDER_BACKEND_VDPLET_DIRECT",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def assembler_works(candidate: Path) -> bool:
    try:
        result = subprocess.run(
            [str(candidate), "-v"], capture_output=True, text=True, check=False
        )
    except OSError:
        return False
    return result.returncode == 0 and "ez80asm version" in result.stdout


def build_local_assembler() -> Path:
    source_root = Path("/Agon/agon-ez80asm/src")
    sources = sorted(source_root.glob("*.c"))
    if not sources:
        raise SystemExit(f"ez80asm source not found: {source_root}")
    destination = TARGET / ".tools/ez80asm"
    destination.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "gcc", "-g", "-Wall", "-DUNIX", "-O2", "-DNDEBUG",
            "-Wno-unused-result", "-fno-common",
            *(str(path) for path in sources), "-o", str(destination),
        ],
        check=True,
    )
    if not assembler_works(destination):
        raise SystemExit(f"locally built ez80asm is not executable: {destination}")
    return destination


def resolve_assembler(value: Path | None) -> Path:
    if value is not None:
        candidate = value.expanduser().resolve()
    else:
        installed = shutil.which("ez80asm")
        candidate = (
            Path(installed).resolve()
            if installed
            else Path("/Agon/agon-ez80asm/bin/ez80asm")
        )
    if candidate.is_file() and assembler_works(candidate):
        return candidate
    if value is not None:
        raise SystemExit(f"ez80asm is missing or incompatible: {candidate}")
    return build_local_assembler()


def select_backend(path: Path, backend: str) -> None:
    lines = path.read_text().splitlines()
    matches = [index for index, line in enumerate(lines) if line.startswith(SELECTOR)]
    if matches != [5]:
        raise SystemExit("wolf3d_backend.inc selector layout changed")
    lines[matches[0]] = (
        f"W3D_RENDER_BACKEND:            equ {BACKENDS[backend]}"
    )
    path.write_text("\n".join(lines) + "\n")


def select_package(path: Path, size: int) -> None:
    lines = path.read_text().splitlines()
    matches = [
        index for index, line in enumerate(lines)
        if line.startswith("W3D_VDPLET_PACKAGE_BYTES:")
    ]
    if matches != [3]:
        raise SystemExit("wolf3d_vdplet_package.inc selector layout changed")
    lines[matches[0]] = f"W3D_VDPLET_PACKAGE_BYTES: equ {size}"
    path.write_text("\n".join(lines) + "\n")


def select_initial_level(path: Path, level: int) -> None:
    if not 0 <= level <= 9:
        raise SystemExit("initial level must be in 0..9")
    lines = path.read_text().splitlines()
    matches = [
        index for index, line in enumerate(lines)
        if line.startswith(START_SELECTOR)
    ]
    if matches != [3]:
        raise SystemExit("wolf3d_start.inc selector layout changed")
    lines[matches[0]] = f"W3D_INITIAL_LEVEL: equ {level}"
    path.write_text("\n".join(lines) + "\n")


def select_invulnerable(path: Path, enabled: bool) -> None:
    lines = path.read_text().splitlines()
    matches = [
        index for index, line in enumerate(lines)
        if line.startswith(INVULNERABLE_SELECTOR)
    ]
    if len(matches) != 1:
        raise SystemExit("wolf3d diagnostic-invulnerability selector changed")
    lines[matches[0]] = (
        f"W3D_DIAGNOSTIC_INVULNERABLE: equ {int(enabled)}"
    )
    path.write_text("\n".join(lines) + "\n")


def select_highscore_mode(path: Path, mode: str) -> None:
    lines = path.read_text().splitlines()
    matches = [
        index for index, line in enumerate(lines)
        if line.startswith(HIGHSCORE_SELECTOR)
    ]
    if len(matches) != 1:
        raise SystemExit("wolf3d diagnostic-high-score selector changed")
    lines[matches[0]] = (
        f"W3D_DIAGNOSTIC_HIGHSCORE_MODE: equ {HIGHSCORE_MODES[mode]}"
    )
    path.write_text("\n".join(lines) + "\n")


def select_starting_player_state(
    path: Path, health: int | None, lives: int | None
) -> None:
    if health is not None and not 0 <= health <= 100:
        raise SystemExit("diagnostic starting health must be in 0..100")
    if lives is not None and not 0 <= lives <= 9:
        raise SystemExit("diagnostic starting lives must be in 0..9")
    lines = path.read_text().splitlines()
    for selector, value, label in (
        (START_HEALTH_SELECTOR, health, "health"),
        (START_LIVES_SELECTOR, lives, "lives"),
    ):
        matches = [
            index for index, line in enumerate(lines)
            if line.startswith(selector)
        ]
        if len(matches) != 1:
            raise SystemExit(f"wolf3d diagnostic-start-{label} selector changed")
        lines[matches[0]] = (
            f"{selector} equ {0xff if value is None else value}"
        )
    path.write_text("\n".join(lines) + "\n")


def build(
    assembler: Path,
    backend: str,
    module: Path | None,
    initial_level: int = 0,
    invulnerable: bool = False,
    highscore_mode: str = "none",
    start_health: int | None = None,
    start_lives: int | None = None,
) -> dict[str, object]:
    if backend == "vdplet-direct":
        if module is None:
            raise SystemExit(
                "--backend vdplet-direct requires --module PACKAGE.vdpl"
            )
        module = module.expanduser().resolve()
        if not module.is_file():
            raise SystemExit(f"VDPlet package not found: {module}")
        if not 0 < module.stat().st_size < 0x20000:
            raise SystemExit("VDPlet package must be 1..131071 bytes")
    elif module is not None:
        raise SystemExit("--module is valid only with --backend vdplet-direct")

    TARGET.mkdir(parents=True, exist_ok=True)
    if not 0 <= initial_level <= 9:
        raise SystemExit("initial level must be in 0..9")
    base_name = "wolf3d" if backend == "standalone" else f"wolf3d-{backend}"
    # ez80asm retains a DOS-era output-filename ceiling. Keep diagnostic
    # suffixes compact even though their surrounding manifests are descriptive.
    suffix = "" if initial_level == 0 else f"-l{initial_level:02d}"
    output_name = f"{base_name}{suffix}.bin"
    output = TARGET / output_name
    with tempfile.TemporaryDirectory(prefix="w3b") as name:
        temporary = Path(name)
        source = temporary / "src"
        shutil.copytree(SOURCE, source)
        select_backend(source / "wolf3d_backend.inc", backend)
        select_initial_level(source / "wolf3d_start.inc", initial_level)
        select_invulnerable(source / "wolf3d_backend.inc", invulnerable)
        select_highscore_mode(source / "wolf3d_backend.inc", highscore_mode)
        select_starting_player_state(
            source / "wolf3d_backend.inc", start_health, start_lives
        )
        if module is not None:
            select_package(source / "wolf3d_vdplet_package.inc", module.stat().st_size)
        temporary_output = temporary / output_name
        subprocess.run(
            [str(assembler), "wolf3d.asm", str(temporary_output), "-l", "-c"],
            cwd=source,
            check=True,
        )
        shutil.copyfile(temporary_output, output)
        listing = temporary_output.with_suffix(".lst")
        if listing.is_file():
            shutil.copyfile(listing, output.with_suffix(".lst"))

    receipt = {
        "backend": backend,
        "initial_level": initial_level,
        "diagnostic_invulnerable": invulnerable,
        "diagnostic_highscore_mode": highscore_mode,
        "diagnostic_start_health": start_health,
        "diagnostic_start_lives": start_lives,
        "assembler": str(assembler),
        "output": str(output.relative_to(PROJECT.parents[2])),
        "bytes": output.stat().st_size,
        "sha256": sha256(output),
    }
    if module is not None:
        packaged_module = TARGET / "wolf3d.vdpl"
        # A previously packaged module is a valid explicit input for a fresh
        # application build. Avoid SameFileError when source and destination
        # are already the canonical target artifact.
        if module != packaged_module.resolve():
            shutil.copyfile(module, packaged_module)
        receipt["module"] = {
            "source": str(module),
            "output": str(packaged_module.relative_to(PROJECT.parents[2])),
            "bytes": packaged_module.stat().st_size,
            "sha256": sha256(packaged_module),
        }
    receipt_path = TARGET / f"{output.stem}.json"
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n")
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend", choices=tuple(BACKENDS), default="standalone")
    parser.add_argument("--assembler", type=Path)
    parser.add_argument("--module", type=Path)
    parser.add_argument("--initial-level", type=int, default=0)
    parser.add_argument(
        "--invulnerable", action="store_true",
        help="acceptance-only build: record attacks but suppress player damage",
    )
    parser.add_argument(
        "--highscore-acceptance", choices=tuple(HIGHSCORE_MODES), default="none",
        help="acceptance-only build: enter a qualifying or non-qualifying score flow",
    )
    parser.add_argument(
        "--diagnostic-start-health", type=int,
        help="acceptance-only build: override new-game starting health (0..100)",
    )
    parser.add_argument(
        "--diagnostic-start-lives", type=int,
        help="acceptance-only build: override new-game starting lives (0..9)",
    )
    args = parser.parse_args()
    receipt = build(
        resolve_assembler(args.assembler),
        args.backend,
        args.module,
        args.initial_level,
        args.invulnerable,
        args.highscore_acceptance,
        args.diagnostic_start_health,
        args.diagnostic_start_lives,
    )
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
