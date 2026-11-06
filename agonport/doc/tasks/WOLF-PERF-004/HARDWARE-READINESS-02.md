# Corrected dispatch reserve — hardware readiness02

This supersedes unexecuted f7e01ef hardware01 readiness. VDPlet identified a
real counterexample: inherited case admission at300seconds remaining could
start inside the stated360second cleanup reserve, and module selection lacked
an admission check. The original source/kit/plan histories remain retained;
no target operation or lease occurred under them.

The new adapter checks module/case/probe admission and rechecks immediately
before the actual RUN keyboard submission, requiring more than660seconds
remaining. New transfer/collection jobs, metadata sessions, staged files and
ordinary CLI commands are refused before the360second window. No new write or
collector is submitted after refusal. Existing jobs retain same-job resume
and their original finite bounds; they are not interrupted at the cutoff.
Normal restoration and known-return RAM preservation are exempt from dispatch
cutoff. A refusal stops successors and retains custody for actual restoration.

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

File-only preparation creates a new ignored build/hardware02 kit with155pins;
HARDWARE-INPUTS-02 identifies its exact digest. The original hardware01 packet
is preserved separately. The normal helper cancelled unstarted a280de32ebe5
and reserved b29f7df54343 against the new plan while MechAgon60 remained active.
No active custody was modified. Actual60 clean handback and fresh Extender
admission/current-tuple comparison are still required before physical work.
