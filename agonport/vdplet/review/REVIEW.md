# Bounded Wolf3D VDPlet human review

This stopped Oryx profile demonstrates only the fixed GOLEM-057 renderer
scene. It is not the Wolf3D game, a production loader, or a new renderer. The
standalone Wolf firmware remains the production oracle and rollback path.

## What code draws what

- `source/wolf3d_scene.cpp` is the exact freestanding C++ source compiled into
  `wolf3d_scene.vdpl`. The module draws every pixel of the reviewed 320x240
  RGB222 frame: border, ceiling/floor, textured brick chamber, and the partly
  occluded yellow billboard.
- `review.bin` is an eZ80 host only. It checks the runtime capability mask,
  uploads the exact package and scene inputs, requests CONFIG and RENDER,
  swaps the completed hidden frame, waits for one key, unloads, releases its
  buffers, clears the MOS callback, restores a single-buffered MOS mode, and
  enables the cursor.
- The host draws no label or overlay on the reviewed frame. Its explanatory
  text appears before the scene and after the reviewer dismisses it.
- `reference.png` is the expected module-only frame from the preserved
  standalone renderer oracle. It is supplied for comparison and is not shown
  by the guest or copied into the emulated framebuffer.

## Review procedure

The central coordinator launches this stopped profile only under an Author
Oryx lease:

```bash
cd ~/Agon/mystuff/Wolf3dOrig/.emulator/vdplet-review
./flexe-agon-emulator
```

1. Wait for the fixed Wolf scene. Compare it with `reference.png` if desired.
2. Confirm that the brick walls have perspective and texture, the yellow
   billboard is transparent around its silhouette, and walls correctly occlude
   part of it.
3. Press any key once to dismiss the scene.
4. At the restored MOS prompt, type `dir` and report that it works.
5. Close the emulator window and report whether the scene and keyboard looked
   correct.

There is no second verifier command for the reviewer. Agent-side retrieval of
`results.dat` and runtime pins happens only after the stopped review closes.
The fixture does not authorize physical flashing, full-game integration,
publication, or replacement of the standalone renderer.

## Rehearsal status

The exact staged profile passed a no-GUI full-MOS rehearsal under central Oryx
lease generation 6 on 2026-10-30. The live 320x240 RGB capture matched
`reference.ppm` byte for byte; INFO, LOAD, CONFIG, RENDER, and UNLOAD replies
all succeeded; injected Enter traversed the guest's real `mos_getkey` path;
and the success text and restored `/wolfvdpl *` MOS prompt were observed. The
frontend returned normally and backend failure/unhandled/unregistered/unmapped
counts were zero. The ignored receipt is
`build/rehearsal/rehearsal.json`, SHA-256
`0faa05cf710a0efdca80a27ee17db3d49acce28864fbe6f62d31b54bfed44f60`.

That result is automated emulator evidence only.

## Human result

The Author completed the visual/keyboard review on 2026-10-30 and supplied
screenshots of both required states. The first shows the expected module-only
Wolf scene with the textured perspective walls, transparent yellow billboard,
and wall occlusion. After one-key dismissal, the second shows the review
success text, restored `/wolfvdpl *` MOS prompt, and a successful `dir`
listing. The emulator was closed afterward and a fresh whole-host inspection
reported no emulator process.

This accepts the bounded emulator scene and MOS keyboard/restoration path. It
does not claim physical-hardware qualification, full-game integration, or
publication approval.
