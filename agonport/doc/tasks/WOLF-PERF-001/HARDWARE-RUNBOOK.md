# Physical qualification runbook — prepared, not executed

The Author requested Olimex time for this three-arm hardware suite on
2026-11-04, following successful headless qualification. Reserve through
Extender and obtain its actual checkout before any bench operation. Firmware
changes are not selected by this request: reconcile installed compatibility
with Extender first. Use the canonical physical-bench reservation and SD
procedures. Never unmount/eject
the card without Smith's explicit request; sync and verify writes in place.

## Package and runtime

Scheduling allowance: 30 minutes total, comprising up to 10 minutes of component
reconciliation/staged deployment, three bounded runs of at most five minutes
each, and five minutes of retrieval and exact restoration. Stop at the first
unexpected failure. Preserve startup and the installed listener; no autorun.
Use a fresh transaction path, retain installed component identities and return
CLI/input, listener/transfer state and any changed display state to the agreed
handback. Return exact startup/component hashes to Extender before release.

The original `build/hardware-kit.zip` preserves the R06 payloads. The physical
readiness revision is `build/hardware-r07.zip`, with inputs and controller
frozen in `hardware/freeze.json`; its only application change is conditional
native mode acquisition and explicit pre-measurement monitor settling. The
unchanged native module and full measured body retain R06's qualification,
and the setup revision passed its bounded headless CPU smoke. The kit contains
the three benchmark
payloads under `wolfperf/cpu`, `wolfperf/unpaced` and `wolfperf/paced`, plus
the input/hash receipts. The deliberate abort control is excluded. No emulator
firmware is presented as a flashable hardware image. Retain the currently
installed firmware identity and rollback image before any approved change.

Require a verified shared VDPlet runtime with ABI 1.6, runtime identity 0x0100
and capability subset 0x0101 (buffers plus direct colour rows). The native
module is the task diagnostic build 0x20261104. Inspect the actual hardware
runtime and CPU frequency; emulator hashes do not establish a physical board's
firmware, clock, RAM fit or performance. Use a separately qualified physical
firmware build if the installed runtime lacks those capabilities.

The app requests mode 136, 320x240 double buffered, with the production 256x160
3D view at (32,20), original HUD and retained static scenery. Package staging
is task-owned at 0x0a0000; the build rejects overlap with the application or
upper 64 KiB stack reserve. PRT1 must be idle. It is borrowed at reload 72,
divider 256 and nominal 18.432 MHz; a busy timer aborts rather than being stolen.

## Invocation after deployment/run authorization

Use fresh payload directories with no old `timing.bin`, `native.bin`,
`before.bin`, `after.bin` or `stack.bin`; the app deliberately uses create-new
file semantics. Preserve previous output on the host before making another
fresh copy. Do not overwrite the ordinary installed Wolf game directory.

For each arm, enter its directory and invoke its local binary, for example:

```text
cd /wolfperf/cpu
runbin ./wolf3d.bin
```

Repeat for `/wolfperf/unpaced` and `/wolfperf/paced` in separate fresh sessions.
CPU performs 600 preparation records without per-pose rendering. Unpaced
performs 600 hidden renders and only presents after timing, so a stationary
display during its measured interval is expected. Paced visibly turns twice
over 2,400 MOS ticks plus completion of the final frame. Assets, two warm-up
frames, native-log readout and SD writes are outside the measured interval.
Allow up to five minutes per process; first unexpected failure stops the set.

Success requires `WOLF-PERF-001 COMPLETE`, normal module UNLOAD, the farewell,
and the restored MOS prompt. On `FAILED` or panic, retain serial/video and
partial files; do not call it a performance result or automatically retry.
The failure handler stops its owned timer and verifies the old vector. It
then holds for diagnostic collection; recovery/reset follows separately
authorized bench procedure. Do not run the deliberate abort control on hardware
as an incidental part of these three performance arms.

## Retrieval and speed qualification

Retrieve `timing.bin`, optional `native.bin`, the memory/stack snapshots, input
receipts, actual firmware/MOS/module hashes and serial/video evidence into a
unique result directory per arm. Hash the retrieved files and verify the full
transfer. Leave the SD card mounted. On the development machine:

```bash
.venv/bin/python agonport/doc/tasks/WOLF-PERF-001/analyze.py RESULT_DIRECTORY
```

Require exact endpoints, zero enemies, matching native counts/angles, zero
unused slots, normal teardown and balanced stack/code integrity, as in the
emulator cohort. The analyzer alone does not establish those teardown checks.

No independent native-video capture is prepared for the first physical cohort.
Retain raw counters and nominal rates on the installed r2 diagnostic runtime;
leave absolute calibrated speed and optical presentation timing pending. Its
per-transaction debug logging is part of the observed end-to-end cost. The
complete disposition is in `hardware/COMPATIBILITY.md`.

For later calibrated work, compare PRT and MOS against an independent physical
time reference over the full paced rotation. Record the first visible rotation
and final pose on video;
retain frame-boundary uncertainty rather than using startup or SD-readout time
as the benchmark denominator. Verify the ESP32's actual clock before converting
CCOUNT to time. Compare the first and second revolutions separately. Only then
report physical completed-render throughput or presentation regularity. Enemy
AI and full populated-game CPU capacity remain outside this fixture.

An apples-to-apples physical Rally comparison also needs the same board,
firmware, clocks and completion/presentation definitions. Its different scene,
road coverage, actor workload and native physics must remain explicit.
