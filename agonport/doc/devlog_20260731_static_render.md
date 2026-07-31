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
Firmware SHA-256:

```text
6b7c5d5193a2e992a779335ba87498af76e186a993d3a615538c49022ff1535d
```

See `first_correct_render_success_story.md` for the milestone narrative and
qualification summary.
