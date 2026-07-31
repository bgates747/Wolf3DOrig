# Wolf3D lean area-connectivity oracle

This directory contains the independent host specification for the eZ80-owned
player-area graph and its first actor-scheduling consumers. It contains no
production assembly and deliberately does not reproduce assembly control flow.

The settled contract is:

1. There are exactly 37 logical area IDs, `0..36`, and one byte of
   player-reachability per area.
2. The authoritative ten-byte door records already carry both area endpoints.
   A door contributes an undirected edge exactly when its unsigned 0.16
   `position` is nonzero. Its action label is irrelevant to connectivity.
3. Each rebuild validates every live edge once, then performs an iterative
   BFS that scans the valid live doors directly. No 37-by-37 matrix exists.
4. Invalid endpoints on an open door are ignored and charge one fault per
   door per rebuild. Closed malformed doors are inert.
5. An invalid or `0xff` player root clears all reachability and charges one
   fault when the root transitions into that value. Rebuilding again with the
   same invalid root does not charge the root fault again.
6. Self-loops do not expand the component. Parallel doors naturally preserve
   an edge while either door remains open.
7. `ACTIVE_NO` actors are scheduled only in a reachable valid area.
   `ACTIVE_YES` and `ACTIVE_ALWAYS` are scheduled globally; free and malformed
   active values are not. Eligibility never mutates the actor's active byte.
8. The original inclusive one-tile actor/player proximity rejection is
   applied only when the actor's area is player-reachable.

The conceptual graph state is 78 bytes:

- reachability: 37 bytes;
- BFS queue: 37 bytes;
- player area: 1 byte;
- queue head/tail: 2 bytes;
- batched topology-dirty flag: 1 byte.

A 16-bit diagnostic fault counter, the last numeric player-area sample plus a
sample-seen byte, and four bounded implementation scratch bytes bring the
actual production allocation to 86 bytes. The existing runtime door records
require no additional topology storage.

## Running the regression

From this directory in the installed checkout:

```sh
../../../.venv/bin/python -m unittest -v scripts/test_area_oracle.py
```

For a staging tree without its own `.venv`, invoke the project-root Python
explicitly:

```sh
/home/smith/Agon/mystuff/Wolf3dOrig/.venv/bin/python \
  -m unittest -v test_area_oracle.py
```

The second command should be run from `scripts/`.

## Coverage

The directed suite covers isolated roots, undirected and transitive chains,
cycles, the `0/36` endpoint extremes, zero-threshold transitions, action-label
independence, parallel doors, 64 self-loops, invalid endpoints, invalid-root
transition accounting, the 64-door limit, all actor active modes, unchanged
39-byte actor records, reachability-gated player overlap, and exact inclusive
one-tile boundaries.

The real medium E1L1 fixture additionally pins:

- player tile `(29,57)` and initial area 2;
- 22 initially closed doors and initial reachability `{2}`;
- door 16 `(1,2)`, then door 7 `(3,1)`, then door 2 `(36,3)`, producing
  `{1,2}`, `{1,2,3}`, and `{1,2,3,36}`;
- all doors open reaching exactly
  `{0,1,2,3,4,5,6,7,10,11,32,33,34,35,36}`;
- both parallel-door pairs and all six self-loop doors;
- exact scheduler-eligible actor-slot sets at the closed, three-door-chain,
  and all-open checkpoints.

Original-source behavior is grounded in `WL_ACT1.C` (`ConnectAreas`,
`DoorOpening`, `DoorClosing`), `WL_AGENT.C` (`Thrust`, `SpawnPlayer`),
`WL_PLAY.C` (`DoActor`), `WL_STATE.C` (`MoveObj`, `CheckSight`), and
`WL_DRAW.C` (the separate render-visibility promotion to active).

## Direct eZ80 production regression

`src/area_regression.asm` is a separate direct regression for the actual
production labels. It contains no copied graph traversal: each checkpoint
lists the expected reachable area IDs, calls the production entry points, and
compares all 37 output bytes plus the player area, topology-dirty flag, 16-bit
fault counter, queue head/tail, and relevant door action/position/dirty state.

The eight cases cover initialization, the exact generated E1L1 checkpoints,
parallel doors, first-opening and final-closing zero boundaries, partial close
and reversal, valid/invalid player-area transitions, malformed live records,
one rebuild batched after simultaneous door transitions, self-loops, and the
documented GP/index-register preservation of
`w3d_rebuild_area_connectivity`.

Run it from the installed checkout with:

```sh
./scripts/run_area_emulator_regression.py
```

To exercise a staging tree against the installed stock emulator, MOS, and VDP:

```sh
W3D_STAGED_ROOT=/tmp/wolf3d_work/Wolf3dOrig \
W3D_RUNTIME_ROOT=/home/smith/Agon/mystuff/Wolf3dOrig \
/home/smith/Agon/mystuff/Wolf3dOrig/.venv/bin/python \
  scripts/run_area_emulator_regression.py
```

The runner assembles in a short disposable directory, boots the normal
Console8 MOS with the stock VDP, waits for the 32-byte `W3A1` result mailbox,
and reports the first failing case/checkpoint/field plus mismatch counts by
case. The accepted fixture reports 1,288/1,288 direct checks across eight
cases. It leaves no binary or emulated SD-card files in the source tree.
