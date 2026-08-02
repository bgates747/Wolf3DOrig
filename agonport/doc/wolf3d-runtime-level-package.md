# Wolf3DOrig Runtime Level Package (`W3L1`)

`W3L1` is the eZ80 application's compact, mutable-world seed. It lets one
assembled client load any shareware Episode 1 floor and difficulty without
regenerating `wolf3d_fixture.inc` or recompiling the application.

The package is generated from the original `MAPHEAD.WL1`/`GAMEMAPS.WL1`
archive by:

```bash
.venv/bin/python \
  agonport/tools/wolf3d_assets/scripts/build_level_packages.py
```

That durable generator writes one ignored, reproducible state file for every
level/difficulty combination below
`agonport/assets/generated/wolf3d/levels/level_XX/`:

```text
state_baby.w3l
state_easy.w3l
state_medium.w3l
state_hard.w3l
```

The same directory owns that floor's `tiles.agnb` and `sprites.agnb`. The
client loads all three by relative pathname, then uploads the package's
tilemap and rebuilds the authoritative eZ80 world before issuing `init_level`
and a complete dirty replay to the VDP.

## Header

All multi-byte fields are little-endian. Version 1.0 has a 64-byte header:

| Offset | Size | Field |
|---:|---:|---|
| 0 | 4 | ASCII magic `W3L1` |
| 4 | 1 | major version (`1`) |
| 5 | 1 | minor version (`0`) |
| 6 | 1 | level index (`0..9`) |
| 7 | 1 | difficulty (`0..3`) |
| 8 | 1 | door count |
| 9 | 1 | non-player actor count |
| 10 | 2 | static count |
| 12 | 1 | deterministic RNG index after spawn ticcounts |
| 13 | 1 | reserved, zero |
| 14 | 2 | total package size |
| 16 | 10 | player seed: x `int32`, y `int32`, angle `uint16` |
| 26 | 14 | seven `uint16` section offsets in the order below |
| 40 | 24 | reserved, zero |

The application checks MOS's file-error result, magic, version, requested
level/difficulty, runtime capacity, total bounds, reserved bytes, exact
canonical section layout, and the end marker before publishing package
pointers to gameplay.

## Sections

Sections are packed consecutively after the header in this exact order:

1. `door_count` ten-byte `W3D_DOOR_*` records;
2. `static_count` six-byte `W3D_STATIC_*` records;
3. `actor_count` 39-byte `W3D_ACTOR_*` records;
4. one 512-byte 64x64 blocking-static bitset;
5. one 4096-byte area-id map;
6. one 4096-byte path-direction map;
7. one 4096-byte VDP tilemap.

The final section is followed by the four-byte `E3L1` end marker. MOS LOAD
silently caps its read to the caller's receive-arena size and does not return
the source file's exact byte count; because the eZ80 clears that arena before
loading, this nonzero marker makes a truncated package fail closed. A valid
canonical package ends at the header's checked total size. Source bytes after
that end are harmless and ignored; the host parser and durable generator still
require exact file length.

The authoritative record offsets and meanings live in
`src/asm/wolf3d/src/wolf3d_world.inc`. Package parsing and host validation
live in `formats/level_package.py`; the eZ80 loader is
`src/asm/wolf3d/src/wolf3d_level_loader.inc`.

## Ownership and lifecycle

The eZ80 retains the loaded package in RAM for the whole level. Immutable map
views point directly into that arena; doors, statics, actors, inventory, and
other changing fields are copied into their normal mutable runtime storage.
Respawning reseeds the current package. Completing a floor selects the next
package, reloads its per-level image containers, preserves game-persistent
player fields, clears per-level state, and submits one complete world reset.

The compile-time `wolf3d_fixture.inc` remains the standalone-regression and
bootstrap default. It is no longer intended to be the application’s only
runtime floor.
