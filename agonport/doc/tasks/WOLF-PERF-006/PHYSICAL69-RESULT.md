# O2 cuts VDP draw time by11.84%

Compiling the same span-optimized module with -O2 instead of -Os reduced mean
VDP pose draw time from36.7942ms to32.4392ms, saving4.3550ms. Completed unpaced
fixture throughput increased from24.8329 to27.8390frames/s (+12.11%). Both
forward and reverse-order pairs show a gain. This completes selected P01;
later priorities and production/default adoption remain unselected.

| Frozen module | Draw ms | Module scope ms | Complete-command ms | Completed fixture frames/s |
| --- | ---: | ---: | ---: | ---: |
| bf7f, Os |36.7942|37.2633|37.3769|24.8329|
| cd429, O2 |32.4392|32.9059|33.0201|27.8390|

Draw is the established VDP bracket around drawing the pose, after command
arrival and through draw completion; it includes preemption/service waits.
Completed throughput counts every finished pose over the guest's whole timed
sequence. Asset loading, module selection, probes and SD collection occur
outside that sequence. Native milliseconds use configured240MHz; throughput
uses nominal1kHz PRT. Independent nominal120Hz MOS gives24.7934/27.7992frames/s.
No optical scanout, external clock calibration or ordinary gameplay trial.

O2's mean draw fits within33.333ms, but its draw p95 is33.4160ms and its slowest
sample33.8259ms. The complete fixture averages about35.92ms per finished pose.
This establishes an improvement, not sustained30Hz. Historical bespoke draw
30.7010ms is a separate older cohort, not a freshly matched parity result.

## Matched physical evidence

Actual generation69 hardware02 ran freeze349e669,328pins, kit a6472082,
fresh SD namespace /test/wolf/perf006/r02. Two controls then four600-pose runs
provide1200records per arm/2400total, with no skipped/coalesced poses.

| Case | Arm | Draw ms | Completed fixture frames/s |
| --- | --- | ---: | ---: |
|03|Os|36.8048|24.8355|
|04|O2|32.6012|27.7123|
|05|O2|32.2772|27.9668|
|06|Os|36.7836|24.8303|

Paired Os-minus-O2 mean draw savings are4.2036ms and4.5064ms; the second pair
reverses execution order. Samples/headings/revolutions are deterministic and
correlated, not statistically independent. Same E1L1 tile34,36 center34.5,36.5,
720degrees/600poses/300distinct headings, no enemies, fixed HUD/weapon and two
warmups. These are unpaced capacity runs, not the20-second paced visual fixture.
RawPRID0xCDCD throughout is interpreted under the pinned SDK as PRO/core0.
Entry/post-production core checks precede logging; the header retains latest
c0 only, not per-sample history or continuous migration proof.

All six guests pass470asset loads/952fences/zero loading errors/timeouts,
normal return and mode0/callback0. Actual installed-module/guest producer joins,
full raw indices/headings/interval bounds and unpaced eZ80 stack restoration
pass. Seven probes show zero live slots/leases and minimum whole-command task
stack1976B (refusal512B). Stack watermark is cumulative; split memory halves
are non-atomic. Neither is a per-function/per-arm peak attribution. Six module
replacements verify previous/selected/backup bytes, supported RECOVER3 and
final target-only state1. No journal, guard or runtime workaround.

The same original native7593 runtime, current UART carrier/observer/clock,
fixtures and actual per-arm producers were retained. Package lengths19896/20928
are joined to real source/listing/binary read/upload/LOAD operands. This
separately checks the composition boundary missed by stopped PERF005/65.

## What changed and what did not get established

Only the candidate private SDK's optimization argument changes -Os to -O2.
Production sources/local helper algorithms and required PSRAM-safety flags,
PIC, ABI, resident limits, SDK and runtime match. Actual code/provider/section/
relocation inspection, sanitizer/output/span/math checks and producer/control
qualification are retained in BUILD-RESULT and HARDWARE-READINESS-02.

O2 package grows19896→20928bytes, executable text14344→15516bytes, resident data
9732→9748bytes; maximum individual static stack report736→768bytes. Relocations
fall51→38. These are compiled-artifact differences, not whole-call stack proof.
The optimizer also changes inlining/layout/generated barriers; required cache
workaround flags remain enabled and actual byte-loop MEMW code was inspected.
No manual safety barrier removal, math-library/provider substitution, wider
store source change or owner SDK/default edit occurred. Measured gain is the
aggregate same-source optimization result, not an isolated dispatch/division/
fill share. Private native positive-count and host-oracle/provider limits stay.
Host output equality does not claim a new physical framebuffer comparison.

## Stopped first attempt and retained custody

Hardware01's unknown boot-admission failure happened before any resource probe,
guest LOAD/RUN, module INIT or timing. All314 first-cohort input bytes and failure
receipts remain preserved; exact restoration and cleanup passed. That attempt
does not contribute timing data or establish a failure of O2. AMENDMENT-02 was
published before changes and selected ONE fresh same-comparison cohort under
the retained actual69 lease. No release/regrant/registry mutation, uncertain
guest replay, altered reset procedure or unbounded setup attempts occurred.

After349e669 publication, a new own-entry CLI/read/EXIT/SAVE-only observation at
1794021281.1931343 and immutable continuation context joined original grant,
new kit and fresh entry bytes. The original grant observation stayed unchanged.
No extra hardware operator or device contact occurred.

After the completed suite, exact incoming1105920B profile8 native app/touched
tail85f9 was restored and independently read back. Unchanged P4d9bcb/EMOSa25f/
startuped403/listener0566 and rawmode0/callback0/route0/files/rootCLI/cursor/
inputneutral/offlineidle/worker0/freebothUSB checks passed. All controller,
compiler, flash and reader children exited. Final held-idle epoch1794022834.0448785
is2026-11-07T03:40:34UTC. Actual69 remains HELD for Smith, even if queued;
there has been no central release, successor grant or further probing. SD stays
mounted. No production/default adoption was performed.

PHYSICAL69-RESULT.json retains the aggregate, all six case/actual producer/
lifecycle receipts, seven probes,160binary hashes, new entry/context, exact
restoration and final held-idle observation. All328 frozen input files were
rehashed at analysis. Full raw bytes and original transfer journals remain in
ignored build/hardware02/evidence. The inherited per-case analyzer's generic
clock text still says emulator; actual physical operation is established by the
hardware/controller/restoration evidence, and all clocks remain nominal.

Continuation subtask dispositions: WOLF-PERF-006-A02-01 through -05 are complete
for this cohort. The pinned amendment retains its predispatch checkbox state;
its immutable contents remain part of the328-input evidence. This result is
the completion record, not a rewrite of the frozen entry conditions.
