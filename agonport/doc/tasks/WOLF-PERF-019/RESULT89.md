# Startup stopped before the first test: actual89

The original reset helper reported a boot/connectivity deadline with readyfalse,
reason0. That does not establish a root cause. Original bootstrap logs, keyboard
state, reset journals and the first failure are retained. No original RAM was
saved: remote input was unready and no guest existed. Later cleanup state is
explicitly post-restoration/post-bootstrap, not substituted original RAM.

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

For all Olimex bench procedures, use the sole authoritative [bench guide](/Agon/mystuff/agon-extender/docs/operations/olimex-bench/README.md).
