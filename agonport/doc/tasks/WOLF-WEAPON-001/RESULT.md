# WOLF-WEAPON-001 — Pre-scaled weapon comparison

## Host comparison

The 20 original first-person frames (shapes 416–435) have identical RGBA2222
bytes across all ten level packs in the verified local game payload. The trial
used the actual production `draw_view_weapon` for the control and Rally’s
extracted VGA64 ordinary bitmap plot for the two prepared-bitmap arms. The
extracted graphics commit `ac2dd598` matches the pinned release. The fixture
compared a full 161×160 prepared image and the same image cropped to its opaque
bounds, with the plot origin adjusted accordingly.

The two arms passed 800 whole-surface comparisons per build, in both the
ordinary and ASan/UBSan builds. These cover all 20 frames, two patterned
backgrounds, and all ten accepted color states (no shift, six red and three
bonus shifts). For the shifted cases, the probe applied the renderer’s palette
remap to opaque pixels in the prepared bitmap before plotting it.

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

## Alexe ordinary plot

Oryx checkout 505 refused the November 9 backend dependency record before
starting Alexe. The current host has `libc6:amd64` version `2.43-2ubuntu2.7`.
The libc, libm and loader digests changed, while `ldd` resolved the same paths
and the other four library digests matched. The three changed files verified
against the installed package. Checkout 505 was released with an empty host.
Checkout 506 bound the current libraries before running the same backend,
firmware, assets and test sequence. [Library identities](ORYX-CLOSURE.json)

All 20 cropped plots stayed off the visible page until C3. All 20 then
matched the RGB oracle pixel for pixel on alternating colored backgrounds.
The worker used the ordinary public VDU bitmap commands in mode 136. Backend
`d77a7305` ran firmware `dc43ecb8` with ELF `576b69f3`. The supervisor completed
in 9.35 seconds at 55.625 °C peak, with boost off. Alexe reported zero unhandled,
unregistered, or unmapped events. The worker exited and Oryx was released with
fresh idle evidence. This run exercised the ordinary unshifted plot command.
Color shifts were checked in the host comparison.

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
  (shape 434). At the planned stock center and the current scale, the cropped
  Demo label is 138×52 at (91, 26). It occupies rows 26–77, while the highest
  cropped weapon frame starts at row 86. The two sprites would occupy
  separate rows with at least eight rows between them. That is an estimate
  from the asset bounds at this viewport. The scanout routine checks every
  active sprite on every line, so disjoint coverage still incurs extra work.
- Crop origins vary by frame, so a tightly cropped weapon sprite needs both a
  new bitmap and a new origin when the animation changes. One fixed origin at
  (98, 86) avoids moving the sprite on frame changes. Padding each frame only
  on its top and left to use this origin takes 190,068 pixel bytes for all
  20. This keeps the same eight-row minimum gap while adding transparent
  pixels to process. Treat it as a separate trial if frame and origin updates
  cannot be synchronized.
- Scanout may see a hardware-sprite change independently of the framebuffer
  flip. Check whether animation and position stay aligned with the game page,
  and measure whole-screen output and renderer time with Demo and weapon
  together. An emulator color comparison cannot establish that scanout budget.

The cropped ordinary plot is the first candidate for a full-game native
comparison. Measure the real plot after the row lease ends and include its
dispatch cost. The 75,010 B figure counts pixel data only. Full-game timing,
device memory, and physical scanout with both overlays remain open.
