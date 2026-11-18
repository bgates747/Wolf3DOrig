# Joint hardware comparison 02: texture cache and exact trig table

This finite cohort closes the physical steps of WOLF-PERF-014 and015 while
sharing the same asset staging, timing application install and restoration.
Both candidates are already independently qualified against exact a926. Keep
PERF016's measured22ef result and017's separate local-divider arm unchanged.
This selects no combination of source changes and no production default.

| Order | Renderer | Scene | Completed poses |
|---|---|---|---:|
|1|A: original a926|E1L1 room(34,36), zero enemies|600|
|2|B: cache8c126c|same|600|
|3|C: trig2844|same|600|
|4|C: trig2844|same|600|
|5|B: cache8c126c|same|600|
|6|A: original a926|same|600|

Each run rotates twice at maximum uncapped presentation speed; per-frame C3
plus ordered-ingress fence remains. No30Hz delay, hidden/static timing arm,
audio change or human-manual-start gate. Entry plus after each run has one
existing INFO-only resource query: seven in total, minimum512B cumulative
watermark. Both candidate comparisons use the same bracketing A runs; state
this shared-control design and drift limits instead of claiming separate ABBA.

Expected25–30minutes; absolute4200s including360s cleanup reserve. Each guest
has300s bound; every new module/guest needs more than660s remaining. Guard new
submissions without interrupting an in-flight transfer. Preserve identity-bound
same-job completion/failed-job retirement rules and exact module-target/backup
verification before supported backup retirement. No retry or extra cohort.

Archive exact selected inputs before post-run checklist changes. Join actual
per-arm module/header/six encoded size/limit operands, SP and presentation
calls to resident RAM;600 consecutive poses/native records/clock bounds and
resource lifecycle to raw output. Report inclusive native draw, per-frame
presented rate and package/stack/data costs separately. No exclusive CPU,
external oscillator or optical scanout claim; no FPS-only rejection criterion.

Actual84 disposition:01/02 qualified and frozen;03 disposed interrupted before
first room LOAD/RUN, not executed matrix;04 cleanup/restore/release complete;
05 stopped evidence published,014/015 physical measurements remain open.
See [RESULT84.md](RESULT84.md). No replay selected.

For all Olimex bench procedures, use the sole authoritative [bench guide](/Agon/mystuff/agon-extender/docs/operations/olimex-bench/README.md).
