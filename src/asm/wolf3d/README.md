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
  - `wolf3d.asm` -- the client entry point. Currently proves the API and
    loader assemble and link together (banner print only); the real
    MOS-driven main loop (map load via `agnb_load_images`, actor
    think/render dispatch to the VDP, input) is future work.
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
