# WOLF-WEAPON-001 — Investigate pre-scaling the weapon and hand

The current `draw_view_weapon` scales the active first-person weapon and hand
frame directly into the back buffer on each draw. Prepare each needed animation
frame once at the active viewport size and reuse it across frames. Try an
ordinary 1:1 bitmap plot into the back buffer first. Compare that with selecting
the prepared frames for one VDP hardware sprite in mode 136. Use the existing
combined weapon and hand artwork where a frame contains both.
[Current draw path](../../../vdplet/production/wolf3d_renderer.cpp)

## Source review

1. Inventory the stock ready, attack, and firing frames, including the knife
   and hand. Match the current sampling, placement, clipping, and transparency.
   Check the supported ordinary bitmap plot for transparency and draw-page
   ordering on the pinned firmware. Estimate scaled bitmap memory, preparation
   time, and frame-selection cost. Compare keeping all frames resident with
   preparing only the active weapon’s set. Couple the cached dimensions to the
   active viewport so a later resize cannot reuse stale frames.
2. Use the [Demo sprite trial](../WOLF-DEMO-001/PLAN.md) to inform setup,
   layering, and scanline load for the hardware-sprite path. The weapon may
   cover a different screen area. Check the VDP compositor’s bitmap format,
   clipping, and per-line work. Establish whether transparent areas still cost
   scanline work.
3. Check how animation changes would stay in sync with the displayed page.
   Preserve the Demo label above the weapon and keep the weapon inside the 3D
   viewport. Account for palette fades and damage flashes, and for hiding the
   sprite on transitions out of gameplay or attract playback.

## Native trial if selected

Use matched scenes and animation sequences in mode 136. Compare the current
per-frame scaling with ordinary plotting of the pre-scaled bitmaps first. Then
compare ordinary plotting with the hardware sprite using the same scaled
frames. Compare each weapon path with the Demo overlay off and on to measure
the effect of sharing scanlines. Include the widest weapon frame and the
largest per-line overlap with Demo. Record the number of scanlines touched,
pixels covered per line, and sprites sharing a line. Observe the entire output
for scanout errors and watch for delayed animation or frame-selection glitches
during page flips.
Use the [firmware pins](../../../../FIRMWARE.md) and the [Olimex bench
guide](/Agon/mystuff/agon-extender/docs/operations/olimex-bench/README.md).

Measure one-time preparation separately from renderer time with drawing
included and uncapped presentation cadence with frame intervals. Compare
ordinary plotting with the current path to measure the effect of removing
per-frame scaling. Then compare the hardware sprite with ordinary plotting to
see whether scanout composition saves more time or slows other rendering.
Report memory cost and any visible scanout failure alongside the timings.
Recommend which path is worth pursuing and document the tested scanline load.

This task records an investigation. Implementation and testing await selection.
