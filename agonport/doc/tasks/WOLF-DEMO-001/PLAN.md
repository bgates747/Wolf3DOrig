# WOLF-DEMO-001 — Try a hardware sprite for the Demo label

Smith selected the VDP hardware-sprite path as the first trial for the
missing attract-mode label. This task is recorded for later execution.

1. Use the stock `SPR_DEMO` graphic from sprite 0 in `VSWAP.WL1` and match
   the position, apparent size and transparency of the DOSBox reference.
   The original draws it over the weapon and scales it with the viewport.
2. Use the VDP hardware sprite as a scanout overlay above both framebuffer
   pages in Wolf’s double-buffered mode 136. Prepare and upload the bitmap
   at the needed size once so the same sprite stays visible across page flips.
   Check clipping, layering and scanline load with the actual bitmap on the
   pinned firmware.
3. Own one sprite and keep its backing valid throughout playback. Show it
   with the first demo frame. Hide and retire it on demo completion, key
   abort and fatal exit, before exposing the next shell screen or MOS.
4. When released for testing, compare against the DOSBox reference on the
   four attract demos. Check that the label stays stable across buffer
   flips and that it clears on input and after the demo. Compare uncapped
   presentation cadence and watch for scanout glitches with the label on
   and off. Record any blocker and bring it back for review before choosing
   a fallback.

The source reference is `DrawPlayerWeapon` in `orig/src/WOLFSRC/WL_DRAW.C`.
Use the [firmware pins](../../../../FIRMWARE.md) and the [Olimex bench
guide](/Agon/mystuff/agon-extender/docs/operations/olimex-bench/README.md)
if a hardware trial is selected. Implementation and testing await Smith’s
direction.
