# Devlog — 2026-07-31 — Wolf3D level-0 static render

## Goal

Produce one visible, persistent render of the original Wolfenstein 3D
shareware level 0 from the player's original first position. This fixture is
deliberately static: load the real level textures and tilemap, submit the
initial doors and player pose, render once, and leave that frame on screen.

## Repository boundaries

- eZ80 fixture: `/home/smith/Agon/mystuff/Wolf3dOrig`
- custom VDP: `/home/smith/Agon/mystuff/agon-vdp-wolf3d`
- owned Fab integration checkout:
  `/home/smith/Agon/mystuff/fab-agon-emulator`
- ignored project-local emulator profile:
  `Wolf3dOrig/agonport/emulator`

The custom VDP should follow the coding conventions mined in
`agonport/doc/vdp-coding-conventions.md`: core `video/` style is tabs,
camelCase names, and same-line opening braces. Pingo is useful only as a
source of proven lifecycle/presentation idioms, not as a coding-style
template.

## Starting worktree state — preserve

`Wolf3dOrig` already had these user/agent changes:

```text
 M src/asm/wolf3d/README.md
 M src/asm/wolf3d/src/wolf3d.asm
?? agonport/tools/wolf3d_assets/scripts/gen_render_fixture.py
?? src/asm/wolf3d/src/wolf3d_fixture.inc
```

`agon-vdp-wolf3d` already had active renderer work:

```text
 M video/vdu_buffered.h
 M video/wolf3d.h
 M video/wolf3d/render/README.md
?? userspace/wolf3d_smoke
?? video/wolf3d/hud/
?? video/wolf3d/render/wolf3d_draw.h
?? video/wolf3d/wolf3d_world.h
```

Do not discard or overwrite these changes.

## Claude-to-Codex VDP checkpoint

Before Codex changed any custom-VDP source, the inherited renderer work was
committed in `agon-vdp-wolf3d`:

```text
commit: 3c228a60ad0f0e0bd190ad2d012bda7de262ca78
tag:    claude-to-codex
message: Checkpoint Wolf3D renderer at Claude-to-Codex handoff
```

The annotated tag message is:

```text
Wolf3D VDP development switches from Claude to Codex
```

The generated x86-64 executable `userspace/wolf3d_smoke` was deliberately
excluded. After the checkpoint it is the only remaining untracked item in
that repository.

## Reproduction and qualification completed

1. Built and smoke-tested the custom native module:

   ```bash
   make -C /home/smith/Agon/mystuff/agon-vdp-wolf3d/userspace \
     FAB_ROOT=/home/smith/Agon/mystuff/fab-agon-emulator smoke
   ```

   The smoke harness resolved the full Fab ABI and exercised Wolf3D
   subcommand 0 plus render-notification registration. Module SHA-256:

   ```text
   3622509bc507b33648e48e15787ae8bf2f78307553aef3d5cb65aaeba981f2c6
   ```

2. Verified `nm` contains all required Fab exports and `ldd` reports no
   missing libraries.

3. Generated level 0 to a temporary include and compared it byte-for-byte
   with the working-tree fixture. It matches. Fixture facts:

   ```text
   level_00 / Wolf1 Map1
   player tile: (29,57)
   player angle: 0 degrees / east
   doors: 22, initially closed
   command stream: 385 bytes
   fixture include SHA-256:
   4bb8cfb35c88f0eaf3a09b45c9b73da2e7104044b97e19108e2a099943e87788
   ```

4. Assembled `src/asm/wolf3d/src/wolf3d.asm` successfully. Binary:

   ```text
   17,317 bytes
   SHA-256 a15d60e68f869b1648abed8ef395ce64e533f85d26a0ecc333fe339366e23771
   ```

5. Rewired only the ignored `agonport/emulator` profile to the matching
   owned Fab executable/MOS, the custom module, the fixture binary, and
   level-0 `tiles.agnb`. `autoexec.txt` uses CRLF and runs:

   ```text
   SET KEYBOARD 1
   cd wolf3d
   load wolf3d.bin
   run
   ```

6. Proved fail-closed behavior: a nonexistent `AGONPORT_VDP` is rejected by
   `agonport/tools/run_emulator.sh` before Fab starts.

7. Interactive reproduction: all texture bitmaps and tilemap buffer 2 load;
   the eZ80 prints the loading and rendering messages, then prints
   `Done -- frame sent, holding.` No Wolf3D image remains visible.

## Confirmed behavior of “holding”

The fixture does not wait for a keypress. It deliberately loops forever:

```asm
hang:
    jr hang
```

This was intended to preserve a successful one-shot frame. The message only
proves that subcommand 7 returned synchronously.

## Investigation and resolution

The display lifecycle omissions above were real but not the root cause. The
fixture now uses a callback-driven foreground loop modeled on
`earth-party-local`, retains a 120 Hz elapsed-time sample for the future
fixed-step simulation, permits only one render in flight, and presents a
validated `W3DR` completion with `C3`. Mode 8 is currently used so `C3` is a
VSync fence rather than a buffer swap. The custom VDP boot variant is branded
`Wolf3DOrig`.

A native host framebuffer probe loaded the real `tiles.agnb`, replayed the
exact generated command stream, and produced more than 31,000 non-black view
pixels. All 256 rays hit geometry. A real-emulator wire trace then confirmed
that subcommands 41, 1, all 22 door updates, 2, and 7 arrived intact, that
`render_frame` completed, and that `C3` executed. This ruled out renderer
math, the generated level fixture, presentation dispatch, and suspected ADL
corruption of the Wolf3D command stream.

The decisive diagnostic plotted every uploaded 64x64 texture using the
canonical bitmap commands before submitting the render. Before the fix, the
VDP trace showed:

```text
bufferWrite: stored stream in buffer 4097, length 4096
vdu_sys_sprites: bitmap 4097 selected
drawBitmap: bitmap 4097 not found
```

The pixels reached VDP buffer storage, but no VDP bitmap object was created.
The fault was in the vendored `agnb_dependencies.inc`:

```asm
@cmd:       db 23,27,$20
@bufferId:  dw 0
@end:
vdu_bmp_create:
```

In ADL mode, `ld (@bufferId),hl` writes three bytes. With no excluded padding
after the two-byte wire field, HLU overwrote the first opcode of the adjacent
`vdu_bmp_create` routine every time an image was finalized. Adding one byte
at `@end` preserves the five-byte command length while safely absorbing HLU:

```asm
@bufferId:  dw 0
@end:       db 0 ; ADL padding for the third byte stored by LD (nn),HL
```

After the fix, the trace reports each texture as a real 64x64 RGBA2222
bitmap, the gallery plots correctly, `render_frame` completes, and the user
confirmed that the real level-0 first-position view is visible. Repaired
fixture binary:

```text
18,280 bytes
SHA-256 773b2577a5794f4beb06ee90014b0d22f6ed6147a16947379cda8bc30867ec5d
```

The same omission existed in the clean canonical
`agon-utils/examples/agnb/api/agnb_dependencies.inc`, introduced when the
reusable API was published in commit `1ffd111a`. The earlier image harnesses
that were tested in the emulator and on hardware still contain the correct
excluded padding byte, and AgonWolf3D uses its separately proven
`vdu_buff_select` helper with that padding. Thus the heavily tested loader
logic was sound while this newly extracted dependency wrapper escaped an
end-to-end consumer test.

The follow-up copy audit found the same extraction mistake in canonical
`vdu_buffer_to_sound`: its final `dw` sample-rate field also lacked the
excluded byte needed to absorb DEU from `ld (@sampleRate),de`. That path was
not used by this image-only fixture. A stale vendor copy at
`golem/reference/agnb-asm/api/agnb_dependencies.inc` contained both defects as
well. Subsequent follow-up work repaired and committed every affected tracked
copy in its owning repository while leaving unrelated dirty files untouched.

## Acceptance test

Complete: a fresh bespoke-emulator launch visibly shows the real level-0
first-position view and leaves it stable on screen.

## Interactive renderer and door-jamb correction

The fixture subsequently became an interactive 30 Hz client: W/S moves
forward/back, A/D strafes, and the cursor keys turn. Simulation advances in
exact four-tick quanta from MOS's 120 Hz clock and stays callback-independent;
the eZ80 sends only the newest player pose when the VDP reports the preceding
frame complete. Mode `8+128` and callback-gated `C3` presentation restore true
double buffering on hardware. The VDP clears the 256x160 gameplay viewport
locally with the original-style light-gray ceiling and dark-gray floor. Its
projection now folds Wolf3D's quarter-pixel scaler convention into the cached
height numerator, fixing the formerly stretched walls without adding a
hot-loop multiply.

Visual inspection then found a door-side artifact: a thin panel beside an
inset door used the normal door face and appeared on a plane parallel to the
door. The original renderer establishes two distinct surfaces:

- the moving door face lies on its tile's half-cell center plane;
- its frame/jamb is the perpendicular boundary face of an adjacent wall and
  uses the dedicated `DOORWALL+2/+3` art.

The custom VDP had treated a center-plane intersection that fell outside the
door tile as a solid hit at the DDA entry gridline. That manufactured the
parallel panel and then selected the door's normal face texture. The corrected
`WallRefresh()` resumes the DDA when the half-cell plane is unresolved. When
the following ordinary-wall hit was entered directly from a correctly
oriented door tile, it keeps that wall-boundary geometry and selects fixed
jamb texture ID 122. No tilemap or wire-format change is needed; level 0's
existing `tiles.agnb` already contains buffer `0x107A` for that texture.

Post-fix qualification:

- native `vdp_wolf3d.so` build and ABI/dispatch smoke test: pass;
- ESP32 `esp32dev` firmware build: pass (82.8% flash, 13.6% RAM);
- fresh fail-closed bespoke-emulator launch and interactive visual acceptance:
  pass.

Interactive acceptance is now complete. The corrected door plane and jamb
geometry were verified in the emulator, the hardware SD deployment was synced,
and the ESP32 firmware was flashed successfully. All four written flash regions
passed esptool's hash verification and the VDP hard-reset cleanly via RTS.

## Roadmap after the first correct rendering pass

The first renderer milestone established enough of the pipeline to start
building gameplay in layers. The next work is deliberately ordered so each
layer has a small, visible acceptance test before later game systems depend on
it:

- **Active now — collision-aware movement and interactive doors.** Recreate
  the original player's wall/door clearance rules on the eZ80, add an
  edge-triggered use key, keep authoritative door animation state in eZ80
  memory, and send only changed door snapshots to the VDP. Door position,
  collision, and rendered moving-face texture coordinates must agree at every
  partial opening.
- **Active now — in-game screen composition.** Import the original shareware
  status-bar art (not splash/title screens), place the 256x160 3D view window
  at its intended centered position above the HUD, and extend the lower panel
  through the extra 40 scanlines in Agon mode 8. Keep the existing projection
  hook so later viewport-size choices do not require ray-loop surgery.
- **Completed — sprite/wall occlusion.** Scaled sprite scratch bitmaps are
  masked column-by-column against the wall-height buffer before their single
  Canvas draw; equality belongs to the wall exactly as in `ScaleShape`.
- **Partially completed — statics and pickups; actors/AI remain queued.** The
  real level statics and authoritative pickup state now exist. Actor state,
  sight/hearing, path selection, and state machines remain independent later
  slices.

The original shareware source is the behavioral oracle for constants,
geometry, state transitions, and naming, but this project continues to use a
clean reimplementation rather than copying its implementation. Durable Python
generators remain the source of generated assembly fixtures and converted
assets.

This round is emulator-only: physical Agon hardware currently carries Pingo
firmware. Do not deploy or flash the Wolf3D VDP during this milestone unless
the user explicitly changes that instruction.
Firmware SHA-256:

```text
6b7c5d5193a2e992a779335ba87498af76e186a993d3a615538c49022ff1535d
```

See `first_correct_render_success_story.md` for the milestone narrative and
qualification summary.

## Gameplay foundation and original status panel

The next layer now keeps gameplay authority on the eZ80 while preserving the
callback-gated renderer established by the first-correct-render milestone:

- Movement uses the original square `0x5800` player radius and `ClipMove`
  ordering (combined X/Y, X only, then Y only). Walls, reserved map bytes, and
  every door except the named `OPEN` state at position `FFFF` are solid.
- Space is a rising-edge use action. Integer-degree sectors select exactly one
  adjacent cardinal tile with the original boundaries, and lock values 1..4
  are already wired to future inventory bits.
- The eZ80 owns all door action, 0.16 position, open timing, reversal, and
  player-obstruction state. A repeating `0955,0955,0956` increment reproduces
  the 70 Hz door travel rate at the 30 Hz simulation step without a multiply;
  the open timer uses third-ticks and clamps at 900 so an obstructed door can
  retry forever without wrapping.
- Only dirty door records and a dirty player pose cross the wire, followed by
  one render request when the preceding callback has completed. Pressing into
  a wall no longer dirties an unchanged pose.
- The VDP subtracts the moving door position before choosing its texture U
  coordinate. Jambs and ordinary parallel wall faces remain unshifted.

The in-game composition has also moved beyond the bare viewport. A new strict
WL1 `VGAHEAD`/`VGADICT`/`VGAGRAPH` decoder extracts only `STATUSBARPIC`,
weapons, keys, digits, and face frames. The durable HUD build packs 44 images
into `hud.agnb`: original chunks use buffer `$4000 + chunkId`, while a composed
320x80 lower panel lives at `$40F0`. Its first 40 rows are byte-identical to
the converted original status strip; rows 40..79 are an explicitly new neutral
blue/cyan extension for mode 8's extra scanlines, not purported original art.
No splash/title assets are included.

The accepted 256x160 view is centered at `(32,0)` above the panel, with the
original dark-cyan play surround in the side margins. The status strip begins
at `y=160`, and the extension occupies `y=200..239`. The VDP redraws the
complete panel and current fields into every hidden buffer before reporting
render completion.

Regression coverage added during this pass:

- 42 host gameplay tests, including 10,000 deterministic randomized collision
  and sliding cases, all 22 generated level-0 door records, command-stream
  parity, cardinal use boundaries, lock behavior, complete door timing, exact
  `FFFF` reopening saturation, and prolonged obstruction.
- 10,017 packed vectors executed against the real eZ80 `ClipMove` assembly in
  an isolated Fab emulator profile, including zero delta, wall thresholds,
  every slide outcome, and door collision states: zero errors.
- Twelve real-data HUD/static decoder, generator, and container tests, plus a deterministic 65,368-byte
  Floyd-built `hud.agnb` (`sha256
  6e796bcfd20d77a5b69113f44a401f23466638312660f03d05e530cdfd2f8c8d`).
- Native VDP DDA regressions for horizontal/vertical moving-door U, the exact
  pass boundary, both jamb orientations, and adjacent parallel wall faces.
  The test fails against the prior renderer and passes against this change.
- The complete eZ80 application assembles, and the bespoke userspace VDP
  build plus ABI smoke test passes. Visual emulator qualification follows
  after the staged changes and generated HUD container are installed together.

Two regressions were found before visual testing: a zero-axis fallback could
mark a blocked player dirty without changing its coordinates, and reopening a
door could land on exactly `FFFF` without changing action from `OPENING` to
`OPEN`. Both now have explicit guards and durable tests.

## Real statics, collision, pickups, and sprite occlusion

The E1L1 plane-1 parser now derives the original non-SPEAR `statinfo[]`
semantics rather than inferring behavior from sprite names. The generated
fixture contains 121 row-major mutable static records: 34 original block-type
decorations, 48 bonus objects, and 39 nonblocking decorations. Its initial
wire stream is 2,079 bytes and sends every `set_static` before player pose and
the first render. `sprites.agnb` is now a required load/deploy asset.

Blocking is intentionally not stored in the shared tilemap. The original
`SpawnStatic` writes block objects into `actorat`, while both block and dressing
records have zero render flags. The eZ80 therefore owns a separate immutable
512-byte LSB-first occupancy bitset: decorations stop the original square
player AABB without becoming opaque DDA geometry. Four new directed/static
records plus randomized static blockers bring the production `ClipMove`
emulator run to 10,017/10,017.

Bonus records remain allocated after collection. Their `shapenum` changes to
the original `-1` sentinel, and only the changed static record plus affected
HUD fields are submitted. Contact is deliberately evaluated in simulation as
pickup-tile overlap with the player's `PLAYERSIZE` AABB after successful
translation. This is a documented port choice replacing the DOS renderer's
visibility-triggered `GetBonus`: collection is deterministic and independent
of write-only VDP state or render cadence. Health/ammo refusal, gibs' health-10
boundary, four keys, treasure values, full heal, weapon upgrades, ammo
saturation, zero-ammo weapon restoration, 40,000-point thresholds, a
persistent 16-bit treasure count, and the original nine-life cap are modeled.

A separate 13-case real-eZ80 pickup harness asserts exact return values,
inventory/statistics, HUD/world/player dirty masks, consumed sentinel, target
static byte, and all 121 dirty bytes. It found and prevented a dispatch-order
error where enum value 2 (`gibs`) was rejected by a later range guard. The
10,017-case collision run likewise caught a register-contract error: the
static bit lookup clobbered `C`, so the caller now reloads both coordinates for
every corner probe.

On the VDP side, projected statics share the actor transform/depth-sort path.
Before each scaled scratch bitmap is drawn, columns whose wall projection is
greater than or equal to the sprite projection become transparent. Native
tests cover the strict depth boundary, clipped viewport offsets, and retained
source transparency while preserving one Canvas operation per sprite.

Future combat integration must re-arm pickup scanning when damage or firing
reduces health/ammo. Today scans follow successful translation, which is
complete for this no-combat fixture; without that later hook, a capacity-
refused pickup would not be reconsidered while the player remained stationary.

Final pre-visual qualification from the installed worktrees:

```text
host gameplay/oracle:              42/42 pass
asset/HUD/static generator:        12/12 pass
production eZ80 ClipMove:          10,017/10,017 pass
production eZ80 pickup state:      13/13 pass
native door/jamb/sprite renderer:  pass
full VDP ABI/dispatch smoke:       pass
wolf3d.bin:                        28,251 bytes
wolf3d.bin sha256:                 f2fed1ddd87428eb2a74ab6649dcc9487ae84268e238bac022f737836d80de21
sprites.agnb sha256:               5e59018f120590b6e9b5f38fc323659e2ac48b55266197bd2864c851b2910c2d
vdp_wolf3d.so sha256:              10ba6479293f893e7f3431f373299debf2e4a4b9d4bf934c9715f1ba895ee89f
```

The ignored emulator profile points at those exact artifacts. Interactive
visual acceptance remains the explicit gate before commit/tag/push.

## Geometric door-well collision follow-up

Interactive review exposed one remaining mismatch between simulation and the
already-correct renderer: the VDP places each thin sliding door on the center
plane of a recessed map cell, but movement still inherited the DOS game's
conservative whole-cell door rejection. The result looked wrong at close
range because the player stopped at the mouth of the recess rather than at the
visible panel.

Movement now tests the square `0x5800` player AABB against the same finite
fixed-point slab used by the renderer:

- vertical doors lie at `x=tileX:8000` and slide along positive Y;
- horizontal doors lie at `y=tileY:8000` and slide along positive X;
- fractions `0..position` are the inclusive opening, while
  `position+1..FFFF` are panel;
- touching the center plane and any remaining panel fraction blocks;
- position `FFFF` has no panel, independently of the action label.

This deliberately differs from the original DOS `TryMove`, which represents a
door in `actorat` and rejects the entire tile. It is the appropriate contract
for this port because it makes movement agree with the actual rendered
geometry and permits natural entry into both door wells. Auto-close
obstruction calls the identical slab/AABB predicate, so a player standing in
clear recess space does not falsely hold a door open.

The hot movement path does not scan all 22 level doors. Because the player
AABB is narrower than one tile, any slab it intersects must belong to one of
the four corner cells already probed for walls/statics. A named door cell is
resolved through IY, preserving the candidate IX, and only that record is
tested. Fractional AABB words are retained alongside the existing tile bytes;
all arithmetic remains explicitly 16-bit where required by the eZ80 register
contract.

New independent coverage pins entry from both wells, exact center-plane
contact from both directions, both orientations, the last passable and first
blocked fractions of a partial aperture, the `FFFE/FFFF` endpoint, ClipMove
escape/slide behavior, and close obstruction. The packed regression ABI stays
40 bytes by assigning former padding byte 36 to door orientation.

Pre-visual qualification of the staged source:

```text
host gameplay/oracle:              49/49 pass (10,000 randomized cases)
production eZ80 ClipMove:          10,028/10,028 pass
main eZ80 application assembly:    pass
wolf3d.bin:                        28,620 bytes
wolf3d.bin sha256:                 6a077c5b4d8fe3412b33f0733b7274b46cbae7d56972833714c70fdc5aca2316
```

Interactive emulator acceptance remains the gate before this work is
committed or pushed.

## Checkpoint before the door-interaction follow-up

This checkpoint deliberately freezes the complete gameplay-and-presentation
round that followed the `first-correct-render` tag, before changing the newly
reported door behavior again. In aggregate, the round delivered:

- a callback-gated, double-buffered 30 Hz client whose fixed-step simulation
  remains responsive when the custom VDP renders more slowly than real time;
- original `ClipMove` ordering, wall collision, edge-triggered door use,
  authoritative door travel/timers/locks, and dirty-only world updates;
- the original centered 256x160 play window and a generated 320x80 lower
  panel, with live health, ammo, score, lives, keys, weapon, and face fields;
- all 121 E1L1 statics from plane 1, including a separate immutable collision
  bitset for the 34 blocking decorations and persistent mutable state for all
  48 pickups;
- original pickup refusal/saturation, keys, treasure accounting, weapon
  upgrades, zero-ammo weapon restoration, 40,000-point extra-life thresholds,
  and the nine-life cap;
- VDP static-sprite projection, stable-slot removal, depth sorting, and
  per-column wall occlusion while retaining one Canvas blit per sprite;
- durable WL1 asset/HUD parsers and generators, deploy support for
  `sprites.agnb` and `hud.agnb`, an independent host oracle, packed real-eZ80
  collision and pickup fixtures, and native renderer/ABI tests.

The custom VDP side of this same checkpoint includes the centered viewport,
flat ceiling/floor and original-style surround, lower-panel composition,
moving-door texture coordinates, correct perpendicular jamb geometry, static
billboards, and the sprite occlusion test target. Build artifacts remain
ignored; only sources, tests, and documentation belong to the checkpoint.

One visual regression is intentionally recorded rather than hidden before the
checkpoint: after replacing the whole-cell DOS door collision rule with the
renderer's center-plane slab, the player reports that door use now works only
from farther back and entry into the recess feels harder, suggesting an
interaction between cardinal use targeting, the player's tile transition, and
the new plane predicate. The tests prove the isolated fixed-point slab cases,
but not yet this complete use/approach sequence in the real E1L1 doorway. The
next change will reproduce that sequence deterministically and reconcile both
systems from this known commit boundary.

## Door-well use invariant: diagnosis and candidate fix

The complete pre-fix checkpoint was committed before investigation as
`2b2dc1a` in `Wolf3dOrig` and `cfc22f9` in `agon-vdp-wolf3d`. The reported
behavior was then reproduced without changing the slab normal.

The old adjacent-only use rule depended on an unstated invariant: the player
could never occupy a door tile. Whole-cell DOS collision guaranteed that
invariant. Center-plane collision intentionally removed it, but Space still
computed only `floor(player)+facing`. At E1L1 door 20 `(32,57)`, the player
starts west and can now reach `x=32.125` with the real `0x1000` movement step.
That correctly places the center inside door tile 32, where the old use code
looked past the door into open tile 33. Backing across `x<32` restored the old
adjacency and made Space work again. A failed press remaining latched until a
sampled release amplified the apparent resistance.

The candidate correction gives a valid door in the player's current tile
priority, irrespective of view direction, and otherwise retains every original
cardinal angle boundary. A current door byte whose index is invalid for the
fixture fails closed rather than falling through to an unrelated neighbor.
Locks and all action/timer/dirty transitions still share the existing single
operation path. No VDP change is involved: vertical and horizontal slab axes
already match the renderer.

The well depth itself is also now quantified. With radius `0x5800` and a panel
at fraction `0x8000`, the camera center can reach fraction `0x27FF` from the
near side or `0xD801` from the far side; the `0x1000` control step lands at
`0x2000`/`0xE000`. Thus the center gains half a tile over the former DOS
rejection boundary, while still retaining the original player clearance from
the visible panel.

Candidate-fix qualification before interactive review:

```text
host gameplay/oracle:              55/55 pass (10,000 randomized cases)
production eZ80 ClipMove:          10,028/10,028 pass
production eZ80 door use:          13/13 pass
main eZ80 application assembly:    pass
wolf3d.bin:                        28,644 bytes
wolf3d.bin sha256:                 f17070445c87edc1610d022380a8f6819ffcd0484abc837573091a4cc3801504
```

Interactive E1L1 review confirmed that doors now work well enough for the
current milestone. Fine tuning of perceived well depth/player clearance is
explicitly deferred, but current-cell and exterior use are accepted. The fix
may therefore be committed as the clean base for actor work.

## First authoritative actor slice

Door behavior was accepted as good enough for the present milestone, so the
next production layer begins from commit `3214b67`. The fixture now decodes
actors directly from the real WL1 plane-1 markers with original difficulty
fall-through, hit points, active/ambush flags, initial states, patrol
destinations, and row-major allocation. Medium E1L1 contains 21 non-player
records: 17 guards, three dogs, and the inert dead guard; six actors begin in
patrol states. Baby/easy, medium, and hard counts are pinned independently as
12, 21, and 38 records.

The eZ80 now owns a fixed 150-slot actor pool, matching the original
`MAXACTORS`; slot zero remains reserved for the player. Byte-sized stable slot
ids replace near pointers in live/free lists and double as VDP actor ids. A
4,096-byte `actorat` grid tracks each markable actor's reserved destination.
The implementation includes deterministic initialization, allocation,
publication, removal, occupancy claim/release, dirty set/remove snapshots, and
the original inclusive one-tile player-versus-shootable-actor collision rule.

Generated durable metadata anticipates rather than fakes the next AI slice:
all floor-area ids, resolved ambush areas, all 18 E1L1 path arrows, and both
area endpoints for every door are retained locally. Door runtime records are
therefore ten bytes, while dirty VDP updates deliberately copy only the
established eight-byte wire prefix.

The actor render ABI has been made camera-independent. VDP subcommand 4 now
takes a 15-byte snapshot:

```text
actorId:u16, baseShape:i16, x:i32, y:i32,
facingDegrees:i16, rotations:u8
```

The VDP derives the view-relative sprite rotation on every render. Stationary
actors no longer need to be resent merely because the player turns. The
native renderer suite covers 0/2/8-frame selection, angle boundaries, actor
lifetime, depth sorting, wall occlusion, culling, and stream length; the full
userspace VDP build and token-matched dispatch smoke pass.

Host actor/fixture tests pin marker decoding, patrol seeding, difficulty
counts, runtime byte layout, command ordering, fake/Mecha-Hitler asset
boundaries, areas, arrows, and door endpoints. Adversarial review additionally
caught and fixed four future-facing faults before integration: recessed door
cells now inherit the original west/north area ownership, empty generated
actor/door/static arrays cannot execute a zero-length `LDIR`, ghosts retain
their original zero hit points, and the graduated DDA regression addresses
the expanded ten-byte door stride. It also identified the exact Fake/Mecha
asset boundary rather than allowing Fake's block to consume Mecha frames.

The durable direct-eZ80 actor harness now passes 10,494 checks. It exercises
all initial records and free slots, every dirty and `actorat` byte, allocation,
publication/removal/reuse, pool exhaustion, sender bytes, inclusive collision
thresholds, and all four fractional-AABB cases where the expanded scan must
reach a reserved destination two tile indices from the candidate center. The
established 10,028-case ClipMove, 13-case pickup, 13-case door-use, and 55-case
host gameplay suites remain green after actor integration.

The interactive emulator view is the remaining acceptance gate before this
slice is considered complete. The staged application currently assembles to
49,581 bytes (SHA-256
`d9523a17ee8e440cad54fe05741f3b6ed9fd9c540992e54b76129bf667b8a39f`).

The state-runner, patrol, area-connectivity, awareness, chase, and combat
sequence is recorded in `agonport/doc/actor_gameplay_plan.md`.

## Original-timed path patrols

The next actor layer retains the original `statetype` durations directly in
70 Hz tics. A single global `2,2,3` cadence advances them at the client's
fixed 30 Hz, exactly consuming seven original tics every three updates without
division or a per-actor fractional field. Actor records therefore remain 39
bytes. The generated map seed now reproduces `US_InitRndT(false)` and
`SpawnNewObj`: medium E1L1's six timed patrol records receive row-major phases
`8,9,0,2,1,9`. The zero is not normalized away. Original `DoActor()` treats
it as a permanent non-transitional W1 state while still calling `T_Path`, and
the port deliberately preserves that visible quirk.

The compact state table now contains all six path states for guards, dogs,
officers, mutants, and SS actors. It carries signed transition overshoot,
calls only the final state's think once, avoids dirtying the duplicate-shape
W1/W3 pause transitions, and caps corrupt transition graphs at sixteen before
removing the bad actor. State ids remain stable generated-data values rather
than code pointers.

`T_Path`, `SelectPathDir`, `TryWalk`, and `MoveObj` are now eZ80-owned. The
implementation preserves physical position versus ahead-tile reservation,
plane-1 arrow turns, residual motion through a tile center, diagonal corner
checks, shootable versus inert occupancy, guard/dog differences, the negative
door-wait encoding, AI opening that ignores locks, and inclusive one-tile
player exclusion. Doors update first, then player input/pickups, then actors.
Only pose/facing/render-shape changes cross the write-only VDP boundary.
Moving doors also test live actor AABBs before continuing to close.
An actorat reservation in the door cell holds even a fully open door first,
matching the original `CloseDoor()` invariant before the finite-slab checks.
Its original adjacent-cell `MINDIST` check is retained at close start as well,
so a patrol that has reserved the far-side tile cannot have the door begin
closing around its still-crossing body.

An independent host oracle and versioned `W3PV` corpus exercise the shared
clock, zero latch, animation dirtiness, dog residual/arrow motion, door
selection/wait ordering, player rejection, and a real 92-frame slot-11 route
through E1L1 door 8. Its 24 host tests pass. After linking the runner, all
pre-existing gates remain green:

```text
asset/fixture host tests:           26/26 pass
gameplay host/oracle:               55/55 pass
production actor pool:              10,494 checks pass
production actor patrol/state:      550 checks pass
production ClipMove:                10,028/10,028 pass
production pickups:                 13/13 pass
production door use:                13/13 pass
main eZ80 application assembly:     pass
wolf3d.bin:                          51,827 bytes
wolf3d.bin sha256:                   5e2569615f2b6e6f671946b6863ecbb1c52489f9a8d3ef6986f79a41834317f9
```

The 550 direct checks include all ten independent `W3PV` cases, malformed
state/occupancy defenses, diagonal and static blocking, moving-door
obstruction, and the exact far-side `MINDIST` close boundary. PRT1 measures
the real 92-frame E1L1 slot-11/door-8 route at 15 ms total, or about
0.163 ms per fixed frame in the emulator. Interactive emulator review is the
remaining acceptance gate after this staged slice replaces the live worktree.

## Lean door-area connectivity and inactive-actor scheduling

The client now owns the original level's 37-area reachability without carrying
the DOS engine's 37-by-37 counter matrix. Each ten-byte door record already
contains its two area endpoints, so one 37-entry iterative BFS scans the live
records directly. A door is an undirected graph edge exactly while its unsigned
0.16 position is nonzero; action labels do not affect connectivity. Parallel
doors, cycles, and self-loops therefore fall out of the same traversal.

Opening's first zero-to-positive step and closing's final positive-to-zero step
mark topology dirty. The complete door pass performs at most one rebuild, so
simultaneous transitions do not reflood repeatedly. A player-area change also
rebuilds before pickups and actors run. Invalid player roots clear the table and
fault once per sampled-value transition; malformed live door endpoints are
ignored and fault once per door per rebuild. The bounded implementation uses 86
bytes, including the 37-byte reachability table, 37-byte queue, diagnostics,
and scratch state.

`ACTIVE_NO` actors now run only in a valid area reachable from the player.
`ACTIVE_YES` and `ACTIVE_ALWAYS` remain global, and eligibility never mutates
the durable active byte. The same area gate limits MoveObj's player-proximity
rejection, while `w3d_CheckSight()` independently rejects invalid actor areas.
The generator now fails closed on actor and live-door areas outside `0..36` and
on levels exceeding the 64-door wire/index budget. Regenerating E1L1 remains
byte-identical (`wolf3d_fixture.inc` SHA-256
`227f7f41706bbbbbffc2a2d94c94178f5c259a92f548cf9267b173194e813389`).

An independent host oracle pins synthetic graph behavior and the exact real
E1L1 components. A separate assembly fixture calls production labels directly,
compares every reachability byte and relevant scalar/door field, and verifies
BC/DE/HL/IX/IY preservation. Independent review found no remaining production
defect. The complete pre-visual gate is:

```text
asset/fixture host tests:           29/29 pass
gameplay host/oracle:               55/55 pass (10,000 randomized cases)
actor patrol host/oracle:           24/24 pass
area host/oracle:                   18/18 pass
production actor pool:              10,494 checks pass
production actor patrol/state:      550 checks pass
production area connectivity:       1,288 checks pass
production DDA/CheckSight:           20,112/20,112 pass
production ClipMove:                10,028/10,028 pass
production pickups:                 13/13 pass
production door use:                13/13 pass
main eZ80 application assembly:     pass
wolf3d.bin:                          52,542 bytes
wolf3d.bin sha256:                   ff928e665ece60a63c22f6a1fb36714bdd49ad897e7f72bcca125a32e9b6b2b8
```

With the area hooks linked, PRT1 measures the same 92-frame real E1L1 patrol
route at 16 ms total (about 0.174 ms per fixed frame) in Fab. Interactive
emulator review remains the acceptance gate before committing this emulator-
coupled slice. Awareness/noise activation is the next actor layer.

## Ordinary actor awareness and reaction staging

The next staging layer ports `SightPlayer()` and the ordinary-class portion of
`FirstSighting()` without conflating them with chase movement. Guards,
officers, mutants, SS, and dogs now detect only from valid connected areas.
Non-ambush noise bypasses facing and the complete line trace; ambush actors
ignore noise, require visual sight, and clear the ambush bit at acquisition.
Quiet visual checks reuse the already-regressed strict 1.5-tile proximity,
eight-direction facing, and wall/door DDA implementation.

Detection seeds the original class delay and returns before activation. The
pending delay consumes the shared `2,2,3` original-tic cadence before any area
or sight revalidation, exactly preserving the DOS behavior if a door closes
during the reaction. Activation installs the class chase-entry state, ten
tics, speed multiplier, and `ATTACKMODE|FIRSTATTACK`; it cancels a negative
door wait but does not change position, tile reservation, direction, area, or
persistent activity. Chase entries intentionally self-loop without motion
until the next direction-selection layer is independently regressed.

The exact 256-byte `US_RndT` table/index convention is now shared runtime
state. Fixture generation records the post-spawn E1L1 index as 6, making the
first gameplay draw table entry 7 (`107`). The officer's fixed two-tic delay
consumes no byte. A one-byte player-noise event remains asserted for every
actor in the current pass and clears only after the complete list traversal.

Qualification of this staging checkpoint:

```text
asset/fixture host tests:           29/29 pass
gameplay host/oracle:               55/55 pass (10,000 randomized cases)
actor patrol host/oracle:           24/24 pass
area host/oracle:                   18/18 pass
awareness host/oracle:              21/21 pass
production actor pool:              10,494 checks pass
production actor patrol/state:      550 checks pass
production area connectivity:       1,288 checks pass
production actor awareness:         321 checks pass
production ClipMove:                10,028/10,028 pass
production pickups:                 13/13 pass
production door use:                13/13 pass
main eZ80 application assembly:     pass
wolf3d.bin:                          53,366 bytes
wolf3d.bin sha256:                   416982060450c647fdccd0fd9595a2bdb7773e968521480903f6713c9ea237ca
wolf3d_fixture.inc sha256:           8e43379689917603c3325ad6a81c4888d33156ec3fdc586d79340b1e5405bfde
```

The awareness fixture calls production labels directly in the stock isolated
emulator. Its 321 checks cover RNG continuation/wrap, every ordinary delay,
area and visual gates, noise/ambush paths, countdown, every FirstSighting
mutation and non-mutation, corrupt-input removal, and whole-pass noise
lifetime. PRT1 measured 10,000 connected quiet visual acquisitions in 1,099 ms
(0.1099 ms/call), with comparisons and file I/O outside the timed loop.
Independent adversarial review found no production defect. The earlier
20,112-case DDA/CheckSight result remains applicable because this slice changed
only its caller and explanatory comment, not the trace implementation.

## Ordinary chase and dog pursuit

The ordinary chase layer now follows the source `T_Chase`, `T_DogChase`,
`SelectChaseDir`, and `SelectDodgeDir` ordering against the authoritative eZ80
world. Guards, officers, mutants, and SS run the line/attack probe before
direction or movement; dogs project their complete movement budget before
requesting a jump. The first-attack reversal exception, exact `128/129` RNG
split, cardinal/diagonal occupancy, closed-door waits, dog door rejection,
residual travel through tile centers, and reservation release/reclaim are all
preserved. Attack decisions are explicit results from the chase routine, so
the state runner can install the appropriate animation without coupling the
direction oracle to combat side effects.

The direct production corpus passes 703/703 checks across nine phases after
the combat records expanded the shared table to 101 states. Its current binary
is 49,881 bytes, SHA-256
`27e224f017b185cffe037b9a6fa137dcab7934d106f3ce9877c6bff3084e2bd1`.
PRT1 measures 10,000 clear close-range ranged requests in 743 ms
(0.0743 ms/call) and 10,000 projected dog-jump requests in 128 ms
(0.0128 ms/call). Assertions, fixture reset, and mailbox I/O remain outside
the timed loops.

## Ordinary enemy attack chains and player damage staging

The next slice appends the original 24 attack states at stable ids 77..100:
three guard shooting states, five dog jump/bite states, three officer shooting
states, four mutant states with two shots, and nine SS states with four shots.
Actions execute on the expiring state before `NEXT`, signed overshoot is
retained, and the final transition reaches the already-qualified chase graph
in the same scheduler call. Ranged and dog-jump chase requests now install the
full first-state duration instead of remaining unlatched seams.

`T_Shoot` revalidates area connectivity and `CheckLine` at action time, derives
the source Chebyshev tile distance (including SS's `floor(2d/3)` adjustment),
and preserves unclamped chance arithmetic, strict comparison, and conditional
damage draws. `T_Bite` uses the exact inclusive `0x20000` physical square and
draws no RNG outside it. Player damage records the last attacker, quarters on
baby difficulty, saturates health at zero, and allows a later hit in the same
actor pass to replace the killer. Death freezes later world quanta while the
foreground still polls Escape and can submit the final health/dead-face HUD.
Sound, damage flash, god/victory presentation, and respawn are deliberately
deferred; durable gameplay state is the current boundary.

The DOS hit chance depended on renderer-owned `FL_VISABLE`, but this port's VDP
is write-only and rendering is intentionally asynchronous. The replacement is
a synchronous CPU projection from authoritative actor/player pose after the
area and line gates. It uses the generated Q12 motion basis, the original
`FixedByFrac` per-product truncation toward zero, the original transform
constants reduced to signed 8.8, and exact strict product inequalities for the
inclusive 0..255 screen interval. It consumes no additional RNG and cannot
make simulation depend on render completion.

Two eZ80-specific review catches are worth retaining. First, an unsuffixed ADL
store of the new uint16 `thrustspeed` field wrote a third byte over player
health; all new two-byte fields are now loaded/stored bytewise. Second, an
arithmetic right shift initially rounded negative Q8-by-Q12 products toward
minus infinity; adding `0x0fff` to non-exact negative magnitudes restores the
source's truncation toward zero. Independent adversarial review then found no
remaining production defect. The independent host combat corpus passes 39/39
tests. The direct production fixture passes 298/298 checks across ten phases;
its 48,311-byte binary has SHA-256
`b68499e151e2828ef26649f26c3a212aa8473be8b6298a0ff306e051cb509e06`.
PRT1 measures 10,000 clear-line ordinary shots in 1,555 ms
(0.1555 ms/call) and 10,000 in-range dog bites in 87 ms
(0.0087 ms/call). The complete earlier direct matrix also remains green,
including 10,494 actor-pool checks, 607 patrol checks, 1,288 area checks, 321
awareness checks, 703 chase checks, and 10,028 ClipMove vectors.

## Ordinary combat emulator and hardware acceptance

The complete staged actor stack was integrated into the live client and built
as a 56,360-byte `wolf3d.bin`, SHA-256
`3de852653caaa2a594b288dac87be42cafc79d60cc7738dba2f3d55c76aeb4b4`.
The existing level-0 sprite container was independently checked before launch:
all guard shapes 50..98 and dog shapes 99..137 are present, including the
shoot and jump/bite frames. No VDP or asset-format change was required for
combat presentation.

Interactive emulator acceptance passed. The real medium-difficulty E1L1
population acquires the player, follows the authoritative eZ80 chase paths,
animates attacks, reduces the live HUD health, and reaches the deliberate
dead-face/frozen-world latch. Render callbacks continued advancing while the
simulation remained independent of variable render time. Combat sound, player
weapons, actor injury/death, drops, and respawn remain explicit later layers.

The same client and its `tiles.agnb`, `sprites.agnb`, and `hud.agnb` containers
were deployed to `/wolf3dorig` on the FAT32 `AGON` card. `autoexec.txt` selects
keyboard layout 1, changes to that directory, and loads `wolf3d.bin` without a
`run`; prior application commands remain commented and the previous file is
preserved as `autoexec.pre-wolf3dorig.bak`.

The current custom VDP was rebuilt from source and flashed to the hardware
ESP32-PICO-D4 through `/dev/ttyUSB0`. PlatformIO reported 83.0% flash and 13.6%
RAM use. All four flash regions passed esptool hash verification, RTS hard
reset succeeded, and the serial device re-enumerated. The 1,087,792-byte
firmware image has SHA-256
`4093eeb054b9494f169c02d576b2d0fd0a7699e09996fc8984eb0d5d80384463`.

Hardware acceptance passed: the complete fixture works, remains eminently
playable under load, and preserves correct simulation behavior. The observed
input/render response may be a touch laggy on hardware, which is retained as a
performance note rather than a correctness failure. This checkpoint is tagged
`ordinary-combat-hardware-pass` in both `Wolf3dOrig` and
`agon-vdp-wolf3d` so the matching eZ80 and VDP sides can be recovered together.
