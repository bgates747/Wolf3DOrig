#!/usr/bin/env python3
"""Build isolated, quickly reachable Wolf3D visual-acceptance payloads."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile


HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[3]
GAME = PROJECT / "src/asm/wolf3d"
TARGET = HERE.parent / "tgt"
GENERATED = PROJECT / "agonport/assets/generated/wolf3d"
MODULE = PROJECT / "agonport/vdplet/production/build/wolf3d_production.vdpl"
FORMAT_ROOT = PROJECT / "agonport/tools/wolf3d_assets"
sys.path.insert(0, str(FORMAT_ROOT))

from formats.level_package import ACTOR_SIZE, LevelPackage, build_package, parse_package  # noqa: E402
from agnb.container import BufferRecord, build_container  # noqa: E402
from agnb.manifest import ImageManifestEntry, buffer_id_for, KIND_SPRITE  # noqa: E402


TILE_GLOBAL = 1 << 16
ACTOR_ACTIVE_YES = 1
ACTOR_CLASS_GHOST = 15
ACTOR_FLAG_AMBUSH = 0x40
GHOST_STATES = (11, 12, 13, 14)
GHOST_SPEED = 1500
GHOST_SHAPES = (288, 289, 290, 291, 292, 293, 294, 295)
GHOST_COLORS = (0xC3, 0xCF, 0xF3, 0x3F)
LEVEL_FILES = (
    "tiles.agnb", "sprites.agnb", "state_baby.w3l", "state_easy.w3l",
    "state_medium.w3l", "state_hard.w3l",
)


@dataclass(frozen=True)
class Scenario:
    name: str
    initial_level: int
    player_tile: tuple[int, int]
    angle: int
    ghosts: bool = False
    one_hit_hans: bool = False
    invulnerable: bool = False


SCENARIOS = (
    Scenario("pushwall", 0, (10, 14), 90),
    Scenario("ordinary-transition", 0, (25, 47), 0),
    Scenario("secret-transition", 9, (45, 11), 180),
    Scenario(
        "hans", 8, (34, 17), 90,
        invulnerable=True,
    ),
    Scenario("victory", 8, (34, 8), 90),
    Scenario("ghosts", 9, (5, 34), 0, ghosts=True),
    Scenario("pause-resume", 0, (29, 57), 0),
)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(path: Path) -> Path:
    if not path.is_file() or path.stat().st_size == 0:
        raise SystemExit(f"missing or empty acceptance input: {path}")
    return path


def player_pose(tile: tuple[int, int], angle: int) -> bytes:
    x, y = tile
    return struct.pack(
        "<iiH",
        x * TILE_GLOBAL + TILE_GLOBAL // 2,
        y * TILE_GLOBAL + TILE_GLOBAL // 2,
        angle,
    )


def require_open(package: LevelPackage, tile: tuple[int, int]) -> None:
    x, y = tile
    if not (0 <= x < 64 and 0 <= y < 64):
        raise ValueError(f"acceptance tile is outside the map: {tile}")
    index = y * 64 + x
    if package.sections["tilemap"][index] != 0:
        raise ValueError(f"acceptance tile is not open floor: {tile}")
    blocking = package.sections["blocking"]
    if blocking[index >> 3] & (1 << (index & 7)):
        raise ValueError(f"acceptance tile contains a blocking static: {tile}")
    if package.sections["areas"][index] == 0xFF:
        raise ValueError(f"acceptance tile has no valid area: {tile}")


def inject_ghosts(package: LevelPackage) -> LevelPackage:
    ghost_tiles = ((8, 34), (10, 34), (12, 34), (14, 34))
    if package.actor_count < len(ghost_tiles):
        raise ValueError("ghost acceptance package has too few actor slots")
    actors = bytearray(package.sections["actors"])
    occupied = set()
    for index in range(len(ghost_tiles), package.actor_count):
        offset = index * ACTOR_SIZE
        x, y = struct.unpack_from("<ii", actors, offset)
        occupied.add((x >> 16, y >> 16))
    for index, (tile, state) in enumerate(zip(ghost_tiles, GHOST_STATES)):
        require_open(package, tile)
        if tile in occupied:
            raise ValueError(f"ghost acceptance tile contains another actor: {tile}")
        x, y = tile
        area = package.sections["areas"][y * 64 + x]
        offset = index * ACTOR_SIZE
        record = actors[offset : offset + ACTOR_SIZE]
        fixed_x = x * TILE_GLOBAL + TILE_GLOBAL // 2
        fixed_y = y * TILE_GLOBAL + TILE_GLOBAL // 2
        struct.pack_into("<ii", record, 0, fixed_x, fixed_y)
        record[8:15] = bytes((x, y, area, 0, ACTOR_ACTIVE_YES,
                              ACTOR_CLASS_GHOST, ACTOR_FLAG_AMBUSH))
        struct.pack_into("<H", record, 15, 1)
        struct.pack_into("<H", record, 17, state)
        struct.pack_into("<i", record, 19, 0)
        struct.pack_into("<h", record, 23, 0)
        struct.pack_into("<h", record, 25, 0)
        struct.pack_into("<i", record, 27, GHOST_SPEED)
        struct.pack_into("<hhh", record, 31, 0, 0, 0)
        actors[offset : offset + ACTOR_SIZE] = record
    sections = dict(package.sections)
    sections["actors"] = bytes(actors)
    return LevelPackage(
        level=package.level,
        difficulty=package.difficulty,
        door_count=package.door_count,
        static_count=package.static_count,
        actor_count=package.actor_count,
        random_index=package.random_index,
        player_pose=package.player_pose,
        sections=sections,
    )


def ghost_proxy_pixels(color: int, frame: int) -> bytes:
    """Return one unmistakably synthetic 64x64 diagnostic ghost sprite."""
    if not 0 <= frame <= 1:
        raise ValueError(f"ghost proxy frame must be zero or one: {frame}")
    pixels = bytearray(64 * 64)

    # Rounded head plus a broad body.  The alternating lower edge makes the
    # two walk frames visibly different without borrowing any paid artwork.
    for y in range(10, 49):
        for x in range(14, 50):
            dx = x - 31.5
            dy = y - 25
            in_head = dx * dx + dy * dy <= 17 * 17
            in_body = 15 <= x <= 48 and 25 <= y <= 46
            if in_head or in_body:
                pixels[y * 64 + x] = color
    for x in range(15, 49):
        wave = ((x // 6) + frame) & 1
        bottom = 50 if wave else 46
        for y in range(46, bottom + 1):
            pixels[y * 64 + x] = color

    # White eyes and opaque black pupils deliberately read as a test icon.
    pupil_shift = 1 if frame else 0
    for eye_x in (23, 36):
        for y in range(22, 30):
            for x in range(eye_x, eye_x + 7):
                pixels[y * 64 + x] = 0xFF
        for y in range(25, 29):
            for x in range(eye_x + 2 + pupil_shift, eye_x + 4 + pupil_shift):
                pixels[y * 64 + x] = 0x03
    return bytes(pixels)


def build_ghost_sprite_container(level_dir: Path, scratch: Path) -> None:
    """Add diagnostic proxies for shapes absent from shareware VSWAP.WL1."""
    manifest = GENERATED / "levels" / level_dir.name / "sprites.jsonl"
    entries = [
        ImageManifestEntry(**json.loads(line))
        for line in manifest.read_text().splitlines()
        if line.strip()
    ]
    existing_ids = {entry.assetId for entry in entries}
    overlap = existing_ids.intersection(GHOST_SHAPES)
    if overlap:
        raise ValueError(f"shareware manifest unexpectedly contains ghost art: {overlap}")

    records = [
        BufferRecord(
            name=entry.name,
            bufferId=entry.bufferId,
            width=entry.width,
            height=entry.height,
            rgba2File=GENERATED / "processed" / entry.rgba2,
            dataSize=entry.dataSize,
        )
        for entry in entries
    ]
    with tempfile.TemporaryDirectory(prefix="ghost-art-", dir=scratch) as name:
        proxy_dir = Path(name)
        for index, shape in enumerate(GHOST_SHAPES):
            proxy = proxy_dir / f"ghost_proxy_{shape}.rgba2"
            proxy.write_bytes(
                ghost_proxy_pixels(GHOST_COLORS[index // 2], index & 1)
            )
            records.append(BufferRecord(
                name=f"diagnostic_ghost_{shape}",
                bufferId=buffer_id_for(KIND_SPRITE, shape),
                width=64,
                height=64,
                rgba2File=proxy,
                dataSize=64 * 64,
            ))
        (level_dir / "sprites.agnb").write_bytes(build_container(records))


def make_hans_one_hit(package: LevelPackage) -> LevelPackage:
    actors = bytearray(package.sections["actors"])
    matches = []
    for index in range(package.actor_count):
        offset = index * ACTOR_SIZE
        if actors[offset + 13] == 7:
            matches.append(offset)
    if len(matches) != 1:
        raise ValueError(f"Hans fixture expected one boss actor, got {len(matches)}")
    struct.pack_into("<h", actors, matches[0] + 25, 1)
    sections = dict(package.sections)
    sections["actors"] = bytes(actors)
    return LevelPackage(
        level=package.level,
        difficulty=package.difficulty,
        door_count=package.door_count,
        static_count=package.static_count,
        actor_count=package.actor_count,
        random_index=package.random_index,
        player_pose=package.player_pose,
        sections=sections,
    )


def patch_state(data: bytes, scenario: Scenario) -> bytes:
    package = parse_package(data)
    if package.level != scenario.initial_level:
        raise ValueError(
            f"scenario {scenario.name} expected level {scenario.initial_level}, "
            f"got {package.level}"
        )
    require_open(package, scenario.player_tile)
    if scenario.ghosts:
        package = inject_ghosts(package)
    if scenario.one_hit_hans:
        package = make_hans_one_hit(package)
    package = LevelPackage(
        level=package.level,
        difficulty=package.difficulty,
        door_count=package.door_count,
        static_count=package.static_count,
        actor_count=package.actor_count,
        random_index=package.random_index,
        player_pose=player_pose(scenario.player_tile, scenario.angle),
        sections=package.sections,
    )
    return build_package(package)


def build_application(level: int, invulnerable: bool = False) -> Path:
    command = [
        sys.executable,
        str(GAME / "scripts/build.py"),
        "--backend", "vdplet-direct",
        "--module", str(require(MODULE)),
        "--initial-level", str(level),
    ]
    if invulnerable:
        command.append("--invulnerable")
    subprocess.run(command, cwd=PROJECT, check=True)
    suffix = "" if level == 0 else f"-l{level:02d}"
    return require(GAME / f"tgt/wolf3d-vdplet-direct{suffix}.bin")


def prepare_scenario(scenario: Scenario, application: Path) -> dict[str, object]:
    destination = TARGET / scenario.name
    with tempfile.TemporaryDirectory(prefix=f"{scenario.name}-", dir=TARGET) as name:
        temporary = Path(name)
        shutil.copyfile(application, temporary / "wolf3d.bin")
        shutil.copyfile(require(MODULE), temporary / "wolf3d.vdpl")
        for relative in ("hud/hud.agnb", "audio/sfx.agnb", "shell/shell.agnb"):
            source = require(GENERATED / relative)
            shutil.copyfile(source, temporary / source.name)
        for level in range(10):
            source = GENERATED / f"levels/level_{level:02d}"
            target = temporary / source.name
            target.mkdir()
            for filename in LEVEL_FILES:
                shutil.copyfile(require(source / filename), target / filename)
            if level == scenario.initial_level:
                for state in sorted(target.glob("state_*.w3l")):
                    state.write_bytes(patch_state(state.read_bytes(), scenario))
                if scenario.ghosts:
                    build_ghost_sprite_container(target, temporary)
        receipt = {
            "scope": "disposable Wolf3DOrig visual-acceptance payload",
            "scenario": scenario.name,
            "initial_level": scenario.initial_level,
            "player_tile": list(scenario.player_tile),
            "player_angle": scenario.angle,
            "synthetic_ghosts": scenario.ghosts,
            "one_hit_hans": scenario.one_hit_hans,
            "diagnostic_invulnerable": scenario.invulnerable,
            "application_sha256": sha(temporary / "wolf3d.bin"),
            "module_sha256": sha(temporary / "wolf3d.vdpl"),
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
        if destination.exists():
            shutil.rmtree(destination)
        temporary.rename(destination)
    return receipt


def main() -> None:
    TARGET.mkdir(parents=True, exist_ok=True)
    # build.py names outputs only by initial level. Snapshot each diagnostic
    # variant immediately so a later invulnerable build cannot overwrite the
    # mortal application path retained for another scenario.
    with tempfile.TemporaryDirectory(prefix="applications-", dir=TARGET) as name:
        application_dir = Path(name)
        applications: dict[tuple[int, bool], Path] = {}
        for level, invulnerable in sorted({
            (scenario.initial_level, scenario.invulnerable)
            for scenario in SCENARIOS
        }):
            source = build_application(level, invulnerable)
            destination = application_dir / (
                f"level_{level:02d}-{'invulnerable' if invulnerable else 'mortal'}.bin"
            )
            shutil.copyfile(source, destination)
            applications[(level, invulnerable)] = destination
        receipts = [
            prepare_scenario(
                scenario,
                applications[(scenario.initial_level, scenario.invulnerable)],
            )
            for scenario in SCENARIOS
        ]
    print(json.dumps({
        "target": str(TARGET),
        "scenarios": [
            {
                "name": receipt["scenario"],
                "initial_level": receipt["initial_level"],
                "application_sha256": receipt["application_sha256"],
                "files": len(receipt["files"]) + 1,
            }
            for receipt in receipts
        ],
    }, indent=2))


if __name__ == "__main__":
    main()
