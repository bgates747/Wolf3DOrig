#!/usr/bin/env python3
"""Stage C: for each real shareware level, determine exactly which wall/door
textures and sprite shapenums it actually uses, then split Stage B's master
images.jsonl into two per-level manifests (tiles + sprites) -- the
granularity Author decision 2026-07-31 asked for ("one .agnb for tile
assets, one for sprites. split by episode and level to keep as much sram
free on the esp32 as possible").

Plane0 (walls/doors): tile values 1..63 are direct wall texture ids (see
formats/vswap.py's wall_tile_to_chunks); values 90..101 are doors, whose
*rendered* texture depends on lock type, not the raw tile value -- grounded
in WL_DRAW.C's DOORWALL+{0,2,4,6} switch (see formats/vswap.py's
door_kind_to_chunks docstring) via the well-established
``lock_type = (tile - 90) // 2`` formula (also used by this repo's sibling
src/toolchain/cli/extract.py, grounded there against WL_GAME.C/WL_DEF.H).
lock_type 0 -> "normal", 1-4 -> "locked", 5 -> "elevator"; the door "jamb"
(frame) texture is always needed once any door tile appears in the level.

Plane1 (statics/actors): static item codes (23-74) map 1:1 to a real
shapenum via spritenames.STATIC_SHAPENUMS (exact, no ambiguity -- statics
don't animate). Enemy/boss/ghost codes identify a creature KIND exactly
(reusing the same tile-range logic as the sibling project's
extract.py -- ENEMY_KINDS/MUTANT_STAND/BOSS_TILES/GHOST_MIN,MAX are
transcribed here rather than imported, per the fork policy), and this
script includes that KIND's *entire* animation-frame shapenum block
(formats/sprite_kinds.kind_shapenum_block) intersected with the master
manifest's actually-converted shapenums -- i.e. every real frame the eZ80
actor state machine could ever select for that creature, not just one
representative frame (Author decision 2026-07-31).
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agnb.manifest import ImageManifestEntry, KIND_SPRITE, KIND_WALL  # noqa: E402
from formats import mapfile, sprite_kinds, spritenames  # noqa: E402

GENERATED_DIR = Path(__file__).resolve().parents[3] / "assets" / "generated" / "wolf3d"
DEFAULT_MAPHEAD = Path(__file__).resolve().parents[4] / "orig" / "data" / "MAPHEAD.WL1"
DEFAULT_GAMEMAPS = Path(__file__).resolve().parents[4] / "orig" / "data" / "GAMEMAPS.WL1"

DOOR_MIN, DOOR_MAX = 90, 101
DOOR_LOCK_KIND = {0: "normal", 1: "locked", 2: "locked", 3: "locked", 4: "locked", 5: "elevator"}
# textureId assignment, must match scripts/export_vswap_art.py exactly.
DOOR_KIND_TEXTURE_ID = {"normal": 121, "jamb": 122, "elevator": 123, "locked": 124}

STATIC_MIN, STATIC_MAX = 23, 74
DEAD_GUARD_TILE = 124  # plane1 code (unrelated to the door textureId 124 above)
GHOST_MIN, GHOST_MAX = 224, 227
ENEMY_KINDS = [("GRD", 108, 112), ("OFC", 116, 120), ("SS", 126, 130), ("DOG", 134, 138)]
DIFFICULTY_TIER_OFFSETS = (0, 36, 72)
MUTANT_STAND, MUTANT_PATROL = 216, 220
MUTANT_TIER_OFFSETS = (0, 18, 36)
BOSS_NAMES = {214: "HANS", 197: "GRETEL", 215: "OTTO", 179: "FAT", 196: "SCHABBS",
              160: "HTLR-FAKE", 178: "HITLER"}
GHOST_NAMES = {224: "BLINKY", 225: "CLYDE", 226: "PINKY", 227: "INKY"}


def plane1_creature_kind(value: int) -> str | None:
    if value in BOSS_NAMES:
        return BOSS_NAMES[value]
    if value in GHOST_NAMES:
        return GHOST_NAMES[value]
    for name, stand, patrol in ENEMY_KINDS:
        for t in DIFFICULTY_TIER_OFFSETS:
            if stand + t <= value <= stand + t + 3 or patrol + t <= value <= patrol + t + 3:
                return name
    for t in MUTANT_TIER_OFFSETS:
        if MUTANT_STAND + t <= value <= MUTANT_STAND + t + 3 or \
                MUTANT_PATROL + t <= value <= MUTANT_PATROL + t + 3:
            return "MUT"
    return None


def scope_level(plane0: list[list[int]], plane1: list[list[int]], max_shapenum: int):
    wall_ids: set[int] = set()
    door_kinds: set[str] = set()
    sprite_shapenums: set[int] = set()

    for row in plane0:
        for value in row:
            if 1 <= value <= 63:
                wall_ids.add(value)
            elif DOOR_MIN <= value <= DOOR_MAX:
                lock_type = (value - DOOR_MIN) // 2
                door_kinds.add(DOOR_LOCK_KIND[lock_type])

    if door_kinds:
        door_kinds.add("jamb")

    for row in plane1:
        for value in row:
            if STATIC_MIN <= value <= STATIC_MIN + len(spritenames.STATIC_SHAPENUMS) - 1:
                sprite_shapenums.add(spritenames.STATIC_SHAPENUMS[value - STATIC_MIN])
            elif value == DEAD_GUARD_TILE:
                sprite_shapenums.add(spritenames.SPR_GRD_DEAD)
            else:
                kind = plane1_creature_kind(value)
                if kind:
                    start, end = sprite_kinds.kind_shapenum_block(kind, max_shapenum)
                    sprite_shapenums.update(range(start, end + 1))

    door_texture_ids = {DOOR_KIND_TEXTURE_ID[kind] for kind in door_kinds}
    return wall_ids, door_texture_ids, sprite_shapenums


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--maphead", type=Path, default=DEFAULT_MAPHEAD)
    parser.add_argument("--gamemaps", type=Path, default=DEFAULT_GAMEMAPS)
    parser.add_argument("--images-manifest", type=Path, default=GENERATED_DIR / "processed" / "images.jsonl")
    parser.add_argument("--out", type=Path, default=GENERATED_DIR / "levels")
    args = parser.parse_args()

    maphead = mapfile.read_maphead(args.maphead.read_bytes())
    gamemaps = args.gamemaps.read_bytes()

    all_entries = [
        ImageManifestEntry(**json.loads(line))
        for line in args.images_manifest.read_text().splitlines()
        if line.strip()
    ]
    wall_entries_by_id = {e.assetId: e for e in all_entries if e.kind == KIND_WALL}
    sprite_entries_by_id = {e.assetId: e for e in all_entries if e.kind == KIND_SPRITE}
    max_shapenum = max(sprite_entries_by_id) if sprite_entries_by_id else 0

    args.out.mkdir(parents=True, exist_ok=True)

    for index, offset in enumerate(maphead.level_offsets):
        if offset <= 0:
            continue
        level = mapfile.read_level(gamemaps, maphead, index, maphead.magic)
        wall_ids, door_texture_ids, sprite_shapenums = scope_level(
            level.plane0, level.plane1, max_shapenum
        )

        tile_entries = [wall_entries_by_id[i] for i in sorted(wall_ids) if i in wall_entries_by_id]
        tile_entries += [
            wall_entries_by_id[i] for i in sorted(door_texture_ids) if i in wall_entries_by_id
        ]
        sprite_entries = [
            sprite_entries_by_id[s] for s in sorted(sprite_shapenums) if s in sprite_entries_by_id
        ]

        level_dir = args.out / f"level_{index:02d}"
        level_dir.mkdir(parents=True, exist_ok=True)
        _write_jsonl(level_dir / "tiles.jsonl", tile_entries)
        _write_jsonl(level_dir / "sprites.jsonl", sprite_entries)
        print(
            f"level_{index:02d} ({level.header.name}): "
            f"{len(tile_entries)} tile assets, {len(sprite_entries)} sprite assets"
        )


def _write_jsonl(path: Path, entries: list[ImageManifestEntry]) -> None:
    from dataclasses import asdict

    with path.open("w") as f:
        for entry in entries:
            f.write(json.dumps(asdict(entry)) + "\n")


if __name__ == "__main__":
    main()
