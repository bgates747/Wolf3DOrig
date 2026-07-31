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
