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

## Console8 playtest observations

Smith confirmed that the High Scores display errors are fixed. He heard a
brief music skip as the attract loop entered High Scores. The opening demo
rendered without the previously reported wall clipping. During the E1L1 and
E1L3 demos, he saw movement blocked around doors and noticed that gun aim
looked off.

The recordings contain player inputs. The original applies each record for
four 70 Hz ticks. The port samples the records on its 30 Hz simulation clock,
which preserves average duration while changing individual movement steps.
The port also uses a sliding collision plane for doors, while the original
keeps a door tile blocked until fully open.

One definite replay defect is independent of collision. The port computes an
unsigned forward or strafe distance but passes it to signed multiplication.
A full forward input requests 35,000 units per port step, interpreted as
−30,536 by the multiplier. E1L1 has 14 records with movement above the signed
limit, first at about 5.1 seconds. E1L3 has 29, first at 3.6 seconds. The
original also applies strafe before forward or backward motion. The port
reverses that order. Eight E1L1 records combine both axes, while E1L3 has zero
combined-axis records. The exact first door or shot divergence has yet to be
isolated.

### Stock DOSBox comparison

Smith confirmed that the original replay lines up shots and kills guards
more reliably than the Console8 port. In the first-floor demo, the original
replay opens a secret pushwall, enters the room and collects loot. The
Console8 replay never reaches that room. These are observed differences in
the replay. The exact input where the paths first diverge remains unknown.

The DOS reference also displays the stylized Demo overlay during playback.
The original draws `SPR_DEMO` over the weapon. The stock WL1 asset is present
as sprite 0 in VSWAP chunk 106, but the four demo levels' sprite packages omit
it. No planned deferral was found in the demo lifecycle work. The next trial
will display it over the weapon using a hardware sprite.
[WOLF-DEMO-001](../WOLF-DEMO-001/PLAN.md)
