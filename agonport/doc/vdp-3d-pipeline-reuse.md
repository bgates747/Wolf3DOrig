# Existing VDP 3D/graphics-pipeline building blocks (working notes)

Companion to [devlog_20260730.md](devlog_20260730.md). This tracks existing
`agon-vdp` functionality that a future Wolf3D VDP renderer might reuse
directly instead of reimplementing (devlog's "reuse instead of
reimplementing" options, items 14-18). Kept separate from the devlog so
each entry can carry enough command-level detail to actually evaluate
reuse, without bloating the chronological log.

Numbering here is durable, same rule as the devlog: entries keep their
number even if others are added, removed, or reordered.

## Status

Just started (T5 in progress, informed by T2's community-docs read).
Nothing below is a decision yet, just gathered facts to decide from.

## Confirmed facts

- **1.** `VDU 23, 0, &A0, bufferId; 32/33, operation, ...` (commands 32/33)
  create or manipulate a 2D (3x3) or 3D (4x4) affine transform matrix
  stored as row-major 32-bit IEEE-754 floats in a buffer. Supports
  identity/invert/rotate/scale/translate/shear/skew/combine, with
  flexible fixed-point/float/16-or-32-bit argument encoding. **Explicitly
  experimental** — requires enabling a test flag
  (`VDU 23, 0, &F8, 1; 1;`) and "may change in the future." Added VDP
  2.9.0 (2D), 2.10.0 (3D combine op).
- **2.** `VDU 23, 0, &A0, bufferId; 34, operation, rows, columns, ...`
  (command 34) generalizes 1 to arbitrary-dimension matrices: set,
  copy+edit, fill, identity/diagonal fill, add, subtract, multiply,
  scalar-multiply, sub-matrix extraction, row/column insert/remove. Also
  experimental, same feature flag as item 1.
- **3.** `VDU 23, 0, &A0, bufferId; 40, options, transformBufferId;
  sourceBitmapId; [width; height;]` (command 40, macro
  `BUFFERED_TRANSFORM_BITMAP`, `0x28`) creates a new bitmap from an
  existing one by applying a 2D transform — directly relevant to
  perspective-scaled wall textures (devlog item 14).
- **4.** `VDU 23, 0, &A0, bufferId; 41, options, format,
  transformBufferId; sourceBufferId; ...` (command 41, macro
  `BUFFERED_TRANSFORM_DATA`, `0x29`) applies a transform matrix to
  arbitrary buffer data, not just bitmaps — could plausibly transform
  raw vertex/vector data for a raycaster/renderer without writing new
  matrix-math code on the eZ80 or in the VDP.
- **5.** The bitmap/sprite API (`VDU 23, 27, ...`) has no scale/stretch
  blit primitive of its own — sprites are frame-based (add/select/show/
  hide/move), with no per-draw scaling command found. Any perspective
  scaling of wall-column textures would have to go through the transform-
  bitmap command (item 3) or a bespoke Wolf3D-specific command, not an
  existing sprite feature (devlog item 16, now answered: no reuse
  available there). Confirmed by the Author: stock VDP sprite bitmaps
  cannot be scaled in place by the matrix-transform commands (items 1-2)
  either — and moot anyway, since this project will not be using VDP
  sprites at all. Also worth noting: Pingo doesn't use those matrix-
  transform commands either, since they post-date Pingo's original
  development in this codebase — it has its own independent transform
  math, not built on items 1-2.
- **6.** The general callback mechanism (`VDU 23, 0, &A0, bufferId;
  80/81, eventType;`, macros `BUFFERED_ADD_CALLBACK`/
  `BUFFERED_REMOVE_CALLBACK`, `0x50`/`0x51`) is real and documented
  (VDP 2.12.0, expanded 2.15.0), but its event types are a closed enum:
  VSYNC, mode change, keyboard, mouse, palette change, read-pixel, and
  VDP-protocol send/receive ranges. There is no generic "an arbitrary
  async VDP operation just finished" event type. This is why Pingo
  invented its own one-off render-complete signal on subcommand 41
  instead of reusing 80/81 — there was nothing to reuse (devlog item 15,
  now answered: not reusable as-is; see the Codex handoff's item 6 for
  the follow-on idea of proposing a new event type upstream).
- **7.** Vendored `vdp-gl` (`AgonPlatform/vdp-gl`, branch `hard-cursors`,
  fetched via PlatformIO rather than committed in-tree) already has a
  real, general-purpose affine bitmap blitter:
  `BitmappedDisplayController::drawBitmapWithTransform()`. It takes a
  bitmap plus a 3x3 float transform matrix and its precomputed inverse,
  works out the transformed bounding box, then rasterizes per-pixel using
  the inverse matrix to sample source pixels (nearest-neighbor, separate
  code paths per pixel format: Mask, RGBA2222, RGBA8888). This is the
  actual engine behind buffered command 40 (item 3) — confirms that
  command isn't just a thin wrapper, it's backed by real reusable
  rasterization code, not something Wolf3D would need to reimplement from
  scratch for simple per-column scaling (devlog item 17, now answered).
  Open question: per-column protocol overhead (a wall renderer might want
  hundreds of scaled column blits per frame) is unmeasured — this is a
  capability finding, not a performance verdict.

## Open questions / still to do

- Whether affine/matrix commands (items 1-2) being gated behind an
  experimental flag is disqualifying for reuse in something meant to be
  upstreamed, or just a caveat to note.
- Whether integer/fixed-point wall-column math is fast enough via
  command 41 (item 4) versus a bespoke ESP32-side routine — needs actual
  measurement, not just protocol-capability review.
- Whether per-column overhead of repeatedly invoking `drawBitmapWithTransform`
  via buffered command 40 (item 7) is fast enough for a full-frame wall
  renderer, or whether a bespoke batched/ESP32-side routine is needed —
  needs actual measurement.
- Existing audio and keyboard/mouse VDU exposure still unreviewed for
  game-loop reuse (devlog item 18).
