# WOLF-PERF-003 hardware02 — loading fence continuation

Smith's Nov5 instruction to release Oryx, reserve Olimex and perform the
hardware suite remains the human authorization. Generation40 failed before
measurement; its evidence and clean release remain in HARDWARE-R01-RESULT.md.
This is a new identified task-owned setup correction, not a replay of that
failed binary. No additional component-owner implementation is requested.

Compile eight eZ80 guests serially on Pi (eight bounded120s children; expected
under two minutes, maximum16min;80C/512MiB guard, owned group cleanup). No native
firmware rebuild: A85c520a1, B7593b9cf, module1907ce17 and rollback remain exact.
All source files except loading_pages.inc, new loading_wait.inc and one call
after main in wolf3d.asm must equal hardware01. Timed bench/audio/render code
remains byte-identical. Assembly and source-contract checks precede readiness.

Loading sends each ordered mode query once. After a MOS0x41 timeout it can wait
again on the same pending flag, up to ten public waits. An independent1200-MOS-tick deadline is checked after
each public wait (nominal10s, not externally calibrated); the final polling
call may extend past that deadline before returning. No intermediate flag
clear, query resubmission, render/C3 replay or timer-path extension. Preserve
both pages. Extender's exact-installed-source advice confirms wait-only reentry
is compatible, not physically qualified. Keep the independent300s invocation
bound; first unexpected failure stops further dispatch.

A new48B loading.bin, written only after main returns with all loader files
closed, records raw MOS elapsed ticks, wait status, timeout/recovery counts,
phase and asset counts. Create-new writer returns safely on failure. Do not
write files from within AGNB callbacks. A recovered timeout is diagnostic
information, not a measured renderer speed or proven receiver defect.

After source/build checks, obtain a new Olimex reservation and actual grant.
Reuse stable /test/wolf/perf003 after a known-file reconciliation; preserve
hardware01 evidence locally and verify reused assets independently. Replace
only the eight known executable files, maintain staged journals/readbacks,
clean known backup only after verified activation. Preserve arbitrary files.
Save generated wolf3d.cfg before resetting it to the original empty input for
each independent fixture. Archive new loading.bin before clearing outputs.

Select the same finite14-fixture ABBA suite and eight B resource probes as
HARDWARE-RUN-01.md. First changed A control is a setup gate: if loading.bin or
its actual MOS return fails, dispatch no successor. Recognize early AGNB
failure only once the post-RUN prompt proves return, then retrieve diagnostics
and RAM before any LOAD. No automatic replay. Whole run deadline45min; each
fixture/probe300s, transfers original bounded jobs, four app-span writes with
independent readback. Preserve current exact entry components/boot and restore
the incoming app/touched tail before clean mode0/callbackzero/CLI/input/idle/
freeports release. SD remains mounted. Fresh component reconciliation and
scheduler grant remain mandatory; generation40 token is invalid.
