# Corrected dispatch reserve — hardware readiness02

This supersedes unexecuted f7e01ef hardware01 readiness. VDPlet identified a
real counterexample: inherited case admission at300seconds remaining could
start inside the stated360second cleanup reserve, and module selection lacked
an admission check. The original source/kit/plan histories remain retained;
no target operation or lease occurred under them.

HARDWARE-RUN-02 explicitly calls this a60minute scheduling horizon/admission
reserve, not a guaranteed wall-time completion or restoration deadline.
Already-submitted transfers can overrun. No replay, resubmission, relaxed job
bound or forced mid-write interruption is introduced. Six guests/seven probes,
all guest/module/native/assets and exact incoming restoration stay unchanged.

Thirteen new-adapter device-free checks pass, including330/360/600/660second
counterexamples, a fresh RUN recheck after setup, no collection or metadata
submission at cutoff, safe in-flight completion followed by successor refusal,
and cleanup exemption. The six retained controller checks remain applicable
with unchanged inherited source. No new compiler or target test was run.

For all Olimex bench procedures, use the sole authoritative [bench guide](/Agon/mystuff/agon-extender/docs/operations/olimex-bench/README.md).
