# WOLF-SECRET-001 — E1L1 marked pushwall tested

The plan was committed and pushed first in `2119a15`. The isolated fixture
passed on Alexe with the accepted production game code and exact VDPlet module
`7490d81c`. The test used the pinned VDPlet async-r1 release and Eirene RC3 MOS.

The fixture reuses the earlier E1L1 spawn at tile (10, 14), facing north.
A new texture on wall (10, 13) reads **PUSH ME**. Its wall texture ID is 63,
within the existing 1–63 pushwall range. Up Arrow activates it. W walks forward.

The stock game uploads an embedded tilemap before the new game's motion
initialization loads the runtime map. The first test with modified level
packages still uploaded stock wall ID 4. The successful fixture changes the
same tile in both maps. The copied game binary differs from the accepted
binary by one embedded tilemap data byte at zero-based offset 152756.
The fixture's four E1L1 packages also omit nonplayer actors so the player can
watch the wall without being killed. The production game, renderer, level
packages and stock textures were verified against their original payload hashes.

On Oryx generation 491, the same stencil appeared on the standing, sliding and
settled wall. The real game sent a completed wall record with one completion,
texture 63 and final tile (10, 11). A second press left the viewport unchanged
and produced no additional wall update. The player moved from (10.5, 14.5)
through the opening and stopped at (10.5, 12.3125) while forward remained held.
The original 3D viewport and post-hold viewport captures establish a visible
change and a stable stop. The pass recorded zero backend faults and verified
the returned evidence and clean Oryx release.

All 30 existing preparation tests and six subtests passed. An offline
comparison of the 68 payload entries verified that the only changed run files
were the copied app, E1L1 tile art and the four E1L1 difficulty packages.

Earlier runs had a short startup wait, incomplete menu input, or a capture
after the player died. The retained captures then identified the embedded map
and the need to wait for a confirmed wall completion before repeating Use.
Run 06 completed in 61.8 seconds. Its evidence is in [EVIDENCE.json](EVIDENCE.json)
and local captures are under `build/r06/returned/test/`.

Smith accepted pushwall behavior after playing the marked fixture on Console8,
closing Phase A item 11 and WOLF-SECRET-001. The guest's secret tally, fresh-game reset, and
collision throughout the sliding interval were outside the measured run.
The wire carries the completed-wall count, which is distinct from the
in-game secret tally. [Locations](LOCATIONS.md) · [Fixture preparation and controls](RUN.md)

## Console8 playtest and idle startup

Smith confirmed that manual Episode 1 entry at the default difficulty showed
the expected pushwall behavior. Music and sound effects were acceptable on
Console8. He heard markedly worse audio from the same fixture on Alexe.

With no input after sign-on, Console8 drew the numeric high-score fields
over the names at the left of the screen. The attract loop then started the
first recorded demo. Its movement and Use controls acted on the marked fixture
spawn, so the wall moved without keyboard input. The demo exited to MOS with
`stage=0C status=03 value=0001 callback=00`.

The original fixture reproduced both defects on Alexe with the pinned VDPlet
and MOS. Both renderer attempts received generation 34 with player angle
`0xFEF1` (the preceding angle was 90°). The demo supplied `0x00FFFF` in the
24-bit turn register for a −1° turn. The ADL addition saw a large positive
delta, and the wrap subtraction left `0xFEF1` in the serialized angle. The
renderer correctly rejected that value outside 0–359°. The demo now extends
the sign through all 24 bits. The focused demo regression checks the upper
byte for positive and negative turns.

The high-score code computed each right-aligned X coordinate in `BC`, then
called the formatter a second time. The formatter used `BC` as scratch,
leaving the draw at X=0. The corrected path formats once before positioning
and draws the decimal glyphs against the existing Level and Score anchors.

The rebuilt fixture uses the same level packages, marked texture, music,
effects, and accepted renderer module. The application and its two receipts
are the only changed payload files. Both fixes are in common client source.
The marked map and modified spawn remain specific to the test fixture.

On Alexe, the corrected fixture rendered the Level and Score columns and
played through the first demo to the title with no guest input after sign-on.
All 1,399 submitted pose records had legal angles. The generation 34 turn
published 89° and the marked pushwall settled at (10, 11). There were no
VDPlet errors in 1,547 submitted updates. The runner used a full-frame title
match that missed the changed footer background on return. Independent
comparison confirmed all 208 rows above the footer matched the original title
and the following credits appeared. The remote shell returned 143 after the
emulator wrote its clean result. The owned emulator was joined and fresh idle
evidence supported normal Oryx release. The separate direct eZ80 demo
regression passed 53/53 checks and exited normally. The 30 preparation tests
and six subtests passed.

The corrected 71-file Console8 package replaced `/mystuff/wolf3dorig` on the
Console8 SD card. All package hashes matched after syncing, including the
two original firmware images. The existing `wolf3d.cfg` was preserved. The
card was left mounted on Oryx after transfer. Local evidence is under
`build/console8-idle-baseline`, `build/console8-idle-fixed` and
`build/console8-demo-adl`.

The Console8 retest showed the numbers in their correct columns, but the
first row clipped the headers. The backdrop ink ends at y=78 and the row
started at y=76. Moving the first row and the name-entry cursor anchor to
y=84 leaves five clear rows and keeps all seven entries in the 200-pixel
backdrop. The new fixture executable differs by exactly the two operands for
that shared constant. All game assets, renderer and firmware match the
previous package.

The 30 preparation tests and six subtests passed. Both fresh Alexe attempts
hit the Oryx temperature limit before startup. Offline composition using the
shipped backdrop and glyphs reproduced the previous live capture exactly,
then verified the new gap and all seven rows. The preview is under
`build/console8-score-gap`. The verified bundle is staged on Oryx, and the
card is absent pending deployment.

### Attract demo map selection

The Console8 idle run showed a demo that looked boxed inside one tile. The
original demo streams select E1L1, E1L3, E1L5 and E1L7 in that order. All four
poses are on open tiles in their own level packages. The marked fixture
changes E1L1's stock spawn from (29, 57) to (10, 14) for the pushwall. That
fixture package is also used by the first demo. The later demos use stock
level packages and spawn poses.

The client supplied the current W3L pose to the renderer, but its map upload
read the old mutable map before the new gameplay state was seeded. At the
E1L3 spawn (20, 1), the preceding E1L1 map has a solid wall and every tile in
the surrounding 3×3 is solid. E1L7's spawn likewise overlaps a door cell in
the preceding floor. This mismatch affects the shared level loader and can
occur with the stock payload.

The renderer upload now clears buffer 2 and sends the current W3L's 4 KiB
base map. The linked marked executable differs from the score-spacing build
by exactly one byte in the map-pointer operand. The renderer, firmware and
level assets are identical. The 71-file bundle is verified on Oryx and
includes the score-spacing fix. Tests on the running Console8 remain pending.
Map and binary evidence is under `build/console8-demo-map`.
