# Actor gameplay plan

This document records the implementation boundary between the authoritative
eZ80 game simulation and the write-only Wolf3D VDP renderer. It is deliberately
grounded in the original WL1 source and the real E1L1 map rather than a
synthetic sprite demo.

## Ownership and wire contract

The eZ80 owns every durable actor field: allocation, state, position, facing,
tile reservation, area, hit points, timing, and AI. The VDP owns only a
render-time copy. A camera move must not make every actor dirty.

VDP subcommand 4 therefore consumes this complete 15-byte snapshot:

```text
actorId:u16, baseShape:i16, x:i32, y:i32,
facingDegrees:i16, rotations:u8
```

`rotations` is `0`, `2`, or `8`. The VDP selects the view-relative frame from
the actor facing and current camera at render time. Subcommand 5 removes one
actor by `actorId:u16`. Slot zero is reserved for the player; actor slots
1..149 are stable VDP ids.

## Milestone A: population, lifetime, collision, rendering

The first production slice decodes the original plane-1 actor markers at
build time. Difficulty filtering follows `ScanInfoPlane()` fall-through
semantics. At medium difficulty E1L1 contains 21 non-player records: 17
guards, three dogs, and one dead guard; six living actors begin patrolling.

The generated fixture also preserves two pieces of map state needed by later
AI instead of rediscovering them:

- a 4,096-byte floor-area map, including resolved ambush tiles;
- a 4,096-byte path-direction map containing the original 18 E1L1 arrows.

Each door's authoritative ten-byte eZ80 record retains its two area endpoints.
Only its established eight-byte prefix crosses the wire.

The fixed actor pool mirrors the original `MAXACTORS=150` ownership model.
Near pointers become byte-sized slot links with `0xff` as the sentinel. A
4,096-byte `actorat` array stores the markable actor reserving each map cell.
Allocation, publication, removal, live/free lists, dirty set/remove snapshots,
and player collision are independent of rendering. Player collision follows
the original inclusive `MINACTORDIST` test against shootable actors and scans
the expanded player AABB tile bounds.

## Milestone B: state runner (implemented)

State addresses must never enter generated data. Actor records store stable
16-bit state ids, and a compact assembly state table supplies shape,
rotation-count, duration, think action, transition action, and next-state id.

The client simulates at an exact 30 Hz while the original durations are
defined at 70 Hz. One shared `2,2,3` original-tic cadence advances all actors;
it is exact over three fixed updates and needs neither runtime division nor a
per-actor fractional field. State records retain the original 70 Hz durations.
Zero-duration states remain latched, as does the original edge case where a
timed state is randomly seeded with `ticcount=0`. The generated deterministic
E1L1 patrol phases are `8,9,0,2,1,9`; the zero-phase dog therefore keeps its
W1 render frame while still executing `T_Path`. A 16-transition defensive cap
removes corrupt state graphs instead of freezing the foreground loop.

An actor is sent only when a state transition changes its render shape, or
when simulation changes position/facing. Pure timing and AI bookkeeping stay
local.

## Milestone C: path patrol movement and connectivity (implemented)

Implement original path following first because it exercises persistent
motion without combat:

- retain the source-marker center while the cached `tilex/tiley` reserves the
  one-cell-ahead patrol destination, matching `SpawnPatrol()`;
- consume the generated direction arrows at tile centers;
- release and claim `actorat` cells transactionally;
- multiply the original per-tic speed by the same shared `2,2,3` cadence, so
  motion and state timing consume one coherent original-tic stream;
- mark an actor dirty only after an actual pose change.

The path slice implements the complete guard/dog/officer/mutant/SS six-state
walk chains, arrow turns, ahead-tile reservations, residual movement through a
tile center, cardinal-versus-diagonal blocking, guard door opening/waiting,
dog door rejection, player-overlap rollback, and actor obstruction of moving
door panels. It runs after doors and player input on every simulation quantum,
independent of render completion. Locks are intentionally ignored for AI door
opening, matching the original source.

Door endpoints now feed an eZ80-owned area graph without duplicating the
original 37-by-37 counter matrix. An iterative 37-entry BFS scans the existing
ten-byte runtime doors directly; `position != 0` is the exact undirected-edge
predicate, so parallel doors and self-loops require no special persistent
state. Zero-to-positive opening and positive-to-zero closing transitions batch
one flood after the whole door pass. Player-area changes rebuild the same
37-byte `area_by_player` table before actors run.

Inactive actors are eligible only while their validated area is reachable;
this never promotes their persistent `ACTIVE_NO` byte. `ACTIVE_YES` patrols
continue globally, malformed/free records fail closed, and MoveObj applies its
inclusive player-distance rejection only in a connected area, matching the
original. Generated door endpoints, area-map cells, and actor seed areas now
reject values outside `0..36`, while runtime scheduling and `w3d_CheckSight()`
independently guard the same bound. Exact visual/noise awareness is implemented
in the following layer.

## Milestone D1: ordinary awareness (qualified)

The first combat-facing layer now ports the original `SightPlayer()` and
`FirstSighting()` contract for guards, officers, mutants, SS, and dogs:

- disconnected and invalid areas reject acquisition before noise or sight;
- ordinary noise wakes every non-ambush actor in a connected area without a
  line trace, while ambush actors ignore noise and require visual sight;
- visual acquisition reuses the established exact-near/facing/DDA predicate;
- the original class-specific reaction delay consumes the same deterministic
  `US_RndT` stream left by fixture spawning and counts down on the shared
  `2,2,3` tic cadence;
- reaction survives a later area disconnect, clears a negative door wait,
  installs the class's first chase state and speed multiplier, and sets
  `ATTACKMODE|FIRSTATTACK` without changing pose, direction, reservation,
  area, or persistent activity;
- one noise byte remains visible for the complete actor pass and is cleared
  only after the list is exhausted.

The exact 256-byte Carmack random table is now a durable runtime service. The
generated E1L1 fixture records the post-spawn index (`6`), so the first runtime
draw is table entry 7 (`107`) rather than silently restarting the stream.
Weapon fire and successful actor damage will call the stable
`w3d_mark_player_noise` producer when those systems land.

The awareness oracle retains chase entry as its independently testable layer
boundary. Production now continues from that exact entry into the qualified
chase layer. A 21-test host oracle and 321-check direct eZ80 harness pin area,
proximity, facing, wall/door, ambush, noise, delay, RNG, activation,
corruption-containment, and whole-pass noise behavior.

## Milestone D2: chase and combat (ordinary attacks implemented in staging)

Bring behaviors across in narrow, testable layers:

1. **Qualified:** chase/dodge direction selection, door waiting, occupancy,
   and residual movement while retaining the original first-attack reversal
   rule. The direct production harness passes 703 checks; 10,000 clear ranged
   requests take 743 ms and 10,000 dog jump requests take 128 ms under PRT1.
2. **Qualified in staging:** the exact guard/officer/mutant/SS shooting
   chains and dog jump/bite chain, action-before-`NEXT` timing, deterministic
   action RNG, action-time geometry, and player damage/death. Since the VDP is
   write-only and simulation is render-independent, ranged hit chance uses a
   deterministic synchronous CPU projection rather than the DOS renderer's
   asynchronously maintained `FL_VISABLE` bit. The direct production corpus
   passes 298/298 checks across ten phases. PRT1 measures 10,000 qualified
   ordinary shots in 1,555 ms and 10,000 in-range bites in 87 ms. Emulator and
   physical-hardware acceptance both pass; the hardware result is playable
   with a small amount of perceived latency under the full fixture load.
3. add player shooting, actor damage/death, kill totals, drops, and score/HUD
   dirtiness;
4. add bosses, projectiles, ghosts, and remaining special actions only after
   ordinary guards and dogs are regression-stable.

Every layer should have a host oracle for broad cases and a direct eZ80
harness for register/width behavior. Visual emulator testing is an acceptance
gate, not the only correctness test.

The current compact state dispatcher deliberately keeps stable ids byte-sized:
the ordinary table is 101 records after the attack chains append at ids
77..100. Full WL1 state coverage will exceed that representation, so the
special-enemy rollout must first widen or remap the dispatcher instead of
silently crossing its 254-id containment ceiling.
