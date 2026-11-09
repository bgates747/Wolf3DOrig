# WOLF-PROD-001 — Promote the qualified renderer into the normal game

Smith directly selected this work November 9, 2026: update the production game
with the new renderer, fix the signed-shift defect, and verify that the mostly
integer pipeline derives from the original code. Freeze and push this plan
before implementation. The earlier optimization goal remains paused.

## Selected implementation

1. Promote the completed PERF021 combined renderer (source backing measured
   module 8d3d19bb) into the maintained production source. Preserve the ordinary
   module lifecycle, asset refusal/release behavior, API/ABI 1.6, capabilities
   257, bytewise row access, PSRAM policy and production HUD/game behavior.
   Do not promote the unmeasured PERF023 arm or diagnostic RUN100/WPN1 wrapper.
2. Make the resulting qualified production package the routine builder and
   deployment selection. Produce a fresh complete game payload and matching
   receipt; preserve old payloads and historical controls. Retain explicitly
   selected profiling instrumentation separately, with the same renderer source.
3. Eliminate negative signed-left-shift scaling from maintained active code.
   The original-ray promotion removes its fixed_div calls. Keep a corrected,
   test-only older-renderer reference using int64 multiplication by 65536,
   with signed/boundary tests under UBSan. Do not rewrite frozen experiments.
4. Trace original integer/fixed-point position, trig/tangent, traversal,
   projection, sampling and timing sources. Separate inherited methods from
   port-specific representations, new optimizations and host floating-point
   table generation. Report exact source identities and intervals.

## Pre-code compatibility decision

All selected renderer units already use the existing synchronous rows/pixel and
asset APIs: no missing firmware service or workaround is selected. The only
production-wrapper donor change is PERF017's zero-guarded u32 division fast path;
retain its signed wrapper and full-width fallback. The new original tangent ray
method intentionally differs from the older reciprocal DDA, so use the retained
qualified combined output as the exact promotion oracle. Keep corrected older
DDA evidence separately; do not claim old and new geometry are identical.

## Qualification and resource bounds

Use normal Pi build FIFO: one serial compiler, ordinary bounded host checks,
80 C stop, missing thermal sensor stop, 512 MiB RAM floor, 180 s ordinary child
(300 s 600-frame sanitizer leaf), 1800 s total with 60 s cleanup reserve.
Assert actual ownership before each child; join only owned groups and release
with next-owner notification. Retain every failed attempt in a fresh directory.

Check host mirror/renderer/module lifecycle/failure behavior; exact six-scene and
600-frame alternating-row/page, geometry/state/lease parity with combined021;
UBSan signed division boundaries; emitted Xtensa package, integer divide body,
PSRAM/relocations/resource limits and actual nested stack frames. Assemble the
normal full game and native-profile control, verify all embedded package-length
operands and production hash joins, and exercise current preparation tests.

Use verified dc43ecb8 async-r1 release and current MOS defaults from FIRMWARE.md.
Current release compatibility must be distinguished from historical performance.
For a runtime check use a new finite current-firmware preparation through normal
Oryx or Olimex scheduling, with exact payload/input freeze before dispatch. Do
not reuse old private7593 installers/controllers. No firmware exception is
inherently required. Any performance fixture is uncapped. User-visible fixtures
are loaded without agent RUN and announced through the application question UI.
Restore changed components to current standards, stop owned actors, leave SD
mounted, and release normally. Do not resume unrelated optimization axes.

## Completion evidence

Commit/push implementation and report including the new production package and
client identities, selection chain, actual checks, signed-shift disposition,
original-code lineage and any concrete runtime limitation. Do not describe
historical 20.90 ms measurements as a new current-firmware speed result.

## Amendment 01 — host compiler memory, before successor dispatch

Attempt module01 passed mirror, signed-divider and legacy/optimized scene tests
then stopped at516816KiB available memory during host module compilation; no
target was contacted. Preserve that failure. Use reduced host debug information
and more frequent GCC garbage collection (ggc-min-expand10/min-heapsize8192).
Keep O2, ASan/UBSan, exact output checks and the512MiB guard unchanged. This is
compiler-memory control, not a change to target algorithms or native flags.
