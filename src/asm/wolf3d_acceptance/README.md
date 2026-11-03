# Wolf3DOrig acceptance profiles

This project creates disposable, ignored VDPlet application payloads for
visual acceptance of scenes which are expensive to reach through ordinary
play. It never edits `orig/data`, the generated standard level tree, or the
production package. Each scenario starts from a copied canonical W3L package
and receives only the documented pose or actor substitutions below.

Run:

```bash
.venv/bin/python src/asm/wolf3d_acceptance/scripts/prepare.py
```

The generated payloads appear under `src/asm/wolf3d_acceptance/tgt/`:

- `pushwall`: real E1L1, one tile south of the original secret wall at
  `(10,13)` and facing north. Press Up once to start the wall, then watch it
  move two tiles and verify that the newly revealed passage is traversable.
- `ordinary-transition`: real E1L1, inside the ordinary elevator facing its
  switch. Press Up once to display the completed-floor screen and enter E1L2.
- `secret-transition`: real E1L10, inside its return elevator facing the
  switch. Press Up once to display the secret-floor completion screen and
  enter E1L2.
- `hans`: real E1L9, one door away from Hans Grosse. His canonical full hit
  pool is preserved for the selected difficulty (850/950/1050/1200), while
  this copied application suppresses player damage so Hans's complete firing
  animation can be observed indefinitely. Hans has no original pain
  animation; his alternating firing frames are not hit feedback. Production
  builds remain mortal.
- `victory`: real E1L9, one step south of the center EXITTILE and facing
  north. Walk forward once to trigger the original in-world player spin and
  BJ run/jump sequence, then review the total-time/average-ratio victory
  screen and two-page Episode 1 ending text.
- `ghosts`: real E1L10 geometry with four copied actor slots replaced by the
  four original ghost classes in one open room around the player. The
  shareware `VSWAP.WL1` does not contain the paid game's ghost shapes
  288--295, so this disposable fixture adds four brightly colored synthetic
  two-frame diagnostic ghosts to its copied `sprites.agnb`. They validate
  movement, contact damage, and state transitions, not original artwork.
- `pause-resume`: real E1L1 at the canonical starting pose. Press Escape,
  verify the in-game End Game / Back to Game / Quit panel, choose Back to Game,
  and confirm that the same level state resumes with a clean complete frame.
- `highscore-qualifying`: after the real startup load, enters the production
  high-score path with a guaranteed qualifying score. Type and edit a name,
  press Return, verify the inserted row, persistence write, and menu return.
- `highscore-nonqualifying`: enters the same production path with a guaranteed
  non-qualifying score. Verify the original table and its finite timeout (or
  dismiss it with a key), followed by the main menu.

The application still shows the ordinary title/menu/difficulty flow. Selecting
any difficulty enters the scenario's chosen floor; every difficulty package is
patched identically. Escape retains the production clean-exit path. Each
payload also carries the separate `help.agnb`, so Read This/F1 exercises the
same on-demand 41-page article as production.

`prepare.py` writes an `expected.json` manifest compatible with the existing
VDPlet profile stager. These are review artifacts, not release payloads.

After generation, stage all nine hash-pinned, stopped Oryx profiles with:

```bash
.venv/bin/python src/asm/wolf3d_acceptance/scripts/stage_oryx.py
```

The stager replaces only these ignored acceptance profiles, verifies every
runtime/payload hash, and never launches a GUI or reserves Oryx by itself.

## Oryx visual review

The currently prepared stopped profiles live under:

```text
/home/smith/Agon/mystuff/Wolf3dOrig/.emulator/wolf3d-acceptance-r01/
```

After Oryx is available again and the Wolf3D agent holds the shared FIFO
checkout, the Author can launch one scenario at a time on Oryx with:

```bash
cd ~/Agon/mystuff/Wolf3dOrig/.emulator/wolf3d-acceptance-r01/pushwall && ./flexe-agon-emulator
cd ~/Agon/mystuff/Wolf3dOrig/.emulator/wolf3d-acceptance-r01/ordinary-transition && ./flexe-agon-emulator
cd ~/Agon/mystuff/Wolf3dOrig/.emulator/wolf3d-acceptance-r01/secret-transition && ./flexe-agon-emulator
cd ~/Agon/mystuff/Wolf3dOrig/.emulator/wolf3d-acceptance-r01/hans && ./flexe-agon-emulator
cd ~/Agon/mystuff/Wolf3dOrig/.emulator/wolf3d-acceptance-r01/victory && ./flexe-agon-emulator
cd ~/Agon/mystuff/Wolf3dOrig/.emulator/wolf3d-acceptance-r01/ghosts && ./flexe-agon-emulator
cd ~/Agon/mystuff/Wolf3dOrig/.emulator/wolf3d-acceptance-r01/pause-resume && ./flexe-agon-emulator
cd ~/Agon/mystuff/Wolf3dOrig/.emulator/wolf3d-acceptance-r01/highscore-qualifying && ./flexe-agon-emulator
cd ~/Agon/mystuff/Wolf3dOrig/.emulator/wolf3d-acceptance-r01/highscore-nonqualifying && ./flexe-agon-emulator
```

Close each emulator before launching the next. These commands are launch
instructions, not authority to bypass the shared Oryx reservation protocol.
