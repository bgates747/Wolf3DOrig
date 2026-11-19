# WOLF-WEAPON-001 — Pre-scaled weapon comparison

## Host comparison

The 20 original first-person frames (shapes 416–435) have identical RGBA2222
bytes across all ten level packs in the verified local game payload. The trial
used the actual production `draw_view_weapon` for the control and Rally’s
extracted VGA64 ordinary bitmap plot for the two prepared-bitmap arms. The
extracted graphics commit `ac2dd598` matches the pinned release. The fixture
compared a full 161×160 prepared image and the same image cropped to its opaque
bounds, with the plot origin adjusted accordingly.

Both arms matched all 800 whole-surface comparisons in the ordinary and
ASan/UBSan builds. These cover all 20 frames, two patterned backgrounds, and all
ten accepted color states (no shift, six red and three bonus shifts). For the
shifted cases, the probe simulated plotting after the renderer’s palette pass
by applying that same remap to opaque pixels in the prepared bitmap.

| Path | Median Pi CPU time per draw | Prepared RGBA2222 bytes, all 20 |
| --- | ---: | ---: |
| Current per-draw scaling | 28.96 µs | — |
| Ordinary plot, full prepared rectangle | 26.03 µs | 515,200 |
| Ordinary plot, cropped prepared rectangle | 6.20 µs | 75,010 |

The timing column is the median of the 20 per-frame medians, with six
alternating-order trials of 250 draws per arm per frame. The median paired
draw-time reduction was 10.5% for full plots and 78.6% for cropped plots. The
cropped five-frame sets use 9,930 B (knife), 17,125 B (pistol), 16,899 B
(machine gun), and 31,056 B (chaingun). These figures exclude bitmap metadata
and extra shift variants. The separate host prep-and-crop sample was about
2.40 ms for all 20 frames together. The measurements are for an isolated Pi CPU
kernel with warm buffers. Native VDU dispatch, ESP32 memory behavior, scanout,
and visible frame cadence remain unmeasured.

## Runtime and hardware-sprite considerations

- The pinned release supports ordinary VDU bitmap selection and 1:1 plotting.
  A module calling `vdu_submit` needs the VDU capability and must end its
  borrowed color-frame lease first (`vdplet_runtime.h`, `submit`). FabGL runs
  ordinary bitmap primitives inline in mode 136 (`displaycontroller.cpp`,
  `addPrimitive`). Wolf’s existing C3 remains the page flip. The HUD begins
  at y=200, below the weapon’s clipped bottom at y=179.
- A plot after the lease ends also follows Wolf’s whole-frame palette remap.
  The probe shows that a correctly remapped prepared bitmap reproduces the
  original flashes. Keeping one cropped set plus the current draw for shifted
  frames is another candidate to evaluate for ordinary plotting. All ten
  complete color sets would cost up to 750,100 pixel bytes before deduplication.
- Mode 136’s VGA64 ISR decorates the scanout line after copying it from the
  visible page. The hardware overlay checks every source pixel across the
  clipped bitmap width on each affected row, including transparent ones.
  The largest cropped source is 131×84 (shape 433). The tallest is 113×94
  (shape 434). Report both maxima alongside the Demo overlap once the Demo
  fixture is measured. Crop origins vary by frame, so a single moving/cropped
  sprite must match the frame’s new origin when the animation changes. If the
  selected interface cannot update both together at the intended presentation
  boundary, measure the common-origin bounds and timing as a separate arm.
- Scanout may see a hardware-sprite change independently of the framebuffer
  flip. Check whether animation and position stay aligned with the game page,
  and measure whole-screen output and renderer time with Demo and weapon
  together. An emulator color comparison cannot establish that scanout budget.

The cropped ordinary plot is the first candidate for a native comparison.
The 75,010 B figure is a pixel budget, not a measured device-resident cost.
The production game still uses the current renderer.
