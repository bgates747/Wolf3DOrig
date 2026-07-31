# Wolf3D actor-awareness host oracle

This project specifies and directly regresses the narrow actor-awareness
layer. `scripts/awareness_oracle.py` is an independent host model; it imports
neither the eZ80 implementation nor the existing DDA oracle. Its wall/door
decision is a replaceable line-of-sight callable, so the model does not
duplicate the already-regressed gameplay raycaster.

The contract is:

1. An actor with an invalid or disconnected area cannot begin detection.
2. Visual sight applies the existing eZ80 gates in order: area, strict
   full-16.16 1.5-tile proximity, eight-direction 8.8 facing, then wall/door
   line trace.  Near sight is automatic only after the area gate.
3. Noise wakes an ordinary non-ambush actor anywhere in a connected area.  It
   bypasses facing and the complete line trace.  This is the full
   `SightPlayer` rule, intentionally distinct from standalone
   `w3d_CheckSight()` where the `made_noise` input bypasses facing but not
   walls.
4. An ambush actor ignores noise and always requires visual sight.  Its ambush
   bit clears as soon as visual acquisition seeds the reaction delay.
5. Detection first seeds the original class-specific delay and cannot activate
   on that same call.  Guard/mutant/SS/dog delays consume one deterministic RNG
   byte; officer delay is fixed at two tics and consumes none.
6. A pending delay counts down before area and sight checks.  It therefore
   survives a later door closure or area disconnect and activates on zero or
   overshoot.
7. Activation installs the semantic class-specific `chase1` state, ten state
   tics, original speed multiplier, `ATTACKMODE|FIRSTATTACK`, and cancels a
   negative door wait.  It does not move, turn, reserve, or otherwise alter
   the actor pose or persistent `active` byte. Chase movement and combat are
   explicitly outside this slice.

The chase-state values in the host oracle remain descriptive strings. The
direct fixture maps them to the production-stable ids 47..51 and compares the
complete resulting actor record fields.

The behavior is grounded in `SightPlayer`, `CheckSight`, and `FirstSighting`
from `orig/src/WOLFSRC/WL_STATE.C`, the `T_Stand`/`T_Path` call sites and chase
state timings in `WL_ACT2.C`, plus the current area and sight contracts in
`../wolf3d_areas/README.md` and `../wolf3d_ai/README.md`.

Run from `scripts/` in the staging tree:

```sh
/home/smith/Agon/mystuff/Wolf3dOrig/.venv/bin/python \
  -m unittest -v test_awareness_oracle.py
```

The directed suite covers area validation, strict proximity boundaries, all
eight facing half-planes, replaceable wall/door results, ordinary noise,
ambush behavior, deterministic delay limits and `2,2,3` countdown, pending
delay persistence, every ordinary class's activation effects, negative door
wait cancellation, and the no-chase-movement boundary.

## Direct production-eZ80 regression

`src/awareness_regression.asm` calls the actual production labels in
`../wolf3d/src/wolf3d_actor_sim.inc` and `wolf3d_sight.inc`. It contains no
second awareness algorithm. Literal directed inputs exercise:

- exact runtime-RNG continuation after generated actor spawning and `255 -> 0`
  index wrap;
- all five ordinary class delay formulas, including officer's no-consume rule;
- connected, disconnected, and invalid actor areas;
- quiet clear/blocked/facing sight and the strict full-16.16 near boundary;
- non-ambush noise bypass, ambush visual acquisition, and immediate ambush-bit
  clearing;
- pending-delay `2,2,3` countdown and persistence after disconnection;
- all five FirstSighting state/tic/speed/flag/distance changes while comparing
  the entire 13-byte pose/area/direction/active prefix unchanged;
- direct and full-runner containment of corrupt class/attack-mode inputs;
- two actors observing one shared noise byte before it clears after the whole
  live-list pass.

The fixture uses the stock isolated emulator and a hardware-compatible PRT1
stopwatch. From the staging tree, run:

```sh
W3D_STAGED_ROOT=/tmp/wolf3d_work/Wolf3dOrig \
W3D_RUNTIME_ROOT=/home/smith/Agon/mystuff/Wolf3dOrig \
/home/smith/Agon/mystuff/Wolf3dOrig/.venv/bin/python \
  scripts/run_awareness_emulator_regression.py
```

The accepted direct corpus reports 321/321 checks across 11 cases. Its binary
is 44,655 bytes with SHA-256
`8311d9390862a71cdfce5788a89b00e25de83721b5c0bf79f7a3bff934f22ceb`.
A reference run measured 10,000 connected quiet visual acquisitions in
1,099 ms, or approximately 0.1099 ms per call; comparisons and file I/O are
outside the timed loop.
