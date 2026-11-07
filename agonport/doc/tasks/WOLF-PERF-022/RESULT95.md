# Actual95 — full uncapped comparison completed

All six600-pose canonical-room runs and seven INFO-only resource checks passed.
The combined renderer reduced inclusive draw time by16.24% against the original,
and3.74% against cyan alone. Completed presentation remained about30.06fps.
These draw savings are retained independently of the unchanged presentation rate.

|Arm (run order)|Mean draw, configured240MHz|Pooled nominal presentation|Package|Resident data|
|---|---:|---:|---:|---:|
|Original (1,6)|24.9555ms|30.06238fps|24420B|13348B|
|Cyan016 (2,5)|21.7146ms|30.06313fps|24504B|13348B|
|Combined021 (3,4)|20.9025ms|30.06238fps|22572B|11184B|

Combined includes the qualified cyan fill, exact degree table, narrow division,
equal-full-height setup cache and column chains. It is1848B smaller than the
original package and uses2164B less resident data. Sprite013 is excluded and
remains Smith's requested human revisit. No production default was changed.

The original controls differed by1.6868% in mean draw cost. Individual run means
were24.7468/21.7213/20.7622/21.0428/21.7079/25.1642ms. Both candidate pairs share
the same two bracketing controls; this is one symmetric three-arm cohort, not
separate independent ABBA experiments. The extra3.74% combined-versus-cyan change
does not isolate or establish additive contributions from its other four units.

Each guest completed600 uncapped poses, two full turns, E1L1(34,36), no enemies
and121 statics. The original C3 plus ordered ingress fence remained per pose.
There was no synthetic30fps pacing or static/hidden drawing. Inclusive native
CCOUNT includes preemption/services; milliseconds use configured240MHz. Guest
PRT/MOS rates are nominal, without external oscillator or optical calibration.
The roughly33/34ms presentation cadence does not by itself establish a hidden
cap, fence defect, exclusive CPU cost or human visual confirmation. Other scenes
and an independently matched bespoke arm were not measured here.

Independent replay checked all3600 raw records,600-step/angle/completion ordering,
the actual per-arm eZ80 LOAD/strict-limit/UPLOAD/VDPL LOAD operands in before/after
RAM against their BIN/listings, balanced entry/exit SP, exact selected module
readback and supported repeated-replacement/backup-retirement lifecycle. All822
frozen input paths rejoin472 published distinct byte sets. All seven raw INFO
records passed; the cumulative minimum remaining native task stack was1748B,
above the unchanged512B floor. Combined's selected source path remains1936/4096B
and its module bound1488/2048B, not a universal interrupt/callback peak claim.

Actual95 used the two original foreground jobs throughout: controller1451306
(session14965), observer1451478 (session27507), owned tracer1451480. Positive
same-kit/same-lease attachment preceded all target I/O. Both original handles
returned exit0; native PID/start/boot checks confirmed all three processes
terminal. No SIGTERM was recorded. This does not explain historical84/91 signals
or prove simultaneous cancellation safe. All arms used the same observer, whose
host tracing can perturb setup/collection; no observer-based speedup is claimed.

Exact incoming1105920B native application/tail85f9cf31 was restored and independently
read back. Fresh rootCLI, raw mode0/callback0/route0, whole startup/listener files,
neutral input, offline listener, idle worker and free USB checks passed. Actual95
released normally at2026-11-07T17:28:46.321142UTC; all Wolf target access stopped.
Mech request2d99072a33d5 and Extender received immediate release notifications
before offline analysis. SD remains mounted. No HOLD or further target action.

Raw evidence and independently joined result: [actual95](results/actual95/RESULT.json),
[release](results/actual95/released.json),
[1542-file manifest](results/actual95/SHA256.json),
[822-input published-byte join](results/actual95/PREPARATION-JOIN.json).
Preserve the separate interrupted actual91 result; this completed new cohort
does not retrospectively turn that failure into a comparison.

Next isolated arm is [PERF023](../WOLF-PERF-023/PLAN.md): supported constant-colour
byte-span address work. Its source census covers98.918% of current constant-fill
bytes; that is an opportunity count, not a measured speedup. It requires its own
correctness, target, producer, resource and fresh physical qualification.
