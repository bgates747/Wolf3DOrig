# Wolf3D direct colour-row review

This bounded review demonstrates an exact renderer with a sharply smaller
caller workspace, not a faster renderer. The direct-row path saves 80,608
workspace bytes (87.47%) but costs about 33% more modeled foreground RENDER
transaction cycles than the accepted copied-pixel control in this scene.

This separate stopped profile reviews the optional direct-row rendering path,
not the Wolf3D game or a replacement production loader. The already accepted
copied-pixel scene remains the control and its original review profile is not
changed.

## Roles

- `source/wolf3d_scene_rows.cpp` is the direct module source under review. It
  draws every scene pixel into borrowed hidden SBGR2222 rows and uses no copied
  colour frame.
- `wolf3d_scene_rows.vdpl` is the exact uploaded direct package.
- `source/wolf3d_scene.cpp` and `wolf3d_scene.vdpl` are the byte-identical
  copied control. They are supplied for provenance and are not invoked by this
  review host.
- `review.bin` only uploads the direct package and scene, invokes CONFIG and
  RENDER, swaps after successful completion, waits for one key, unloads,
  clears owned buffers/callback state, and restores the saved MOS mode/cursor.
  It draws no scene pixels.
- `reference.png` is the accepted standalone-renderer oracle. The host does
  not display or copy it into the framebuffer.

## Later review procedure

Only after automated JIT and interpreter receipts pass and Golem grants an
Author slot, launch the stopped project-local profile using its canonical
wrapper:

```bash
cd ~/Agon/mystuff/Wolf3dOrig/.emulator/vdplet-rows-review
./flexe-agon-emulator
```

1. Confirm that the recognizable brick chamber, textured perspective walls,
   transparent yellow billboard, and wall occlusion match the accepted scene.
2. Press any key once. This requests the normal unload and cleanup path.
3. Confirm that the application reports successful review completion and
   returns cleanly to MOS with its mode, cursor, callback, and owned buffers
   restored.
4. Close the emulator and report the visual result.

No second terminal command or verifier is requested. This preparation does not
authorize launching the profile, physical flashing, full-game integration,
default replacement, publication, commit, or push.

## Rehearsal status

The exact staged profile passed one no-GUI full-MOS rehearsal under central
Oryx generation 27 on 2026-10-30. The live direct-row scene matched the
reference PPM byte for byte; INFO reported capability value 287; LOAD, CONFIG,
RENDER, and UNLOAD returned their expected replies; injected Enter traversed
the real `mos_getkey` path; direct-module success/restoration text and the
`/wolfrows *` prompt appeared; the frontend exited normally; and backend
failed, unhandled, unregistered, and unmapped counts were zero. The ignored
receipt is `build/rehearsal/rehearsal-run/rehearsal.json`, SHA-256
`cdea3c7bf9175be6031f968bee3490639a3509bb772e306f4139282aefa35c77`.

Raw evidence was preserved separately, then only test-created outputs were
removed from the Oryx profile. Its runtime manifest and launcher reverified,
the host was empty, generation 27 was released, and the profile is again
stopped. This is automated emulator evidence, not human or physical
acceptance.

## Human result

The Author completed the bounded visual and keyboard review on 2026-10-30.
The displayed direct-row scene matched the accepted reference in composition
and occlusion. A single key took the normal UNLOAD and cleanup path, returned
to MOS, and `dir` worked at the restored prompt. This accepts the intended
one-shot emulator review flow. It does not accept physical hardware, the full
game, a default cutover, or publication.

The Author then typed `run` manually at the MOS prompt. That second invocation
reached the diagnostic path because this review-only guest retains its
transaction counter: the successful first run leaves five transactions and a
second run reaches ten while the one-shot assertion still expects five. The
second invocation nevertheless produced valid replies through UNLOAD. This is
a fixture rerun limitation, not a renderer, runtime, cleanup, keyboard, or
first-run failure. Do not rerun this one-shot guest in the same emulator
session; changing it would require requalification of the accepted fixture.

The raw human-review evidence was preserved in the ignored
`build/human-review/` tree. Generation 29 was explicitly released after the
profile outputs were retrieved and removed, the runtime manifest and launcher
were reverified, and the Oryx host was confirmed empty. The profile is stopped.
