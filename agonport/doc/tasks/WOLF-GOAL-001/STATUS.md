# Overnight optimization status

Current reference is the a926 original-ray renderer,24420B. All listed physical
comparisons use the canonical room, maximum uncapped presentation, configured
240MHz inclusive draw timing and nominal guest clocks. Draw cost and completed
presentation rate are separate measurements. No production default is silently
changed; exact source/target/producer evidence remains with each task.

|Item|What the evidence currently establishes|Disposition|
|---|---|---|
|Cyan fill016|Actual81 draw25.137→21.691ms, pooled reduction13.707%; presented rate about30.06fps unchanged; image+84B|Best individually measured draw arm; preserved as the second reference in021|
|Local narrow division017|Actual85 draw25.136→24.602ms, pooled2.125% reduction versus3.111% control spread; rate unchanged; image+4B|Qualified useful work saving; exact isolated timing effect unresolved|
|Equal-full-height setup018|Actual87 draw25.137→25.247ms, difference0.438% versus3.134% control spread; rate unchanged; image+60B|No established gain or precise regression; retain qualified arm and resource costs|
|Column chains019|Scalar ordering preserved; host room census avoids1045504/1199104 membership checks (87.19%); image+172B, selected native path1936B versus1344B|Individual timing unavailable: actual89 failed before any guest, then exact restoration/release|
|Exact degree table015|Exact angle/output parity; image−2240B and resident data−2164B|Individual timing unavailable after pre-guest interruptions; included in021|
|Combined021|Five supported units above compose correctly; exact source/target/real producers and supplemental ordered row-alias checks pass; image22572B (−1848B), data11184B, selected native path1936/4096B|Actual95 full matched comparison completed: draw24.956→20.903ms (−16.241%); another3.740% below cyan; presentation30.062fps unchanged. Package−1848B/data−2164B. Retain measured combined reference; no automatic default adoption|
|Sprite hoisting013|Room pooled+2.05% draw cost, actor-rich−0.8%; no rate change established|Smith explicitly requested review after sleep; no FPS-only rejection or automatic adoption|
|Identical-post grouping020|Canonical room opportunity191864/4368126 texture reads (4.392%); all pixel stores remain, groups mostly width1|Source gate completed; defer harder implementation here, preserve near-wall/larger-view future opportunity|
|Generic libgcc admission|Allocated44B metadata still violates existing package admission|No strip/guard workaround; supported local017 candidate is separate|
|Presentation/fence|Actual81/85 steady pre-presentation work23–30ms, none within one nominal60Hz refresh; draw savings trade against fence wait|No attributed hidden cap, second-VBlank defect or exclusive CPU claim; future pipeline changes require their own owner/component qualification|

Actual89 failed input admission after exact timed-native installation, before
any room/INFO query. Cause remains unknown; restoration85f9/readback/current
bootstrap/full handback/release passed. Its zero-sample failure is preserved and
never relabelled as a performance result. Actual91 was a distinct combined
comparison, not an individual019 retry. Its first control SD validates24.750ms
draw and30.0616fps; no combined speedup/regression can be inferred. The host
signal sender/cause remains unknown, and no blind replay is selected. It keeps the maintained one-shot boot
route, all guards, exact incoming restoration and MechAgon-first scheduling.

Useful entry points: [PERF021 readiness](../WOLF-PERF-021/HARDWARE-READINESS.md),
[actual89 failed-cohort report](../WOLF-PERF-019/RESULT89.md),
[actual87 scaling result](../WOLF-PERF-018/RESULT87.md),
[sprite human revisit](../WOLF-PERF-013/REVISIT.md),
[post census](../WOLF-PERF-020/CENSUS-RESULT.md),
[presentation source](PRESENTATION-SOURCE.md),
[same-guest-clock budget](PREPRESENT-BUDGET.json).

Host-signal dependency: [WOLF-HOST-001](../WOLF-HOST-001/RESULT03.md) qualifies
controlled separate foreground attach. [PERF022 actual foreground checks](../WOLF-PERF-022/HOST-RESULT01.md)
also qualify app-server-parented controller/observer pairs, the unchanged real
interruption handler, known-sender capture, observer cancellation/refusal and15
negative handshakes. Historical sender/cause remains unknown; simultaneous loss
of both jobs and host tracing perturbation remain limits.

[PERF022 actual95](../WOLF-PERF-022/RESULT95.md) completed the full six uncapped
original/cyan/combined/combined/cyan/original rooms and seven INFO queries. All3600
records/822 frozen inputs/real producers/module lifecycle/stack/resource/observer
and full restoration joins passed. Both original foreground handles and tracer
joined; no SIGTERM observed. Normal release17:28:46UTC and immediate Mech-next/
Extender notices completed before analysis. Minimum native INFO remaining1748B.
Control spread1.687%; other scenes, optical calibration, unit attribution and
historical host-signal cause remain unestablished. No hardware lease is retained.

[PERF023](../WOLF-PERF-023/PLAN.md) separately freezes one supported complete-quad
constant-span byte-address specialization against exact combined8d3d. Source
census covers98.918% of current constant-fill bytes; no speed claim. Isolated
host/target qualification is selected under ordinary serial Pi compilation;
new producer bindings and a separate finite physical freeze/fresh admission
remain required. No Oryx work, wider stores, helper/provider or default change.
