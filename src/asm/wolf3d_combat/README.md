# Wolf3D ordinary combat regression

This staging-only project specifies and directly exercises D2.2 ordinary
enemy attacks. `scripts/combat_oracle.py` is an independent executable host
contract and `scripts/test_combat_oracle.py` is its directed regression.
`src/combat_regression.asm` calls the production eZ80 labels directly, while
keeping its inputs and expected values independent. No file here is included
by the application build.

The scope is deliberately narrow:

- guard, officer, mutant, and SS shoot animation chains;
- the dog jump/bite animation chain;
- source-ordered `T_Shoot`, `T_Bite`, and relevant `TakeDamage` behavior;
- the fixed-step player's `thrustspeed` producer; and
- a deterministic CPU visibility replacement for the original renderer-owned
  `FL_VISABLE` bit.

Chase selection remains in `../wolf3d_chase`. A ranged request installs the
class's shoot1 state, and a dog jump request installs dog jump1. The attack
selection RNG and the later action RNG are distinct: animation time and other
actors may consume random bytes between them.

## Exact animation chains

All 24 attack records have rotations zero and no think function. As in
`DoActor`, an end action executes when its current state expires, before
following `NEXT`. `NewState` seeds the complete first-state duration. Signed
overshoot may traverse and execute several actions in one scheduler call.

| Class | Stable ids | Shapes | Tics | End-action tics | Chase return |
|---|---|---|---|---|---|
| guard | 77..79 | 96, 97, 98 | 20,20,20 | shoot 40 | 60 |
| dog | 80..84 | 135,136,137,135,99 | 10,10,10,10,10 | bite 20 | 50 |
| officer | 85..87 | 285,286,287 | 6,20,10 | shoot 26 | 36 |
| mutant | 88..91 | 234,235,236,237 | 6,20,10,20 | shoot 6,36 | 56 |
| SS | 92..100 | 184,185,186,185,186,185,186,185,186 | 20,20,10,10,10,10,10,10,10 | shoot 40,60,80,100 | 110 |

The destination chase1 ids are guard 47, dog 48, officer 49, mutant 50, and
SS 51; each begins with a ten-tic countdown. Under the port's repeating
`2,2,3` original-tic clock, actions occur on the first fixed quantum reaching
or passing their source time:

| Class | Observed `(elapsed tic, expiring state)` | Return quantum / countdown |
|---|---|---|
| guard | `(42,78)` | elapsed 60 / 10 |
| dog | `(21,81)` | elapsed 51 / 9 |
| officer | `(28,86)` | elapsed 37 / 9 |
| mutant | `(7,88)`, `(37,90)` | elapsed 56 / 10 |
| SS | `(42,93)`, `(60,95)`, `(81,97)`, `(100,99)` | elapsed 112 / 8 |

Every muzzle action re-reads current area connectivity, line of sight, cached
tile distance, player movement, and CPU visibility. Every bite re-reads current
physical positions. Losing eligibility during a wind-up suppresses that one
action; it never stalls the animation chain.

## `T_Shoot`

The exact action order is:

1. Validate the actor area. A malformed area is corrupt; a valid disconnected
   area returns silently with no line trace, RNG, or sound.
2. Run `CheckLine`. A blocked result returns with no RNG or sound.
3. Compute Chebyshev distance from cached actor/player tile coordinates.
4. For SS only, replace it with `floor(2 * distance / 3)`. This effective
   distance drives both chance and damage.
5. Compute the signed, unclamped chance:

| Player signal | CPU-visible | Chance |
|---|---:|---:|
| `thrustspeed >= 6000` | yes | `160 - 16*d` |
| `thrustspeed >= 6000` | no | `160 - 8*d` |
| below 6000 | yes | `256 - 16*d` |
| below 6000 | no | `256 - 8*d` |

6. Consume exactly one byte and hit on strict `random < chance`. Chance at
   least 256 always hits but still draws; chance at most zero always misses
   but still draws.
7. Only a hit consumes a second byte. Damage is `random >> 2` for `d < 2`,
   `random >> 3` for `d < 4`, and `random >> 4` otherwise.
8. Call `TakeDamage`, then emit the firing sound. A qualified miss still
   sounds. SS has its distinct sound; guard/officer/mutant use the ordinary
   Nazi firing sound.

Representative pinned vectors are:

| Case | Visible / speed / distance | Hit bytes | Chance / result |
|---|---|---|---|
| guard strict edge | yes / 0 / 2 | `223,0` | 224 / hit, damage 0 |
| guard strict miss | yes / 0 / 2 | `224` | 224 / miss, one draw |
| exact run boundary | yes / 6000 / 2 | `255` | 128 / miss |
| hidden guard | no / 0 / 2 | `239,0` | 240 / hit |
| same cached tile | yes / 0 / 0 | `255,255` | 256 / hit, damage 63 |
| far guard | yes / 0 / 20 | `0` | -64 / miss but sound |
| SS raw distance 5 | yes / 0 / effective 3 | `0,255` | 208 / damage 31 |

## `T_Bite`

Dog attack sound occurs first, including an out-of-range action. Current
physical coordinates are eligible when both axes satisfy the inclusive square

```text
abs(player.x - dog.x) <= 0x20000
abs(player.y - dog.y) <= 0x20000
```

An out-of-range bite consumes no RNG. An in-range bite consumes one byte and
hits on strict `< 180`; a hit alone consumes a second byte and deals
`random >> 4`. Thus `179,255` hits for 15 damage with two draws, while `180`
misses with one. There is no area, line, visibility, or thrust gate.

## Player damage

The host pins the original side-effect order, including behavior not yet
needed by the first production fixture:

1. Always publish `LastAttacker`.
2. Victory returns immediately after that write.
3. Baby difficulty quarters points; easy, medium, and hard are identical.
4. God mode suppresses health subtraction only.
5. Health at or below zero clamps to zero, marks death, and publishes the
   killer. A later hit in the same actor pass may overwrite that killer.
6. Damage flash, `gotgatgun=0`, health redraw, and face redraw occur even for
   zero reduced damage and under god mode.

This means a successful zero-damage hit is not equivalent to a miss. An
in-flight attack during victory still performs its gates and RNG and still
sounds; only `TakeDamage` returns early.

## Fixed-step `thrustspeed`

The port publishes requested movement before collision, never actual
displacement. Opposing keys cancel on their signed axis. One unopposed W/S
axis contributes `0x1000`; one unopposed A/D axis contributes `0x1000`.
Rotation, use, and collision contribute nothing. The complete output set is:

```text
no translation or both opposites: 0
one unopposed axis:                4096
forward/back plus strafe:          8192
```

Accordingly a single current movement key is below original `RUNSPEED=6000`,
while a diagonal is at or above it. W+S and A+D contribute zero, including
when both opposing pairs are held.

## Deterministic CPU visibility

The DOS `FL_VISABLE` value was set asynchronously by `DrawScaleds` using
renderer `spotvis` state and could remain stale on several skip paths. The VDP
here is write-only, and render completion is intentionally decoupled from the
30-Hz simulation. Gameplay therefore must not depend on a render callback.

After `T_Shoot` has passed area and `CheckLine`, the replacement projects the
actor center synchronously from authoritative CPU pose:

1. Subtract actor minus player full 16.16 X/Y, then arithmetically reduce each
   to signed 8.8. A 64x64 map fits the signed word.
2. Load the player's normalized 0..359-degree Q12 forward basis from the same
   generated motion table used for movement: `(cos, -sin)` in map-Y-down
   coordinates.
3. Compute each signed Q8-by-Q12 product with source `FixedByFrac` semantics:
   truncate its magnitude toward zero before adding terms.
4. Compute

```text
forward = relX*cos + relY*(-sin)
lateral = relX*sin + relY*cos
nx      = forward + 0x17
```

5. Reject `nx < 0x58`. Otherwise compute C-style signed truncation
   `screenX = 127 + trunc(lateral * 87 / nx)` and accept inclusive columns
   `0..255`.

The assembly may avoid division with equivalent strict products:

```text
lateral < 0: abs(lateral)*87 < nx*128
lateral >=0:     lateral *87 < nx*129
```

This is a deliberate clean replacement, not an attempt to preserve stale
renderer quirks. Occlusion remains `CheckLine`'s job. Exact projection vectors:

| `(relX Q8, relY Q8, heading)` | `(forward,lateral,nx,screenX,visible)` |
|---|---|
| `(512,0,0)` | `(512,0,535,127,true)` |
| `(-512,0,0)` | `(-512,0,-489,none,false)` |
| `(0,-512,90)` | `(512,0,535,127,true)` |
| `(65,0,0)` | `(65,0,88,127,true)` |
| `(64,0,0)` | `(64,0,87,none,false)` |
| `(233,-374,0)` | `(233,-374,256,0,true)` |
| `(233,-377,0)` | `(233,-377,256,-1,false)` |
| `(233,377,0)` | `(233,377,256,255,true)` |
| `(233,380,0)` | `(233,380,256,256,false)` |
| `(512,-512,45)` | `(724,0,747,127,true)` |
| `(70,-140,1)` | `(71,-138,94,0,true)` |
| full delta `(-1 LSB,-200 Q8,30)` | reduced `(-1,-200)`, then `(100,-173,123,5,true)` |

The generated 45-degree basis is exactly `(2896,-2896)`; 315 degrees is
`(2896,2896)`. The final one-degree vector pins per-product truncation toward
zero: a plain negative arithmetic shift would produce lateral -139 and place
that exact center incorrectly at screen column -1.

## Running the regression

From this directory's `scripts/` subdirectory:

```sh
python3 -m unittest -v test_combat_oracle.py
```

The accepted host corpus reports 39/39 tests. It pins every state record and
link, action-before-NEXT and overshoot, source and `2,2,3` timelines, all 16
translation-key combinations, near-plane and both screen-edge boundaries,
cardinal/diagonal projection, area/line ordering, unclamped chance extremes,
strict RNG thresholds and exact draw counts, all damage bands, SS distance,
sound order, zero damage, baby/god/victory/death behavior, multi-shot
re-evaluation, and the bite square's inclusive one-LSB edges.

### Direct production-eZ80 regression

From the repository root, run:

```sh
python3 src/asm/wolf3d_combat/scripts/run_combat_emulator_regression.py --timeout 60
```

The runner assembles `src/combat_regression.asm` against the production
`wolf3d_actor_sim.inc` and `wolf3d_motion.inc`, boots the stock VDP emulator
headlessly, and reads a fixed 32-byte MOS-file mailbox. The ten phases cover
all 24 state records, class entry, scheduler timing and overshoot, shoot
gates/chance/damage, CPU projection, thrustspeed, bite boundaries, player
damage/death, malformed-state containment, and timing. Literal fixture
expectations live in the assembly rather than being generated by the host
oracle.

Accepted result on 2026-07-31:

```text
PASS: 298 direct production-combat eZ80 checks across 10 cases
binary: 48311 bytes
sha256: b68499e151e2828ef26649f26c3a212aa8473be8b6298a0ff306e051cb509e06
PRT1: 10,000 clear-line ordinary shots: 1555 ms (0.1555 ms/call)
PRT1: 10,000 in-range dog bites:          87 ms (0.0087 ms/call)
```

The PRT1 measurements come from loops containing only the production action
call; setup and result comparisons remain outside the timed region. They are
the current emulator's measurements, while using the same eZ80 timer idiom
available to a hardware run.

Source anchors are `orig/src/WOLFSRC/WL_ACT2.C` (`T_Shoot`, `T_Bite`, and the
five state families), `WL_AGENT.C` (`ControlMovement`, `Thrust`, and
`TakeDamage`), `WL_PLAY.C` (`DoActor`), `WL_STATE.C` (`NewState`), and
`WL_DRAW.C` (`FixedByFrac`, `TransformActor`, and original visibility).
