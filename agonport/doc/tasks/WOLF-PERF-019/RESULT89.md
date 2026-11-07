# Startup stopped before the first test: actual89

The independent chains/trig comparison produced **zero room frames and zero
INFO queries**. It stopped after the exact timed-native image was installed
and independently read back, when the current matched bootstrap could not
establish Agon boot/input admission. No room guest or module was loaded or run.
There is **no performance result** for either arm and no automatic retry.

The original reset helper reported a boot/connectivity deadline with readyfalse,
reason0. That does not establish a root cause. Original bootstrap logs, keyboard
state, reset journals and the first failure are retained. No original RAM was
saved: remote input was unready and no guest existed. Later cleanup state is
explicitly post-restoration/post-bootstrap, not substituted original RAM.

Original driver PID1415850/session76691 exited1. A separately frozen cleanup-only
helper used the original grant and byte-identical549-input kit in a fresh output
namespace. It invoked no suite, probe, entry constructor side effect, room LOAD
or RUN. It restored the exact incoming **1105920-byte** native/tail span FIRST,
independently read it back as
`85f9cf31219d679cffef48029d736331a3a3dfc78511d19d48a04cd2bd6a74de`,
then performed one current matched bootstrap and the complete handback.

The reset ledger contains one matched P4 initialization/Agon-reset sequence on
the original timed image, which failed admission, and one on the restored
incoming image, which passed. No recovery-specific attempts or suite replay
followed. The esptool hard-reset path can reset both mainboard processors; these
counts describe the explicit bootstrap sequences, not isolated VDP-only resets.

Cleanup PID1418333/session50170 exited0 with owned children joined. Fresh rootCLI,
rawmode0/callback0/route0, whole startup/listener, neutral input, offline listener,
idle worker and free USB checks passed. Normal release completed
**2026-11-07T14:45:59.234980UTC**,44.970 seconds after the original final observation.
All Wolf target access stopped; SD remains mounted. Actual-next MechAgon
GOAL-001-IRQ-DIAG-R06 and Extender were notified before offline reporting.

[Verified failed-cohort/restoration result](results/actual89/RESULT89.json),
[original and cleanup evidence pins](results/actual89/SHA256.json),
[independent offline verifier](report89.py) and
[frozen cleanup-only helper](cleanup89.py) retain the distinction between failed
benchmark startup and successful restoration/release. Source, target and producer
qualification remain valid as their own evidence; physical chain/trig timing
and native branch counts remain unmeasured.
