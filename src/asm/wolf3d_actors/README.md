# Wolf3D actor-pool regression

This directory contains a durable, direct-eZ80 regression for the production
[`wolf3d_actors.inc`](../wolf3d/src/wolf3d_actors.inc). It deliberately does
not carry a test copy of actor algorithms.

The assembly fixture validates:

- the complete generated medium-difficulty E1L1 seed (21 live actors), slot 0,
  all 128 free records, all 150 dirty bytes, and all 4096 `actorat` cells;
- actor and state id lookup at both ends and across invalid state ids;
- detached allocation, zeroing, tail publication, `NEVERMARK`, middle-list
  self-removal, reusable slots, and SET/REMOVE/SET dirty precedence;
- deterministic full-pool exhaustion and carry behavior;
- clear, exact inclusive `0x4800`, one-LSB-outside, nonshootable, corrupt-slot,
  and out-of-scan player/actor collision cases, plus all four high/low X/Y
  3x3-to-4x4 AABB crossovers where the actor reserves the second-away tile;
- the actual command memory passed synchronously by `RST.LIL 18h`: subcommand
  4 prefix/length and all 15 payload bytes for cardinal and continuous facing,
  plus subcommand 5 prefix/length/id and post-submit dirty clearing.

The runner always uses the stock VDP. Actor commands are write-only snapshots;
their bytes are verified in eZ80 memory after the synchronous send, so no
custom Wolf3D VDP behavior can make a broken eZ80 producer pass.

Run from any directory:

```sh
W3D_STAGED_ROOT=/tmp/wolf3d_work/Wolf3dOrig \
W3D_RUNTIME_ROOT=/home/smith/Agon/mystuff/Wolf3dOrig \
/home/smith/Agon/mystuff/Wolf3dOrig/.venv/bin/python \
  /tmp/wolf3d_work/Wolf3dOrig/src/asm/wolf3d_actors/scripts/run_actor_emulator_regression.py
```

`W3D_STAGED_ROOT` selects the source under test. `W3D_RUNTIME_ROOT` selects the
already-established emulator, MOS and stock-VDP artifacts. The runner builds a
disposable SD-card tree, waits for a 16-byte MOS-file mailbox, reports the first
failure with phase/reason/detail, and removes the temporary profile.

## Patrol/state-runner regression

[`patrol_regression.asm`](src/patrol_regression.asm) directly exercises the
production `wolf3d_actor_sim.inc` and motion-owned door routines. Its runner
generates the independent W3PV-v1 corpus in a disposable short work directory,
symlinks the staged production includes there for `ez80asm`, and runs with the
stock VDP. No patrol algorithm is copied into the assembly fixture.

The eleven oracle cases pin the exact shared `2,2,3` original-tic cadence, zero-tic
latch, same-shape and shape-changing state boundaries, guard/dog door rules,
residual movement through a path arrow, inclusive player overlap, dirty state,
destination release/reclaim, door-before-actor ordering, and a 92-frame route
using real medium E1L1 slot 11 and door 8. A malformed signed wait of `-257`
also proves that path movement cannot alias door zero through the low byte and
fails closed at `NODIR` without removing or dirtying the actor. Directed
assembly-only checks add
walls, blocking statics, shootable/nonshootable reservations, map underflow,
diagonal corner rejection, actor door obstruction, the original adjacent-cell
`MINDIST` CloseDoor boundary at a fully open door, and invalid-state removal.

Run from any directory:

```sh
W3D_STAGED_ROOT=/tmp/wolf3d_work/Wolf3dOrig \
W3D_RUNTIME_ROOT=/home/smith/Agon/mystuff/Wolf3dOrig \
/home/smith/Agon/mystuff/Wolf3dOrig/.venv/bin/python \
  /tmp/wolf3d_work/Wolf3dOrig/src/asm/wolf3d_actors/scripts/run_patrol_emulator_regression.py
```

The accepted corpus reports 607/607 direct production-assembly checks. The
92-frame real E1L1 slot-11/door-8 route currently measures 16 ms total
(approximately 0.174 ms per fixed simulation frame) with PRT1 in Fab.

The patrol mailbox is 37 bytes and includes per-case and per-phase mismatch
counts in addition to the first compact diagnostic. A PRT1 stopwatch reports
the elapsed whole milliseconds for the real 92-frame E1L1 acceptance route;
the same timing path can run unchanged on hardware.
