# Guarded local divider: actual85

The uncapped A/B/B/A comparison completed **2400 poses and five INFO queries**.
Mean inclusive draw time was25.136ms for the controls and24.602ms for the
guarded32-bit candidate: **2.125% lower in this cohort**. Presented rate remained
about **30.06fps**. Control draw time drifted3.111%, so the pooled2.125% is not
a precise isolated estimate of the optimization's effect.

| Run | Arm | Mean draw ms at configured240MHz | Completed-frame fps |
|---|---|---:|---:|
|1|Original a926|24.751|30.06163|
|2|Candidate12857|24.629|30.06313|
|3|Candidate12857|24.575|30.06163|
|4|Original a926|25.521|30.06163|

Both candidate means were below both control means, but the difference against
the first control is much smaller than against the last. The negligible pooled
FPS difference corresponds to timestamp quantization and is not a demonstrated
presentation improvement. Keep the exact qualified candidate and its arithmetic
work reduction for later combined evaluation; unchanged FPS alone does not
dispose it. No default or combined source adoption is made here.

The candidate changes only the existing local unsigned-magnitude helper: after
the zero guard, zero high words use32-bit QUOU; all other inputs retain the exact
wide fallback and signed wrapper. Original package24420B becomes24424B (**+4B**),
resident data stays13348B. Candidate SHA256:
`12857ecfa682d3f149c0d9688e7654f7692f6bde985b0cad2b35d33cf35ebf64`.
The generic libgcc44B allocated-metadata admission problem remains unresolved;
this result neither bypasses that guard nor claims a newly admitted library.

Every run has600 consecutive scripted poses, two turns, no synthetic pacing,
the current original raycast and the canonical room(34,36), zero enemies and121
statics. Actual selected module/header and six linked package-size/strict-limit
operands, balanced SP and both per-frame presentation/fence calls join resident
RAM. Whole module replacement, prior target/owned backup identity and supported
retirement join across all four arms. Five raw INFO results pass; the lowest
cumulative watermark is1896B, above the unchanged512B requirement. These are
cumulative observations, not individual arm stack peaks or native branch counts.

All actual85 work used the required Extender interpreter/launcher and exclusive
fresh grant. The original driver1363229/session69056 completed with exit0.
The exact incoming1105920B native application/tail was restored and independently
read back as85f9. One current matched bootstrap and fresh rawmode0/callback0/
route0, whole startup/listener, rootCLI, neutral input, offline listener, idle
worker and free USB checks passed. All owned children joined; normal release85
completed **2026-11-07T13:11:08.266053UTC**, with immediate Extender/MechAgon notice.
SD remains mounted. No P4/EMOS/startup/listener/carrier change occurred.

[Verified result](results/actual85/RESULT85.json),
[818 retained evidence pins](results/actual85/SHA256.json) and the original
514-input snapshot index preserve the complete cohort, restoration and release.
[report85.py](report85.py) performs the independent offline joins using the
previously actual81-replayed reporter. Current means use inclusive CCOUNT at
configured240MHz and nominal PRT/MOS clocks. No exclusive CPU, external
oscillator calibration, optical scanout or human visual confirmation is claimed.
Actual84's unrelated SIGTERM sender remains unknown; this successful cohort
does not establish its cause or a host repair.
