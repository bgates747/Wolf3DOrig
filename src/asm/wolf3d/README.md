# Wolf3D eZ80 client

The real, permanent eZ80 game client. Distinct from its two siblings under
`src/asm/`:

- `wolf3d_hello` -- raw wire-protocol smoke test for the `BUFFERED_WOLF3D`
  (`0x4A`) VDP opcode. Proves the encoding, nothing else.
- `wolf3d_ai` -- the sight/collision logic's own prototyping + regression
  project. Its job was validating `w3d_CheckLine`/`w3d_CheckSight` in
  isolation against a host oracle and the eZ80 emulator; that's done.
- `wolf3d_gameplay` -- the independent host/oracle and real-eZ80 regression
  project for player collision, `ClipMove`, door state/timing, use sectors,
  blocking statics, mutable pickups/HUD state, and generated wire parity.
- `wolf3d_areas` -- the independent host oracle and direct-eZ80 regression for
  lean door-area connectivity, player-root flooding, and area-gated actor
  scheduling/player exclusion.
- `wolf3d_awareness` -- the independent host oracle and direct-eZ80 regression
  for ordinary-enemy sight/noise acquisition, deterministic reaction delays,
  and `FirstSighting` state changes.
- `wolf3d_chase` -- the independent host oracle and direct-eZ80 regression for
  ordinary chase/dodge selection, door waits, reservations, movement, and
  guard/dog attack requests.
- `wolf3d_combat` -- the independent host oracle and direct-eZ80 regression for
  ordinary ranged/melee attack chains, player damage, movement-speed hit
  chance, and deterministic CPU-side actor visibility.
- `wolf3d_player_combat` -- the independent host oracle and direct
  production-code eZ80 regression for player weapon timing, input, target
  selection, actor pain/death, scores, and stable runtime drops.
- `wolf3d_death` -- the direct production-code eZ80 regression for asynchronous
  render/fizzle ownership, killer-facing turns, life semantics, and complete
  attempt reseeding.

Project layout follows the established `src/asm/<app>/{src,tgt}` convention:

- `src/` contains:
  - `wolf3d_world.inc`/`wolf3d_math.inc`/`wolf3d_sight.inc` -- the validated
    reusable gameplay API, graduated here from `wolf3d_ai` once proven (20
    host oracle tests, 20,112 emulator regression records, both zero
    errors -- see `../wolf3d_ai/README.md`).
  - `agnb_api.inc`/`agnb_dependencies.inc` -- the canonical `.agnb` asset
    loader, vendored verbatim from `agon-utils/examples/agnb/api/` per this
    project's fork/vendor-don't-cross-import convention
    (`agonport/doc/wolf3d-asset-toolchain-plan.md` decision 5). Public entry
    points: `agnb_load_images`/`agnb_load_images_with_callback` (DE ->
    filename). Files packed by `agonport/tools/wolf3d_assets/` already land
    their buffers at the exact ids these loaders expect
    (`Wolf3dWallBufferId()`/`Wolf3dSpriteBufferId()` on the VDP side).
  - `wolf3d.asm` -- the interactive player's-first-position fixture: it loads
    real level_00 wall and sprite textures plus original HUD art,
    uploads the real tilemap, initializes every door and static, then runs a
    callback-gated 30 Hz
    control/render loop. W/S move, A/D strafe, Left/Right turn, Up Arrow
    operates the containing door well or the adjacent facing door, Space
    attacks, and 1..4 select knife, pistol, submachine gun, and gatling gun.
    Escape exits, restoring and clearing the single-buffered MOS display mode
    that was active before launch. Player collision and
    eZ80-authoritative moving doors, original blocking decorations, persistent
    pickups, live HUD fields, and the real difficulty-filtered E1L1 actor
    population are active. Original state timing and path patrols are also
    live, with door-area connectivity determining inactive-actor eligibility.
    Awareness, reaction delays, ordinary chase movement, guard/officer/
    mutant/SS shooting, dog bites, and player damage/death are live. See
    "Interactive render fixture" below.
  - `wolf3d_fixture.inc` -- generated, do not hand-edit; see below.
  - `wolf3d_render_async.inc` -- the callback-driven control-loop scaffold:
    one render may be in flight, `W3DR` completion is copied by the MOS
    interrupt callback, and the foreground validates and presents it. It
    also retains the 120 Hz elapsed clock needed by future fixed-step
    simulation.
  - `wolf3d_actors.inc` -- fixed 150-slot authoritative actor pool, live/free
    lists, tile occupancy, player collision, complete patrol-state table, and
    dirty VDP set/remove bridge. Slot zero is reserved for the player.
  - `wolf3d_actor_sim.inc` -- original 70 Hz actor state semantics advanced by
    an exact `2,2,3` tic cadence at the client's 30 Hz fixed step, plus
    `T_Path`, arrow following, ahead-tile reservation, actor movement/player
    exclusion, guard/dog door behavior, the exact Carmack RNG stream,
    ordinary-enemy awareness/reaction, chase/dodge movement, ordinary attack
    state chains, CPU-side combat visibility, and player damage/death.
  - `wolf3d_areas.inc` -- 37-area player reachability rebuilt by an iterative
    BFS over live ten-byte door records. It batches exact zero-position door
    topology transitions, handles parallel/self-loop doors without a matrix,
    and supplies the scheduling and sight gate for inactive actors.
- `tgt/` is ignored generated output.

## Building

```bash
cd src/asm/wolf3d/src
ez80asm wolf3d.asm ../tgt/wolf3d.bin
```

ez80asm resolves a nested bare `include` relative to its own working
directory, not the including file's directory, so anything that includes
`wolf3d_sight.inc` (which itself bare-includes `wolf3d_world.inc`/
`wolf3d_math.inc`) must be assembled with this `src/` directory as cwd --
see `../wolf3d_ai/scripts/run_dda_regression.py` for a worked example of
invoking ez80asm against an entry file that lives in a different directory
while keeping this one as cwd.

## Interactive render fixture

`wolf3d.asm` exercises the full settled wire protocol
(`agonport/doc/handoff_ez80_ai_raycaster.md`) end to end against a real
level instead of a synthetic one: it loads level_00's real wall/door and
static-sprite textures through the modern AGNB container API, printing one
`.` only after each image is fully finalized as a VDP bitmap. As a temporary upload-path
diagnostic, the completion callback also selects and plots every finalized
wall bitmap unscaled in a mode-0 gallery; the much larger sprite container
uses dot-only breadcrumbs. Once the gallery is visible,
press any key to switch to the Wolf3D render attempt. This distinguishes a
bad MOS-to-VDP bitmap upload from a later renderer/presentation failure;
the host-side Tk viewer alone does not exercise that upload path. It then
loads `hud.agnb`, which contains only the original in-game status assets--not
an extended panel, title, or splash screens. A load error aborts before
rendering. It uploads the real tilemap,
sends one `set_door` per real door (all closed -- the level's actual state at
first spawn), one `set_static` per real decoration/pickup, sets the player's
real start tile/facing, selects 320x240x64 double-buffered mode 8+128,
clears the draw surface, and issues one `render_frame`.

After that first frame, held-key input advances the persistent player pose at
an exact 30 Hz fixed step. Collision uses the original square `0x5800` player
radius and combined-vector/X-only/Y-only `ClipMove` ordering, so the player
slides along blocking walls. Door cells are not treated as solid cubes: the
player can enter either recessed well until the square AABB touches the
center-mounted sliding panel. Partial openings use the VDP's exact aperture
rule (`0..position` is gap, `position+1..FFFF` is panel), including the same
geometry for auto-close obstruction. This deliberately improves on the DOS
movement test, which conservatively treated the entire door tile as occupied.
The 34 original block-type decorations occupy a separate immutable 64x64
bitset: they stop the player but remain sprites, so they never poison the DDA
wall map. The fixture owns all 121 level-0 statics in compact six-byte mutable
records. Stable original-style slots are preferable here to a heap/list: the
VDP wire index never changes, removal is one sentinel store, and E1L1 uses only
726 bytes of record storage.
The 48 original bonus objects are collected when their tile overlaps the same
player AABB after a successful translation. This deterministic simulation-side
contact rule replaces the DOS renderer's visibility-triggered collection and
therefore cannot vary with VDP or rendering cadence. Refused full-health or
full-ammo pickups remain active; consumed objects use the original
`shapenum=-1` sentinel and only that static slot plus changed HUD fields cross
the wire.
Up Arrow is rising-edge-triggered. A valid door cell containing the player takes
priority, keeping the control usable from either recessed well; otherwise the
original one-adjacent-cardinal-tile lookup and angle boundaries apply.
The eZ80 owns door action, 0.16 position, auto-close timing, and player
obstruction; only dirty door/player snapshots are sent before a render. The
client never allows more than one VDP render in flight.

The VDP centers the accepted 256x160 view at `(32,20)` in mode 8, leaving the
320x200 play surround visible on all four sides. It draws original chunk 98's
320x40 status bar directly at `y=200` in every back buffer before presentation.

Presentation follows the same ownership model as `earth-party-local`: the
MOS keyboard callback recognizes the ten-byte `W3DR` completion record and
only publishes a mailbox flag; the foreground control loop validates the
token/sequence and issues exactly one `C3` frame boundary, presenting the
completed hidden buffer. The loop remains responsive without submitting
duplicate frames. Escape disables the VDP notification producer, removes the
callback, restores the caller's saved base video mode without the double-buffer
flag, clears its text and graphics surfaces, and returns cleanly. Player motion
advances at a fixed 30 Hz from
the 120 Hz MOS clock; render submission is capped at the same cadence and
skips stale snapshots if rendering falls behind.

At the default medium difficulty the E1L1 fixture additionally owns 21
non-player actor records (17 guards, three dogs, and one dead guard). The
eZ80 retains the original floor-area ids, path arrows, door area endpoints,
actor live/free lists, and `actorat` occupancy. The VDP receives complete
15-byte render snapshots containing stable actor id, base shape, 16.16
position, world facing, and a `0`/`2`/`8` rotation count; it chooses the
view-relative sprite frame at render time, so camera motion does not dirty
stationary actors. The six map-spawned patrols advance every 30 Hz simulation
quantum after doors and player input, independently of render completion.
Their original random animation phases, including the zero-phase W1 latch,
are generated deterministically; movement follows real plane-1 arrows and
ordinary guards open/wait for doors while dogs reject a closed door. The
ordinary classes acquire the player through the original connected-area,
noise, ambush, proximity, facing, wall/door, and class-delay rules, then run
the original chase/dodge selectors and residual movement. Guards, officers,
mutants, and SS enter their exact shooting chains; dogs enter their jump/bite
chain. Attack actions re-check current geometry and use the shared deterministic
RNG stream. Because the VDP is write-only and render completion is decoupled
from simulation, weapon targeting uses synchronous CPU projection plus a
current `CheckLine` for every candidate instead of the renderer-owned
`FL_VISABLE` bit. This prevents an occluded actor from masking a farther clear
target and prevents knife damage through opaque geometry; equal Q8 depths
retain live-list order. Player health saturates at zero. Lethal damage freezes
ordinary world simulation, presents
the dead face, turns by the shortest path toward the validated killer at the
original angular rate, synchronizes the final view to both mode-8 surfaces,
and hands the viewport to the VDP-owned original red fizzle. The eZ80 then
applies release-before-new-press acknowledgment, original life/score
semantics, a complete authoritative E1L1 attempt reseed, and one
purpose-tagged respawn render. Displayed life zero remains one final playable
attempt; exhausting it leaves a stable red game-over placeholder until Escape.

Knife, pistol, machine gun, and chaingun timelines, target selection, actor
pain/death chains, class scores, extra lives, and stable clip/weapon drops are
live. Weapon and death sounds are retained as deterministic simulation events;
audio playback, bosses, projectiles, menus/high-score entry, and level
completion remain later layers. The remaining rollout is recorded in
`agonport/doc/actor_gameplay_plan.md`.

`wolf3d_fixture.inc` (the tilemap + precomputed command-stream bytes) is
generated, not hand-written:

```bash
.venv/bin/python agonport/tools/wolf3d_assets/scripts/gen_render_fixture.py --level 0
```

Re-run it (from the repo root) to regenerate/switch levels; it reads real
`MAPHEAD.WL1`/`GAMEMAPS.WL1` data and derives the tilemap, door table
(`vertical`/`lock` from tile parity, grounded in `WL_GAME.C`'s
`SetupGameLevel`), row-major static records, separate blocking-static bitset,
and player start tile/facing directly -- nothing in it is hand-tuned. For
shareware E1L1 it emits 121 statics: 34 blockers, 48 pickups, and 39
nonblocking decorations.

The original in-game HUD assets are likewise generated from the bundled WL1
archive:

```bash
.venv/bin/python agonport/tools/wolf3d_assets/scripts/build_hud_assets.py
```

This writes the ignored, reproducible
`agonport/assets/generated/wolf3d/hud/hud.agnb`; the decoder, stable buffer-ID
contract, and tests are documented in
`agonport/tools/wolf3d_assets/HUD_ASSETS.md`.

Run the gameplay host and real-eZ80 regressions from the repository root:

```bash
.venv/bin/python -m unittest -v \
  agonport/tools/wolf3d_assets/tests/test_actor_fixture.py \
  agonport/tools/wolf3d_assets/tests/test_static_fixture.py
.venv/bin/python -m unittest discover -v \
  -s src/asm/wolf3d_gameplay/scripts -p 'test_gameplay_oracle.py'
.venv/bin/python \
  src/asm/wolf3d_gameplay/scripts/run_gameplay_emulator_regression.py \
  --random-cases 10000 --include-zero-delta
.venv/bin/python \
  src/asm/wolf3d_gameplay/scripts/run_pickup_emulator_regression.py
.venv/bin/python \
  src/asm/wolf3d_gameplay/scripts/run_use_emulator_regression.py
.venv/bin/python \
  src/asm/wolf3d_actors/scripts/run_actor_emulator_regression.py
.venv/bin/python \
  src/asm/wolf3d_actors/scripts/run_patrol_emulator_regression.py
.venv/bin/python -m unittest discover -v \
  -s src/asm/wolf3d_areas/scripts -p 'test_area_oracle.py'
.venv/bin/python \
  src/asm/wolf3d_areas/scripts/run_area_emulator_regression.py
.venv/bin/python -m unittest discover -v \
  -s src/asm/wolf3d_awareness/scripts -p 'test_awareness_oracle.py'
.venv/bin/python \
  src/asm/wolf3d_awareness/scripts/run_awareness_emulator_regression.py
.venv/bin/python -m unittest discover -v \
  -s src/asm/wolf3d_chase/scripts -p 'test_chase_oracle.py'
.venv/bin/python \
  src/asm/wolf3d_chase/scripts/run_chase_emulator_regression.py
.venv/bin/python -m unittest discover -v \
  -s src/asm/wolf3d_combat/scripts -p 'test_combat_oracle.py'
.venv/bin/python \
  src/asm/wolf3d_combat/scripts/run_combat_emulator_regression.py
.venv/bin/python -m unittest discover -v \
  -s src/asm/wolf3d_player_combat/scripts \
  -p 'test_player_combat_oracle.py'
.venv/bin/python \
  src/asm/wolf3d_player_combat/scripts/run_player_combat_emulator_regression.py
.venv/bin/python \
  src/asm/wolf3d_death/scripts/run_death_emulator_regression.py
```

**Hardware deployment** (no emulator/build harness involved): assemble as
above, mount the FAT32 card labelled `AGON`, then run from the repository root:

```bash
.venv/bin/python agonport/tools/deploy_wolf3d_to_sd.py --write-autoexec
```

The narrowly scoped deployer validates the mount and writes only
`/wolf3dorig/wolf3d.bin`, `/wolf3dorig/tiles.agnb`,
`/wolf3dorig/sprites.agnb`, `/wolf3dorig/hud.agnb`, and (when explicitly
requested) `autoexec.txt`. The
generated autoexec selects keyboard layout 1, changes to `/wolf3dorig`, and
loads the program, but leaves `run` commented so the fixture never starts
automatically.

The custom `agon-vdp-wolf3d` VDP firmware must already be flashed onto the
hardware for the door-plane/wall-rendering fix
(`VDP_AGENT_UPDATE3` in the handoff doc) to actually be exercised -- that
firmware build/flash is out of this project's scope (separate repo).

The first fully correct emulator and hardware rendering milestone is recorded
in [the success story](../../../agonport/doc/first_correct_render_success_story.md).
