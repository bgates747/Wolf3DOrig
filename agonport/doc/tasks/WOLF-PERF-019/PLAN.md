# WOLF-PERF-019 — Visit only the columns in each wall texture group

## Pre-code unit compatibility

Current draw_walls discovers needed IDs, acquires them ascending, then scans all
256 columns for each needed ID. PERF014 caches ID resolution but deliberately
leaves those repeated membership scans. This candidate removes that work.

Existing ordinary integer arrays and the current finite per-texture asset lease
support this method as-is. No firmware/SDK/provider/service, allocation, format,
borrowed pointer, wider store or compiler/PSRAM policy change is needed. The
current frame's world/height/tile/U metadata remain stable inputs throughout
rendering, as required by the existing grouped renderer and ID-cache candidate.

Use a128-entry uint16 head array with sentinel256 and a256-entry uint8 next
array, all initialized. Visit columns255 down to0. For a positive height and
valid resolved ID1..127, prepend its index to that ID's chain. The previous head
fits a byte when present; otherwise point the last node to itself. This permits
column255 as a real node without an ambiguous byte sentinel. Every link either
advances to a strictly larger column or terminates at that same final column.

Visit texture IDs ascending exactly as before. Skip sentinel heads; acquire,
bounds-check, count and release exactly once per nonempty group. Traverse its
chain ascending and retain the existing per-column geometry setup, sampler,
U read and pixel stores unchanged. A self link ends the group. Empty and invalid
columns never enter a chain; no unchecked narrowed sentinel or uninitialized
link can be consumed. Acquire/bounds/release failures retain original precedence.

Head256B plus next256B replace needed128B: nominal local storage increases384B.
The compiler may inline/split differently; actual emitted frames and nested
module/native path must pass before dispatch. Runtime cumulative watermark
and the512B floor remain. Source memory counts are not a target peak claim.

This removes repeated membership scans and ID resolution, while retaining
grouped texture acquisition and exact column-major read/write order, including
aliased row/source cases. Pixel writes, texture samples, ray geometry and painter
order are unchanged. Construction/link traversal adds work and local storage;
source counts alone cannot establish a performance win.

This is a local optimization of the already documented grouped consumer method.
It is neither literal Carmack post widening/generated scaling nor a workaround
for their incompatible units/x86/VGA implementation. Those original-method
boundaries remain explicit in WOLF-GOAL-001/WALL-POST-DESIGN.md.

Qualified source/target/host/producer result: [BUILD-RESULT.md](BUILD-RESULT.md).
Separate physical01 selection and qualified freeze: [HARDWARE-READINESS.md](HARDWARE-READINESS.md).
Actual89 stopped before any room/probe at startup admission. Exact restoration,
full handback/release and the failed-cohort disposition are complete:
[RESULT89.md](RESULT89.md). Independent chain/trig timing remains unmeasured;
no automatic replay or performance/default claim. Actual018 is unchanged.

For all Olimex bench procedures, use the sole authoritative [bench guide](/Agon/mystuff/agon-extender/docs/operations/olimex-bench/README.md).
