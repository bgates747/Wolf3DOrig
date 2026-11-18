# WOLF-SECRET-001 — Alexe test

Use the fixture payload from prepare.py with the pinned release firmware
and FX224 Alexe frontend and backend. Use the existing SDL headless input
and capture shim from FX249's donor. The fixture launcher only loads the
game. The automated test types RUN . and navigates the normal menus.

Use one finite run on Oryx with the normal checkout. Capture the boot,
menu, marked wall, moving wall and settled position. Check that a second
Use leaves the wall in place. Walk into the passage and check that the view
stops changing while forward is held against the final wall. These captures
exercise the game client and renderer together. They cannot directly read
the secret counter or prove collision state in every intermediate frame.

Abort within 240 seconds, at 80 C or below 512 MiB available memory.
Join the owned emulator process, retrieve captures and verify idle before
release. The human playtest, if requested, uses the separate load-only
profile.

Run 02 keeps the original failed capture and uses a fresh profile directory.
It waits for visible title content for up to 135 seconds before sending menu
input, within the original 240-second total limit.

Run 03 accounts for the sign-on and rating screens. Run 02 saw the real
Episode 1 selector and stopped one screen before difficulty. Run 03 compares
the viewport while walking against the final wall, excluding the animated HUD.

Run 03 loaded the accepted renderer and entered E1L1, but the fixed wait after
difficulty selection left the live player exposed until death. Run 04 watches
for the first frame containing the stencil and sends Use immediately. It
selects the easiest stock difficulty for the test.

Run 04 proved the game received the modified spawn and new texture, but
its first 4 KiB tilemap upload still used the stock tile ID 4 at (10, 13).
It also showed guards killing the player in the test room. The next isolated
payload changes the same tile in the embedded map, one data byte in the copied
client, and omits enemies from the E1L1 fixture packages. It keeps executable
code and the accepted VDPlet module byte-identical.

Run 05 rendered the stencil at spawn and during motion. A fixed two-second
host wait proved too short for this emulator. Run 06 waits for the production
client's completed pushwall record, checks its origin, destination, direction,
texture and completion count, then checks repeat Use and walking the passage.

## Prepare another copy

Run the fixture builder from the project root against the verified local
production payload. Choose a fresh output directory.

```sh
mkdir -p agonport/doc/tasks/WOLF-SECRET-001/build
.venv/bin/python agonport/doc/tasks/WOLF-SECRET-001/prepare.py \
  agonport/doc/tasks/WOLF-SECRET-001/build/payload
```

For Alexe, use the current-release profile preparation in the
[project preparation guide](../../../../tools/README.md) with that payload.
At the MOS prompt enter `RUN .`. Follow the stock sign-on, rating and title
screens to New Game, Episode 1, and a difficulty. The marked panel is directly
ahead. Press **Up Arrow** once to push and **W** to walk into the passage.

The copied `build-receipt.json` identifies the accepted base build. The fixture's
`payload.json` identifies the actual run files and the data byte changed in the
copied executable.

To check the idle path, dismiss the sign-on once and leave the keyboard
alone. The rating, title, credits and High Scores should appear, followed by
the recorded demo. Its Use and movement can push the wall from the modified
fixture spawn. A completed demo returns to the title. Press a key on the
title to open the menu for manual Episode 1 play.
