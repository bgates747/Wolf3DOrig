# Wolf3D eZ80 gameplay sight

This project contains the eZ80-owned, planar gameplay raycaster used for
enemy line-of-sight decisions. It does not render columns or pixels; the VDP
owns rendering.

Project layout follows the established `src/asm/<app>/{src,tgt}` convention:

- `src/` contains the regression executable (`dda_regression.asm`). The
  reusable assembly API it exercises (`wolf3d_world.inc`/`wolf3d_math.inc`/
  `wolf3d_sight.inc`) has graduated to `../wolf3d/src/` now that it's
  validated -- this project's own job was prototyping and proving that API,
  not owning its permanent home. `dda_regression.asm`'s bare
  `include "wolf3d_sight.inc"` therefore requires ez80asm to be invoked with
  `../wolf3d/src` as its working directory (ez80asm resolves a nested bare
  include relative to its cwd, not the including file's own directory); the
  regression runner below already does this.
- `scripts/` contains durable fixture/vector generators and the emulator
  regression runner.
- `tgt/` is ignored generated output.

The shared 64x64 tilemap is produced by
`agonport/tools/gen_dda_fixture.py` and tracked at
`agonport/assets/generated/dda_smoke_test_map.bin`.

## Numeric contract

Public positions are non-negative signed 16.16 values in the range
`0 <= coordinate < 64<<16`. `w3d_CheckLine` deliberately discards the low
eight fractional bits for ordinary-cell traversal and performs that hot path
at 8.8 precision. Input coordinates and each ordinary DDA step are therefore
quantized at 1/256-tile resolution.

Door positions remain unsigned 0.16 values. On encountering a door tile, the
routine computes its center-plane intercept directly from the original 16.16
endpoints, verifies that the plane really crosses that door's row or column,
and compares the full 16-bit fraction as `fraction <= door.position`.

Map and direction conventions are defined in `../wolf3d/src/wolf3d_world.inc`.

## Regression

Run the host oracle checks and the complete eZ80 emulator suite with:

```bash
.venv/bin/python \
  src/asm/wolf3d_ai/scripts/test_dda_oracle.py -v
.venv/bin/python \
  src/asm/wolf3d_ai/scripts/run_dda_regression.py
```

The emulator suite defaults to 10,000 randomized records per public routine,
in addition to directed threshold cases. It uses the eZ80 PRT1 timer and
pauses timing around vector-file reads, so the reported mixed-loop budget can
also run unchanged on hardware. Before timing, an ABI preflight verifies A/Z/
carry, the active BC/DE/HL and IX/IY registers, and all shadow GP registers
for both public routines.

`CheckSight` applies these gates in order:

1. disconnected areas reject;
2. both full-16.16 per-axis distances strictly below 1.5 tiles accept
   automatically;
3. noise bypasses facing but never walls or area connectivity;
4. all eight directions use a forward half-plane test (`nodir` accepts);
5. `CheckLine` decides geometric obstruction.

Reserved map bytes `0xC0..0xFF` block conservatively. Actor/player starting
cells are assumed valid and open under the gameplay-state contract.

## Clean implementation boundary

Names and externally visible behavior follow the project handoff and may be
cross-checked against the educational reference source. The assembly,
generated oracle, data layout, and control flow here are independently
implemented and do not include or redistribute id Software source.
