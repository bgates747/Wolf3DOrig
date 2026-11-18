# WOLF-PROD-002 — Full-game Console8 retest

Smith accepted pushwall behavior and requested the regular game with the
fixes found during the marked-fixture review. Freeze and push this plan
before integrating or deploying the full game.

1. Record pushwall acceptance and close Phase A item 11 and WOLF-SECRET-001.
   Retain the fixture and its evidence as a reproducible test.
2. Integrate the common-client fixes for High Scores column alignment and
   header spacing, full-width signed demo turns, and renderer map selection
   on level entry. Keep the accepted VDPlet renderer and the ordinary game
   build. Package all ten original Episode 1 levels, every difficulty, and
   the regular shell, audio and gameplay assets. Build directly from the
   normal production sources and generated stock assets.
3. Verify the linked map operand, retained demo-turn regression evidence,
   High Scores layout, stock data, and pinned firmware. Check the new
   payload against the previous regular game. Confirm that E1L1 has its
   original spawn, actors and unmarked secret wall. Publish the verified
   payload to the project's normal local deployment path.
4. Replace the previous Wolf deployment at `/mystuff/wolf3dorig` on the
   Console8 SD card on Oryx. Preserve the player's configuration, saves and
   scores. Include the same pinned VDPlet and MOS images in the deployment
   directory. Synchronize writes, verify readback and leave the card mounted.
5. Return the game build identity, verification and the manual MOS commands.
   Smith will check all four idle demos and play the regular game. The
   deployment result and physical acceptance are recorded separately.

The accepted renderer is `7490d81c`. Console8 firmware follows
[FIRMWARE.md](../../../../FIRMWARE.md). The marked fixture baseline and
the evidence for the three client areas are in [WOLF-SECRET-001](../WOLF-SECRET-001/RESULT.md).
