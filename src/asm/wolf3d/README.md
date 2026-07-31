# Wolf3D eZ80 client

The real, permanent eZ80 game client. Distinct from its two siblings under
`src/asm/`:

- `wolf3d_hello` -- raw wire-protocol smoke test for the `BUFFERED_WOLF3D`
  (`0x4A`) VDP opcode. Proves the encoding, nothing else.
- `wolf3d_ai` -- the sight/collision logic's own prototyping + regression
  project. Its job was validating `w3d_CheckLine`/`w3d_CheckSight` in
  isolation against a host oracle and the eZ80 emulator; that's done.

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
    real level_00 textures, uploads the real tilemap, initializes every door,
    then runs a callback-gated 30 Hz control/render loop. W/S move, A/D strafe,
    the arrow keys turn, and Escape exits. Collision, actors, and the wider game
    loop remain future work. See "Interactive render fixture" below.
  - `wolf3d_fixture.inc` -- generated, do not hand-edit; see below.
  - `wolf3d_render_async.inc` -- the callback-driven control-loop scaffold:
    one render may be in flight, `W3DR` completion is copied by the MOS
    interrupt callback, and the foreground validates and presents it. It
    also retains the 120 Hz elapsed clock needed by future fixed-step
    simulation.
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
level instead of a synthetic one: it loads level_00's real wall/door
textures through the modern AGNB container API, printing one `.` only after
each image is fully finalized as a VDP bitmap. As a temporary upload-path
diagnostic, the completion callback also selects and plots every finalized
64x64 bitmap unscaled in a mode-0 gallery. Once the gallery is visible,
press any key to switch to the Wolf3D render attempt. This distinguishes a
bad MOS-to-VDP bitmap upload from a later renderer/presentation failure;
the host-side Tk viewer alone does not exercise that upload path. A load
error aborts before rendering. It uploads the real tilemap, sends one
`set_door` per real door
(all closed -- the level's actual state at first spawn), sets the player's
real start tile/facing, selects 320x240x64 double-buffered mode 8+128,
clears the draw surface, and issues one `render_frame`.

After that first frame, held-key input advances the persistent player pose at
an exact 30 Hz fixed step. The client resubmits only dirty player state and
never allows more than one VDP render in flight. There is deliberately no
collision yet, making this fixture useful for walking through and inspecting
the complete map.

Presentation follows the same ownership model as `earth-party-local`: the
MOS keyboard callback recognizes the ten-byte `W3DR` completion record and
only publishes a mailbox flag; the foreground control loop validates the
token/sequence and issues exactly one `C3` frame boundary, presenting the
completed hidden buffer. The loop remains responsive without submitting
duplicate frames. Escape disables the VDP notification producer, removes the
callback, and returns cleanly. Player motion advances at a fixed 30 Hz from
the 120 Hz MOS clock; render submission is capped at the same cadence and
skips stale snapshots if rendering falls behind.

`wolf3d_fixture.inc` (the tilemap + precomputed command-stream bytes) is
generated, not hand-written:

```bash
.venv/bin/python agonport/tools/wolf3d_assets/scripts/gen_render_fixture.py --level 0
```

Re-run it (from the repo root) to regenerate/switch levels; it reads real
`MAPHEAD.WL1`/`GAMEMAPS.WL1` data and derives the tilemap, door table
(`vertical`/`lock` from tile parity, grounded in `WL_GAME.C`'s
`SetupGameLevel`), and player start tile/facing directly -- nothing in it
is hand-tuned.

**Hardware deployment** (no emulator/build harness involved): assemble as
above, mount the FAT32 card labelled `AGON`, then run from the repository root:

```bash
.venv/bin/python agonport/tools/deploy_wolf3d_to_sd.py --write-autoexec
```

The narrowly scoped deployer validates the mount and writes only
`/wolf3dorig/wolf3d.bin`, `/wolf3dorig/tiles.agnb`, and (when explicitly
requested) `autoexec.txt`. The generated autoexec selects keyboard layout 1,
changes to `/wolf3dorig`, and loads the program, but leaves `run` commented so
the fixture never starts automatically.

The custom `agon-vdp-wolf3d` VDP firmware must already be flashed onto the
hardware for the door-plane/wall-rendering fix
(`VDP_AGENT_UPDATE3` in the handoff doc) to actually be exercised -- that
firmware build/flash is out of this project's scope (separate repo).

The first fully correct emulator and hardware rendering milestone is recorded
in [the success story](../../../agonport/doc/first_correct_render_success_story.md).
