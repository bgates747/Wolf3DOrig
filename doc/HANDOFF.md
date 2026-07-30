# Handoff — wolf3dmaps (as of 2026-07-25)

> **Superseded, kept for history.** Since this was written the project
> pivoted away from image-based extraction (see below) to decoding the
> real shareware binary files directly, moved from
> `/home/smith/Desktop/wolf3dmaps` to `/home/smith/Agon/mystuff/Wolf3dOrig`,
> and got a git repo. For current state, read
> [map_toolchain_notes.md](map_toolchain_notes.md),
> [devlog_20260730.md](devlog_20260730.md), and
> [agon_port_notes.md](agon_port_notes.md) instead — this file is
> historical context only, not an accurate handoff anymore.

This document exists so a fresh agent session can reconstruct project
state and continue seamlessly. Read this first, then the companion
docs it references.

## 1. What this project is

`wolf3dmaps` extracts a machine-readable (JSON) map definition from the
classic Wolfenstein 3D overview map images — one per floor, 60 floors
total (6 episodes × 10 floors). This is step one of a larger,
longer-term ambition: the Author intends to eventually port a
Wolfenstein-3D-style raycasting engine to run on an **ESP32-based VDP**,
driven by an **eZ80 assembly application** (this is an Agon-platform
project — hence `~/Agon/` paths below). The Author may or may not clone
the original game exactly; the primary goal is a general game engine
for original development, but cloning Wolf3D itself is also plausible
("knowing me, we may try to clone the actual game" — direct quote).

**Nothing has been extracted yet.** All work so far is organizational,
research, and design-question-gathering. No extraction code exists.

## 2. Companion documents (read these next)

- [devlog_20260725.md](devlog_20260725.md) — the living devlog/design
  doc. Contains: Project Goals, Today's Goal (checklist), a section on
  the external reference source clone, a section on the shareware data
  acquisition, and a 13-item **"Open Questions for the Author"**
  checklist (`[x]` = answered with a recorded Decision, `[ ]` =
  unanswered). **Only Q1 and Q2 are answered.** Q3–Q13 are the main
  blocker to writing extraction code and are reproduced in Section 5
  below for the next agent to re-ask the Author.
- [wolf3d_reference.ipynb](wolf3d_reference.ipynb) — a markdown-only
  (no code cells yet) research notebook, meant to grow into a
  programming/user reference. Documents, with citations: level
  structure (64×64 grid, 3-plane format), Plane 0 structural tile value
  ranges, Plane 1 "things" value ranges, a comparison color-legend from
  an existing open-source Wolf3D-in-JS renderer, the `MAPSWL6.H`
  level-name enum (confirms 8-regular+boss+secret=10-floors/episode
  structure), a section concluding no pre-decoded/JSON map data exists
  in any repo searched, and an "Open items" section flagging that
  individual wall **texture names** (per numeric ID) remain unfound.

## 3. Workspace state (verified facts, not guesses)

Workspace root: `/home/smith/Desktop/wolf3dmaps` (no git repo initialized yet).

```
wolf3dmaps/
├── .gitignore                              # excludes both EXTERNAL symlinks below
├── doc/
│   ├── devlog_20260725.md
│   ├── wolf3d_reference.ipynb
│   └── HANDOFF.md                          # this file
├── src/assets/maps/orig/
│   ├── Overview.png
│   └── Episode_1/ .. Episode_6/
│       └── 0.png .. 9.png                  # zero-based; 8=boss floor, 9=secret floor
├── wolf3d-original-source-EXTERNAL         # symlink -> ~/Agon/id/wolf3d (see below)
└── wolf3d-shareware-data-EXTERNAL          # symlink -> ~/Agon/id/wolf3d-shareware (see below)
```

Two **external, git-ignored** reference resources were set up outside
the repo and symlinked in for convenient browsing in-session:

- **`~/Agon/id/wolf3d`** — a `git clone` of
  [github.com/id-Software/wolf3d](https://github.com/id-Software/wolf3d),
  the official 2012 id Software source release (`WOLFSRC/` dir: all
  original C/ASM). Ships under id's own **Limited Use Software License
  Agreement** (educational-use-only, no redistribution of the source) —
  **not** a permissive OSS license despite common perception. Contains
  no game data files at all (confirmed by search) — source only.
- **`~/Agon/id/wolf3d-shareware`** — the actual shareware Episode 1
  game data (`MAPHEAD.WL1`, `GAMEMAPS.WL1`, `VSWAP.WL1`, etc.),
  downloaded from the Internet Archive
  ([archive.org/details/Wolfenstein3d](https://archive.org/details/Wolfenstein3d),
  id's v1.4 shareware release, freely redistributable by id's own
  long-standing policy). This is real binary map/texture data for
  Episode 1 (10 levels) that could be used to validate/cross-check the
  image-based extraction, or to write a from-scratch binary decoder as
  an alternate/complementary path — **not started, no code written**.

**Deliberate boundary (explicitly requested twice by the Author):**
`wolf3dmaps` is a standalone repository, not a fork of id's source.
Nothing from either external resource above is to be vendored, copied,
or committed into this repo — both symlinks are excluded via
`.gitignore` specifically so an eventual `git init`/publish here can
never accidentally redistribute id's licensed material.

## 4. Key technical facts already verified (grounded, not guessed)

- Wolf3D level = **64×64 tile grid**, hard-coded in the original engine
  (ignores width/height header fields). This fits comfortably under the
  Author's **256×256 tile ceiling** for the eZ80 target — not a current
  concern.
- File format (for a real binary decode, if pursued): `MAPHEAD.WL6/WL1`
  (RLEW tag + per-level `u32` offset table) → `GAMEMAPS.WL6/WL1` (each
  level: header with 3 plane offsets/lengths + name, each plane
  Carmack-compressed then RLEW-compressed, decompressing to 64×64
  `u16` values) → `VSWAP.WL6/WL1` (64×64 wall textures + RLE sprites).
- Plane 0 = structural (walls 0–63, elevator 21, doors 90–101, area
  tiles 107–143). Plane 1 = "things" (player spawn 19–22, items,
  enemies 108–227, pushwall marker 98, etc.). Full value-range tables
  are in the notebook, not repeated here.
- 60 levels total = 6 episodes × (8 regular + 1 boss + 1 secret),
  confirmed via id's own `MAPSWL6.H` enum — matches our zero-based
  `0.png`–`9.png` renaming exactly (index 8 = boss, index 9 = secret).
- No existing machine-readable/JSON map data was found in either
  repo searched (id-Software/wolf3d or the fan project vpoupet/wolfenstein)
  — every source ships/decodes the original compressed binary format
  at runtime. Our extraction effort is not duplicating existing work.
- Wall **texture names** (friendly name per numeric wall ID) remain an
  **unresolved open item** — flagged honestly as not-yet-found in the
  notebook rather than guessed at.

## 5. Immediate next step: re-ask the Author these questions

Devlog Q1 (output format → JSON, tabular-where-feasible) and Q2 (grid
resolution → 64×64 confirmed, fits the 256×256 ceiling) are already
answered — don't re-ask those. **Please re-ask the Author Q3–Q13
below** (reproduced verbatim from the devlog) one at a time or in a
batch, whichever the Author prefers, and record answers back into
[devlog_20260725.md](devlog_20260725.md) under "Open Questions for the
Author" (flip `[ ]` → `[x]` and add a `- **Decision:**` line, following
the exact pattern already used for Q1/Q2):

3. [ ] **Tile taxonomy** — Should wall tiles be classified by their
       in-game texture name (e.g. `greystone`, `wood`, `bluestone`), by
       a generic numeric/enum ID, or both (ID + human-readable label)?
4. [ ] **Marker taxonomy** — What's the full legend of colored markers
       we should expect (enemies by type, treasure, weapons, doors,
       push-walls, player start/facing, elevator switches, etc.)? Do you
       have a reference legend/key image, or should we reverse-engineer
       it empirically from the maps?
5. [ ] **Coordinate system** — Should the origin `(0,0)` be top-left,
       bottom-left, or match the original game engine's coordinate
       convention?
6. [ ] **Ambiguous/overlapping tiles** — How should we handle doors,
       secret push-walls, or elevator tiles that may render similarly
       to plain walls/floors in the overview image?
7. [ ] **Player facing/orientation** — Does the overview image encode
       the player start's facing direction, and if so, should that be
       captured in the schema?
8. [ ] **Tooling/language** — Any preference for the extraction
       tooling (e.g. Python + Pillow/OpenCV vs. a Node/TS image
       library), given the rest of the repo lives under `src/`?
9. [ ] **Output location & naming** — Where should generated map
       definitions live (e.g. `src/assets/maps/extracted/Episode_1/0.json`),
       and should the naming scheme mirror the `orig/` structure we just
       set up?
10. [ ] **Validation strategy** — Beyond visual inspection, do you want
        an automated check (e.g. re-render the extracted definition
        back into an image and diff against the source) to confirm
        fidelity?
11. [ ] **Schema versioning** — Should the map definition include a
        `schemaVersion` field so the format can evolve without breaking
        older extracted maps?
12. [ ] **Non-uniform images** — Should we assume all 60 floor images
        share identical dimensions/scale, or do we need to detect
        per-image scale (e.g. if the overview map was rendered at a
        different resolution)?
13. [ ] **Overview file** — Does [Overview.png](../src/assets/maps/orig/Overview.png)
        need its own extraction pass (e.g. episode/level graph, secret
        level connections), or is it purely cosmetic/out of scope for
        this effort?

Once enough of Q3–Q13 are answered (at minimum Q3/Q4/Q8/Q9 are
prerequisite to writing any code), proceed to the devlog's "Today's
Goal": extract a machine-readable definition from
[Episode_1/0.png](../src/assets/maps/orig/Episode_1/0.png) first,
validate it, then iterate outward to the rest of Episode 1 and finally
the other five episodes.

## 6. Style/working notes for the next agent

- The Author likes numbered checkbox lists (`[ ]`/`[x]`) for tracking
  open decisions, and answers them interactively over multiple turns —
  don't expect all of Q3–Q13 answered at once.
- The Author is meticulous about licensing boundaries around id
  Software's original material — always keep external reference
  clones/data out of this repo's git history, and prefer
  reimplementing logic from scratch over adapting/copying id's C source
  even under "Educational Use."
- When citing facts about the original file format, prefer this
  notebook's already-cited primary sources over re-guessing at URLs.
- Whenever the Author asks an Agon-porting-specific aside (how a future
  Agon-side loader/renderer would consume this project's formats, platform
  constraints, etc.) rather than a question about this project's own
  toolchain, log it in [agon_port_notes.md](agon_port_notes.md): the
  question, the answer given, and whether it was resolved or deferred.
  Informal running log, not rigorously structured — append, don't rewrite.
