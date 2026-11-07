# WOLF-PERF-006 — Performance-gap priorities and the O2 comparison

Smith directly selected the first item on2026-11-06: document the prioritized
list, commit/push all dirt in logical groups, implement the first improvement,
reserve bench time now and test as soon as qualification and admission allow.
He explicitly requires retaining the bench after testing even with a queued
successor. This supersedes previous task plans requiring immediate release.
Only priorityP01 is selected for implementation/testing; later priorities are
recorded for discussion, not automatically executable follow-ups.

## Prioritized work

- [x] WOLF-PERF-006-P01 — Compare exact current module under -O2 versus -Os.
  Low implementation effort, uncertain potentially useful payoff. Same source,
  helpers, safety flags/runtime/scene. Close package/sections/stack/actual guest
  producer bindings before matched physical timing. Selected now.
- [ ] WOLF-PERF-006-P02 — Qualify optimized division provider instead of fixed
  64-iteration helper. Moderate effort/potentially substantial gain; exact
  supported libraries, signed domains, final closure/relocations/stack first.
- [ ] WOLF-PERF-006-P03 — Hoist remaining textured-pixel invariants where safe.
  Moderate effort/potentially substantial payoff. Extrapolates measured span
  improvement, not another measured result. Preserve masks/permutation/alpha/
  bytes/row lifetimes and inspect actual generated loops.
- [ ] WOLF-PERF-006-P04 — Factor sprite-column occlusion decisions once per
  column. Low/moderate effort, scene-dependent payoff. Preserve row locality,
  clipping/wall-wins-equality/transparency and bounded storage.
- [ ] WOLF-PERF-006-P05 — Reduce repeated texture-group wall-column scans while
  retaining acquisition savings. Moderate effort/conditional payoff; exact
  borrowed-resource lifetime and output equivalence first.
- [ ] WOLF-PERF-006-P06 — Compare quarter-wave versus full trig tables.
  Moderate effort/likely smaller payoff and resident-data cost. Setup-only
  floating-point trig is not a hot-frame diagnosis.
- [ ] WOLF-PERF-006-P07 — Study original wall-post/scaling/visibility techniques.
  High effort/uncertain payoff; these already differed in bespoke, and literal
  x86 methods do not automatically suit Xtensa. Projection and sprite ties are
  behavior decisions, not covert performance edits.

Priorities use VDPlet VDPL031/NEXT-MEASUREMENTS, VDPL033 original-unit ledger,
verified physical63/67 and VDPL034 lineage discussion/report. The latter report
is reviewer evidence pending owner verification, not an established defect list.
Both original draw entry points are synchronous; finite RUN alone is not a
measured cause. Independent physics/latest-pose rendering is a separate possible
responsiveness task; this comparison does not select it.

## Immutable implementation subtasks

- [x] WOLF-PERF-006-01 — Freeze this plan, PRE-CODE and finite hardware plan,
  reserve normal Olimex FIFO immediately, notify scheduler of explicit hold.
- [x] WOLF-PERF-006-02 — Prepare isolated exact bf7f physical67 control and same
  source candidate. Only candidate SDK copy's optimization flag -Os→-O2 changes;
  no owner SDK/default change. Reproduce exact control binary or stop.
- [x] WOLF-PERF-006-03 — Serial Pi build/check: source/math/lifecycle/host output,
  actual compiler flags/helpers/sections/relocations/PSRAM-safe code and whole
  resources; qualify package-dependent real eZ80 producers per arm. Preserve
  failed attempts and stop on mismatch; no relaxed guards or uncertain replay.
- [x] WOLF-PERF-006-04 — Qualify derived actual controller/listener lifecycle,
  current ROM/map/API/bootstrap/fullspan rollback and fresh input kit. Commit/
  push concrete freeze before final scheduler preflight; actual grant required.
  Original hardware01 admitted actual69; it stopped before guest entry and was
  restored. AMENDMENT-02 separately freezes one same-task retained69 cohort.
- [x] WOLF-PERF-006-05 — Run matched control/control then four600-pose unpaced
  original/candidate/candidate/original cases, entry/after-case7INFO probes;
  unchanged E1L1(34,36)/720degrees/noenemy work and native7593/carrier/observer.
- [x] WOLF-PERF-006-06 — Exact incoming native app/touched-tail restoration and
  independent whole readback, files/mode0/callback0/route0/rootCLI/input/idle/
  freeUSB/joined actors. Retain actual lease after tests per Smith; announce
  restored-idle held custody to scheduler and user, never grant next yourself.
- [ ] WOLF-PERF-006-07 — Decode/report/share raw matched results and limits,
  positive/negative outcome and source/provider/code/stack. No production
  adoption or second priority unless subsequently selected. Bench release
  remains held pending Smith's instruction.

## Build and execution boundaries

Pi compiler FIFO, assert-before-child, serial children,15min horizon/180s
compiler/240s check bounds,80C/512MiB available RAM floor, stop/join only owned
process groups and normal compiler release. No emulator/Oryx workload selected.
Physical expected25–40min/60min scheduling horizon. New module/case/probe/RUN
require >660s remaining; ordinary new jobs/collection >360s. Original same-job
finite bounds may overrun; no midwrite interruption/transaction resubmit/query
replay. Cleanup exempt; first unexpected stops successors. Known returned setup
failure saves resident RAM before LOAD, handles absent/corrupt optional outputs,
then exact restoration. Unknown state retains custody for supported recovery.
Only nativeB app/touched-tail install+exactincoming restore/readback; no P4/
EMOS/partition/NVS/startup edits, no private imports or cache-safety relaxation.
Fresh namespace/guest+module length joins/current exact tuple required. After
normal clean restoration keep bench ownership idle for Smith instead of release.
Nominal configured clocks/preemption-inclusive/uncalibrated/fixture-specific
limits remain. No physical-pixel/gameplay/30Hz promise or default adoption.
