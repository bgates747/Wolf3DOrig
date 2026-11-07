# Equal-height scaling setup cache: actual87

The uncapped A/B/B/A comparison passed **2400 poses and five INFO queries**.
This cohort shows **no established timing improvement**: pooled inclusive draw
was25.137ms for the controls and25.247ms for the candidate, a0.438% increase.
The two controls differed3.134%, larger than that pooled difference. Presented
rate remained about **30.06fps**; the negligible pooled difference is timestamp
quantization, not a demonstrated cadence gain.

|Run|Arm|Mean draw ms at configured240MHz|Completed-frame fps|
|---|---|---:|---:|
|1|Original a926|24.749|30.06163|
|2|Setup-cache2a249f|25.277|30.06313|
|3|Setup-cache2a249f|25.218|30.06163|
|4|Original a926|25.525|30.06163|

Both candidate means lie between the two control means. Preserve the exact
qualified work-saving arm and its costs for later evaluation; this result
neither demonstrates a speedup nor establishes a precise regression. No default
or combined adoption is made. Source census113434 eligible reuses out of153600
columns (73.85%) remains an independently qualified host count, not a sampled
native branch count or performance share.

The change caches clipping/step/initial-fraction setup when the next column of
an acquired texture has identical FULL height. Texture sampling and scalar
column/read/write/acquisition/error order, ray geometry and metadata remain
unchanged, including qualified aliases. Package24420B becomes24480B (**+60B**),
resident data stays13348B. Candidate SHA256:
`2a249f85e6e88559e1e32d7c9af6906a4f543a693f97f07aa5b0799a53505ed8`.
Selected nested wall/acquire path1344/4096B does not claim a universal peak.

All four actual guests completed600 consecutive poses/two turns in the same
canonical E1L1(34,36) room, zero enemies and121 statics, with no pacing cap.
Actual selected module/header and six per-arm linked size/strict-limit operands,
balanced SP and both per-frame presentation/fence calls join resident before/
after RAM. Whole module replacement, exact previous target/owned backup and
supported retirement join through the four arms. All five raw INFO records pass;
lowest cumulative stack watermark is2020B above the unchanged512B floor. This
is a cumulative observation, not an individual candidate or ISR peak.

Fresh actual87 sole custody used the mandatory Extender interpreter/launcher.
Original PID1378273/session30885 completed exit0 with all owned children joined.
Exact incoming1105920B native app/tail was restored and independently read back
as85f9. One matched bootstrap and fresh rawmode0/callback0/route0, whole startup/
listener, rootCLI, neutral input, offline listener, idle worker and free USB
checks passed. Normal release completed **2026-11-07T14:05:05.729274UTC**; actual
next MechAgon43d and Extender received the handoff before offline reporting.
Wolf019 voluntarily moved behind that first-priority case, now1fec8fdf3f1b.
All Wolf target access stopped; SD remains mounted. No P4/EMOS/startup/listener/
carrier/provider change occurred.

[Verified result](results/actual87/RESULT87.json),
[818 retained evidence pins](results/actual87/SHA256.json) and the original
415-input snapshot index preserve the cohort/restoration/release.
[report87.py](report87.py) performs independent offline producer/RAM/lifecycle/
resource/clock/restoration joins using the previously replay-qualified reporter.
Current measurements are inclusive CCOUNT at configured240MHz and nominal
PRT/MOS intervals. No exclusive CPU, external oscillator calibration, optical
scanout, native reuse counter or human visual confirmation is claimed.
Actual84's host SIGTERM cause remains unknown; this run does not repair it.
