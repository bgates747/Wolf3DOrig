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
|Combined021|Five supported units above compose correctly; exact source/target/real producers and supplemental ordered row-alias checks pass; image22572B (−1848B), data11184B, selected native path1936/4096B|Frozen six-run comparison versus original and cyan; actual91 started, result pending|
|Sprite hoisting013|Room pooled+2.05% draw cost, actor-rich−0.8%; no rate change established|Smith explicitly requested review after sleep; no FPS-only rejection or automatic adoption|
|Identical-post grouping020|Canonical room opportunity191864/4368126 texture reads (4.392%); all pixel stores remain, groups mostly width1|Source gate completed; defer harder implementation here, preserve near-wall/larger-view future opportunity|
|Generic libgcc admission|Allocated44B metadata still violates existing package admission|No strip/guard workaround; supported local017 candidate is separate|
|Presentation/fence|Actual81/85 steady pre-presentation work23–30ms, none within one nominal60Hz refresh; draw savings trade against fence wait|No attributed hidden cap, second-VBlank defect or exclusive CPU claim; future pipeline changes require their own owner/component qualification|

Actual89 failed input admission after exact timed-native installation, before
any room/INFO query. Cause remains unknown; restoration85f9/readback/current
bootstrap/full handback/release passed. Its zero-sample failure is preserved and
never relabelled as a performance result. Actual91 is a distinct combined
comparison, not an individual019 retry. It keeps the maintained one-shot boot
route, all guards, exact incoming restoration and MechAgon-first scheduling.

Useful entry points: [PERF021 readiness](../WOLF-PERF-021/HARDWARE-READINESS.md),
[actual89 failed-cohort report](../WOLF-PERF-019/RESULT89.md),
[actual87 scaling result](../WOLF-PERF-018/RESULT87.md),
[sprite human revisit](../WOLF-PERF-013/REVISIT.md),
[post census](../WOLF-PERF-020/CENSUS-RESULT.md),
[presentation source](PRESENTATION-SOURCE.md),
[same-guest-clock budget](PREPRESENT-BUDGET.json).
