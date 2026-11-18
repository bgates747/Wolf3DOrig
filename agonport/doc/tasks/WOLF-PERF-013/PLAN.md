# WOLF-PERF-013 — Sprite-column decision hoisting

Baseline is PERF009/build/r01/candidate, module SHA256
`a926b48ab3207b59773cc8283d59cc687f274ef2af00017451567449a4c69656`,24420B.
Candidate changes only sprite-column invariant calculations. Drawing remains
row-major with the same texture acquisition/release, painter ordering, strict
wall-height comparison, alpha, texture stepping/rounding and output mapping.
Original control must reproduce byte-for-byte before the candidate is admitted.
Hardware timing remains unqualified until the exact matched physical run.

Each build has a new output directory, finite900s total/240s per-step bound,
80C/512MiB guards and serial owned children. No retry of failed build or target
case without preserving its receipt and a separate corrected selection.

For all Olimex bench procedures, use the sole authoritative [bench guide](/Agon/mystuff/agon-extender/docs/operations/olimex-bench/README.md).
