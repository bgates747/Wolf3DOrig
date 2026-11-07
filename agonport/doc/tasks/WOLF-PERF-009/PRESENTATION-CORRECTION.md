# Correction: hidden drawing was wrongly announced as visible rotation

Smith reported a steady native VGA scene during the specifically announced
candidate interval in actual75. Wolf incorrectly told him to watch for visible
rotation. The exact fixture source explains his observation: unpaced bench.inc
wp_next applies/render600 changing poses into the hidden surface; after the
loop it stops PRT timing and only then calls w3d_vdu_present once. Two full turns
finish at the initial heading. There is no per-pose presentation in this path.

The current source/header/native logs identify600 submitted headings and native
draw-call intervals, not600 displayed frames. A completed hidden draw rate is
not measured visible/gameplay FPS. Earlier unpaced reports using the same method
must be read with this correction; retained raw records are not being relabeled
or rewritten. The independently presented paced fixture that Smith previously
confirmed is a different artifact, not validation of current unpaced output.
Actual visible rotation and display cadence need a separately selected fixture
that presents each pose; do not silently add swaps to a frozen draw-capacity arm.

The first two control cases have another purpose: wp_run initializes the owned
PRT, sets expected_abort and jumps to wp_failed before warmup/render measurement.
They check timer/vector/interrupt restoration and MOS return. They should be
separate clearly named harness checks, not unexpected static preludes to a
human-requested rotation. Smith explicitly requires STATIC TIMER TESTING ONLY
(and no-rotation wording) if that fixture is used again. PERF010 owns this label.

Actual75 was deliberately stopped by Wolf SIGTERM, not an unknown supervisor.
Cases01–05 and six resource probes were collected; case06 selected/restored the
baseline module and began typing its VDU marker, but neither LOAD nor RUN was
issued. Five local case receipts remain raw execution/collection receipts, not
optical acceptance. The balanced comparison is incomplete and no visible/FPS
verdict is published from it. New source files must not reopen this stopped run.

Incoming native/tail1105920bytes85f9 were restored and independently read back.
Ordinary cleanup bootstrap failed readiness; one supported Agon-only recovery
also failed, followed by one supported initialized-P4→Agon recovery which passed
actual CLI/rawmode0/callback0/route0/wholefiles/inputneutral/offlineidle/freeUSB/
joined actors. Actual75 clean release2026-11-07T07:18:38.955558+00:00, next actual
MechAgon1b46642ee71b notified immediately with Extender. No reflash after original
restoration, no fixture replay, SD remains mounted. Complete reset/action ledger,
original failures and release are retained under build/hardware01.
