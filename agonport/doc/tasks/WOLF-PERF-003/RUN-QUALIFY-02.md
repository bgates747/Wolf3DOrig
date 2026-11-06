# Fresh qualification q02: r05, unchanged native02 firmware

q01 stops at case6's300-second timeout before its first render. Native UART
contains only378of4096zero bytes in the first dedicated diagnostic-log upload;
no warm-up/timed rotation completion follows. This identifies the stalled setup
boundary, not the underlying transport/emulator cause. Five preceding cases pass;
cleanup controls7/8 were not run. Oryx302 was released at17:22:33UTC after joined
children,465retrieved output hashes and fresh whole-host idle. Exact q01 harness
is preserved with verified freeze hashes under build/r04/harness.

r05 uses stock CLEAR/CREATE for this task's12056-byte log, followed by the same
mode-info fence already used by A. This changes setup only. All eight guests and
host integrity/decoder checks pass; the safe-SDK module and both native firmware
images remain byte-identical to r04. Canonical AGNB-derived room parity also
passes at0/45/90/135/180/225/270/315degrees: all76800pixels and1792geometry bytes
per heading match the standalone oracle and copied/direct production paths,
with independent-row guard/sync and lease checks. Pi145/146 released cleanly.

Prepare a new stopped q02 profile set with --failure-first. Exact order:

|Order|Backend|Arm|
|---|---|---|
|1|vdplet|paced with diagnostic captures|
|2|bespoke|cpu|
|3|vdplet|cpu|
|4|bespoke|unpaced|
|5|vdplet|unpaced|
|6|bespoke|paced with diagnostic captures|
|7|bespoke|intentional restored-timer abort|
|8|vdplet|intentional restored-timer abort|

At most eight sequential headless processes, each300seconds, actual fresh
Oryx FIFO checkout/assert, frozen private inputs, no GUI/hardware. Stop on first
unexpected failure, retain results and ordinary/owned cleanup, retrieve/hash,
fresh whole-host idle and release/notify before extended analysis. Capture-free
A/B/B/A performance comparison remains later after qualification. No physical
or ordinary-game speed result follows from this schedule.
