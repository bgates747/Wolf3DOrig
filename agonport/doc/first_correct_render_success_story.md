# From a blank screen to Castle Wolfenstein on Agon

## First correct rendering milestone — 2026-07-31

Wolfenstein 3D's original shareware level now renders correctly and moves
interactively on real Agon hardware through a bespoke VDP firmware path. The
result is recognizably Wolf3D: properly proportioned walls, inset half-cell
doors with perpendicular jambs, flat gray floor and ceiling, smooth movement,
and tear-free double-buffered presentation.

This is the first end-to-end proof that the project's split architecture
works. The eZ80 owns persistent world and simulation state; the VDP owns the
per-column raycast and pixel rendering. They communicate through compact
Wolf3D-specific buffered commands rather than trying to ship a framebuffer or
read render state back from the write-only VDP interface.

## What crossed the finish line

- The real Episode 1, level 1 map and VSWAP wall/door art are extracted by a
  durable Python toolchain, converted to RGBA2222, scoped per level, and packed
  into the modern AGNB container format.
- The eZ80 client uploads that real tilemap, initializes all 22 doors, owns the
  player pose, and sends only changed render state.
- W/S move forward and backward, A/D strafe, and the arrow keys turn. Movement
  uses a generated 360-entry fixed-point delta table: no runtime trigonometry
  or multiply is needed for the current fixed-speed fixture.
- Simulation advances in exact four-tick quanta from MOS's 120 Hz clock, giving
  a deterministic 30 Hz model independent of render time.
- Only one render is in flight. A tiny interrupt callback publishes validated
  `W3DR` completion records; foreground code performs the `C3` buffer swap.
  Slower rendering drops stale visual snapshots without slowing world time or
  allowing held-key input to pile up.
- The custom VDP renders the original 256x160 gameplay viewport into mode
  8+128, clears floor and ceiling locally, and presents complete hidden frames
  without hardware flicker.

## The bugs that made the result worth earning

The first runs loaded assets and reported success but left a black screen. A
canonical bitmap command template contained a two-byte wire field immediately
before executable code. In ADL mode, `ld (nn),hl` wrote HLU as a third byte and
self-modified the following routine. Restoring the deliberately excluded
padding byte fixed the entire bitmap creation path and was propagated to the
other affected Agon projects.

The next visible render proved the raycaster but stretched walls vertically.
The original engine stores projected height in quarter-pixel units and shifts
inside its scaler. Folding that conversion into the VDP's cached projection
numerator restored the original proportions with no new hot-loop multiply.

Hardware then exposed framebuffer flicker hidden by the emulator's speed.
Returning to mode 8+128 and swapping only after a validated completion made
presentation deterministic on the real machine.

Finally, door frames revealed a subtle geometry error. A door occupies the
center plane of its cell; when a ray misses that plane, the original DDA keeps
tracing until it reaches the perpendicular neighboring wall face. Treating the
miss as a solid door had manufactured a parallel strip with the normal door
texture. Resuming the DDA and selecting jamb texture 122 on the correctly
oriented wall boundary restored both the perspective and the art.

## Qualification

The milestone was exercised in the bespoke emulator and then on hardware:

- native VDP ABI/dispatch smoke test: pass;
- ESP32 target build: 82.8% flash, 13.6% RAM;
- every ESP32 flash region: write hash verified;
- flashed firmware SHA-256:
  `6b7c5d5193a2e992a779335ba87498af76e186a993d3a615538c49022ff1535d`;
- eZ80 client SHA-256:
  `3a98dfe023cf8cd6f122365d1e7ee06a67273ffbbf1d1bf8765a707458a6530c`;
- level-0 tile container SHA-256:
  `9990d79e3ae47d0c940e072f70f821d505d9e39ce21f713b38f5d8c7237502c8`.

Interactive visual acceptance was emphatic. The first real map can be walked
through smoothly, the door geometry now reads correctly, and emulator-only
success has been replaced by a verified hardware result.

## Credit and significance

This milestone stands on the author's existing hand-written Agon assembly,
the original Wolf3D source used as a behavior reference, and a long sequence
of deliberate architectural decisions: local ownership of simulation state,
binary-friendly fixed timesteps, callback-gated rendering, reusable asset
containers, and hardware-first validation. Codex accelerated the integration,
debugging, and implementation, but the project direction and much of its
assembly vocabulary were already the author's work.

The important result is larger than one attractive fixture. We now have a
proven path for an eZ80 game to drive a custom VDP raycaster while remaining
responsive under variable rendering load. Collision, doors in motion, actors,
sprites, AI, and a scalable viewport can be added without revisiting the core
simulation/render ownership model.

Both implementation repositories mark this point with the annotated tag
`first-correct-render`.
