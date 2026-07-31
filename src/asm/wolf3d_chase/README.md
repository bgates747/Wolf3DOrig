# Wolf3D ordinary chase host oracle

This staging-only project specifies the smallest faithful movement layer after
actor awareness. `scripts/chase_oracle.py` is an independent host model of the
ordinary `SelectChaseDir`, `SelectDodgeDir`, `T_Chase`, and `T_DogChase`
behavior. It composes the already-settled eZ80 `TryWalk`, `MoveObj`, door,
area, occupancy, reservation, and shared-clock contracts. It does not import
or translate the production assembly.

The contract is:

1. Directions use the source enum exactly: east `0`, northeast `1`, north
   `2`, northwest `3`, west `4`, southwest `5`, south `6`, southeast `7`, and
   nodir `8`. Opposites and diagonal lookup preserve that ordering.
2. `SelectChaseDir` tries the larger player-delta axis, the other direct axis,
   the previous direction, then exactly one randomized source-enum scan. A
   byte greater than `128` scans north, northwest, west; `0..128` scans west,
   northwest, north. Reversal is suppressed until the final attempt. A direct
   or old-direction success consumes no RNG; reaching fallback consumes one.
3. `SelectDodgeDir` always consumes exactly one RNG byte. It tries the
   symmetric toward-player diagonal, four cardinal preferences, then reversal.
   Byte values below `128` swap both preference pairs. `FIRSTATTACK` clears
   before the attempts and removes reversal suppression for that one call.
   Zero deltas deliberately keep the source's west/north bias.
4. Ordinary guards, officers, SS, and mutants call the supplied line predicate
   before direction or motion work. A clear line consumes one attack byte.
   Chance is `(original_tics << 4) / max_tile_delta`, except same-tile range or
   adjacent range with signed distance below `0x4000` uses chance `300`. The
   comparison is strictly `roll < chance`.
5. Attack execution is an explicit layer boundary. Return values are
   `NONE=0`, `RANGED=1`, `DOG_JUMP_REQUESTED=2`, and `CORRUPT=0xFF`. A ranged
   request means install the class-specific shoot chain. A dog jump request
   means install `s_dogjump1`; the later `T_Bite` RNG and player damage do not
   occur here. Either request stops motion without mutating pose or state.
   The production state runner now consumes either request immediately and
   installs the corresponding attack chain. This chase oracle deliberately
   stops at the raw request seam, so an isolated repeated call requests again
   and keeps the actor paused.
6. Motion uses `speed * original_tics`. The world clock supplies exact
   repeating `2,2,3` original-tic deltas for 30-Hz simulation. Equality at a
   cached tile center still snaps position and selects/reserves the next leg;
   positive residual budget continues along it in the same think call.
7. Ordinary cardinal walkers may commit a closed door as their cached
   destination. Selection requests it once, then the same think requests it
   again while waiting; a fully open door is ordinary floor and proceeds.
   Dogs and all diagonal moves reject a non-open door but may cross a fully
   open one. This models the original door lifecycle: DoorOpening removes the
   actor-grid sentinel at fully open, and CloseDoor restores it on closing.
   Closing-door requests reverse them to opening.
8. Shootable actor reservations, statics, walls, and malformed cells block.
   Nonshootable actors are passable. The scheduler releases the current
   actor's cached reservation during its think and reclaims the final cached
   destination afterward. The settled port keeps both `NONMARK` and
   `NEVERMARK` actors wholly unreserved.
9. `MoveObj` tentatively changes both axes by the full move for diagonals. If
   the actor's valid area is connected, both center deltas within the inclusive
   `+/-0x10000` player square roll the move back without consuming leg
   distance. One LSB outside either axis or a disconnected area permits it.
10. Dogs test their complete remaining budget against the same inclusive
    one-tile square before each movement segment and request their jump without
    RNG. They use dodge selection, never acquire door waits, and treat an
    injected negative distance as `CORRUPT` before projected range testing.

The line predicate is replaceable because wall/door line tracing already has
its own oracle and regression. Awareness, `ACTIVE` scheduling, state-tic
dispatch, attack-state installation, player damage, and the original
`victoryflag` shutdown are outside this layer. The scheduler must suppress
chase work during victory. Player fixed coordinates are authoritative here;
`player_tile_x/y` are derived with `>> 16`, so callers must keep the original
cached player tile fields coherent with the fixed pose.

Two impossible-data policies intentionally follow the settled eZ80 port rather
than unsafe DOS behavior: destination areas outside `0..36` retain the prior
actor area, and malformed ordinary/dog door waits return `CORRUPT`. These are
containment paths, not legal gameplay transitions.

The behavior is grounded in `TryWalk`, `SelectDodgeDir`, `SelectChaseDir`, and
`MoveObj` from `orig/src/WOLFSRC/WL_STATE.C`; `T_Chase` and `T_DogChase` from
`WL_ACT2.C`; original scheduler reservation behavior from `WL_PLAY.C`; and the
current staged actor/area contracts in `../wolf3d_actors/README.md` and
`../wolf3d_areas/README.md`.

Run from `scripts/` in the staging tree:

```sh
python3 -m unittest -v test_chase_oracle.py
```

The directed suite reports 41/41 passing tests. It pins direct/old/fallback
direction ordering, both RNG thresholds and exact draw counts, the symmetric
diagonal table, `FIRSTATTACK`, occupancy/corners/doors/areas, ranged chance
boundaries, attack-request pausing, the `2,2,3` budget, equality and residual
tile crossing, reservation release/reclaim, connected player-overlap bounds,
ordinary door waits, dog projected-range equality, and corrupt-input policy.

## Direct production-eZ80 regression

`src/chase_regression.asm` calls the production chase, dog-chase, selector,
TryWalk, state-runner, CheckLine, door, and movement labels. It carries only
synthetic inputs and literal source-derived expectations; it contains no
second chase algorithm. The stock VDP is sufficient because every result is
compared in eZ80 memory and written through a fixed 32-byte MOS mailbox.

The direct fixture covers:

- larger-axis, old-direction, last-resort reversal, trapped, and exact
  `128/129` chase fallback behavior;
- symmetric vertical-first dodge, below-`128`/exact-`128` randomization,
  `FIRSTATTACK`, and zero-delta bias;
- clear/blocked CheckLine paths, strict chance-eight `7/8` rolls, chance 300
  with roll 255, failed-shot dodge selection, exact RNG indices, and complete
  actor preservation on requests;
- `2,2,3` budgets, center equality, positive residual crossing, persistent
  dodge mode across a center, and full fixed-coordinate/distance results;
- closed-door wait/opening, subsequent open-door progress, fully open floor
  behavior for ordinary actors and dogs, non-open dog rejection, and
  shootable/nonshootable reservations;
- exact two-axis dog projection, repeated unlatched jump requests, full
  diagonal movement, and fail-closed class/direction/wait containment;
- all 30 original chase state records from stable ids 47..51 through appended
  id 76, plus the appended ordinary attack records through id 100, including
  shapes, rotations, timings, think/action ids, links, and total state count
  101;
- one complete live-list scheduler route proving `2,2,3`, release/reclaim,
  dirtiness, no hidden RNG, and no actor fault.

Run from any directory:

```sh
W3D_STAGED_ROOT=/tmp/wolf3d_work/Wolf3dOrig \
W3D_RUNTIME_ROOT=/home/smith/Agon/mystuff/Wolf3dOrig \
/home/smith/Agon/mystuff/Wolf3dOrig/.venv/bin/python \
  /tmp/wolf3d_work/Wolf3dOrig/src/asm/wolf3d_chase/scripts/run_chase_emulator_regression.py
```

The accepted direct corpus reports 703/703 checks across nine phases. Against
the expanded ordinary-combat state table its binary is 49,881 bytes with
SHA-256
`27e224f017b185cffe037b9a6fa137dcab7934d106f3ce9877c6bff3084e2bd1`.
A reference PRT1 run measured 10,000 clear close-range ordinary chase requests
in 743 ms (0.0743 ms/call) and 10,000 projected dog-jump requests in 128 ms
(0.0128 ms/call). Assertions, mailbox I/O, and per-call fixture reset are
outside both timed loops.
