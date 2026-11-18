# WOLF-PROD-002 — Full game ready on Console8

The plan was frozen and pushed as `bbe7ff0` before integration. Smith’s
pushwall acceptance was recorded in `6402a67`. The full-game client was
built from `c473c1e` with the accepted production renderer `7490d81c`.

The normal game now positions the high-score numbers in their columns and
leaves five clear pixel rows below the headers. Recorded demos sign-extend
turn deltas to the eZ80’s full register width. The renderer receives the
newly loaded floor’s map before it draws the first pose, including during
attract playback and ordinary floor transitions.

The 310,055-byte executable has SHA-256
`47fdb5736d6c6437915c098b97dbf5708c39cae4126229e6e974f1db8ef031ba`.
The normal deployment payload was updated. Its 40 level-state packs and all
other stock assets matched the previous regular game byte for byte. E1L1
starts at (29, 57) and has the original texture and actors at every
difficulty. The renderer is byte-identical. The linked map operand and both
score-spacing operands matched the intended values. All 32 host tests and
six subtests passed. The prior 53-check demo regression and High Scores
layout evidence remain in [WOLF-SECRET-001](../WOLF-SECRET-001/RESULT.md).

All 71 files in `/mystuff/wolf3dorig` on the Console8 SD card verified after
sync. The card's `autoexec.txt` and existing `wolf3d.cfg` were preserved. Both
pinned firmware images are at the top of the deployment directory. The card
was left mounted on Oryx, and the previous marked fixture was archived on
Oryx outside the card. Local assembly, package and transfer receipts are
under `build/`.

At the MOS prompt, enter the following commands.

```text
CD /mystuff/wolf3dorig
LOAD wolf3d.bin &040000
RUN .
```

For the idle check, dismiss sign-on and wait through High Scores and the four
recorded demos on E1L1, E1L3, E1L5 and E1L7. For ordinary play, start a new game
from the menu. Physical acceptance is pending Smith’s playtest.
