# Presentation plateau: matched source and existing phase evidence

Read-only goal07 progress; no new device run, firmware change or drain removal.
All six relevant graphics files from VDPlet WAD003 independently rehash equal
inside the exact retained7593 benchmark source export. The7593 BIN also matches.
This closes the earlier source-identity caveat for those files, not clock or
optical attribution. Full pins and actual78 phase means are retained alongside.

Mode136 is double-buffered320×240 at nominal60Hz. Its C3 switchBuffer calls
Canvas.swapBuffers; SwapBuffers always queues and, under double buffering,
blocks on the notification from its executor. The executor swaps and notifies.
CA waitPlotCompletion defaults false and Canvas.waitCompletion(false) processes
primitives immediately. It is not an unconditional second VBlank delay. Keep
both existing presentation and ordered-ingress accounting boundaries intact.

Actual78 was uncapped,600 complete steps per run. The mean guest reply-wait
and following presentation+fence phases move in opposite directions while the
presentation interval remains about33.27 nominal PRT ms:

| Scene/arm | Reply wait ms | Presentation+fence ms | Active ms |
|---|---:|---:|---:|
| Room A |25.3783|5.1150|33.2583|
| Room B sprite-hoist |26.0650|4.4800|33.2600|
| Sprites A first |28.0800|2.9067|33.2850|
| Sprites B first |27.9417|3.0283|33.2850|
| Sprites B second |27.7400|3.2850|33.2783|
| Sprites A second |28.0217|3.0100|33.2850|

This is consistent with work changes being absorbed by a presentation wait at
unchanged cadence. It supports Smith's caution that no FPS gain alone cannot
dispose an optimization's resource value. It does not isolate C3 from the query/
serial component of the combined presentation bucket, prove a scheduling cause,
or measure exclusive busy CPU, power or other-task resource savings. Guest ms
have1ms resolution; native draw CCOUNT is separate inclusive local elapsed time.
Do not subtract those different clocks and label the residual exclusive work.

The fixture's source stamps before preparation/upload/RUN completion, then
before C3 and after the ordered fence. The current bracket already separates
reply wait from presentation+fence, but cannot divide the latter into swap wait,
serial transfer and query processing. A future selected timing contract would
need that additional observability through supported owner interfaces; not a
blind removal of fences, hidden-only draw rate or a private Canvas/timer import.
No such new physical axis is selected here. Exact renderer work reduction and
uncapped visible output remain the current practical candidates.

## Existing actual81 records: same-clock phase check

The measured cyan-fill correction reduced inclusive native drawing time by
13.7%, while completed presentation remained about30.06fps. An additional
offline check uses only the already-retained guest-clock records: exclude the
first phase row and compare599 successive presentations per run. There is no
new target observer or subtraction between guest milliseconds and CCOUNT.

| Run | Reply wait ms | Presentation/fence ms | Interval counts,33ms /34ms |
|---|---:|---:|---:|
| A first |25.411|5.142|437 /162|
| Cyan correction first |22.528|8.037|437 /162|
| Cyan correction second |22.339|8.162|438 /161|
| A last |26.232|4.274|437 /162|

Within each run, reply wait and presentation/fence are negatively associated
(correlation −0.785 to −0.826; fitted descriptive slope −0.808 to −0.846).
The unchanged33/34ms interval distribution and compensating phase movement
strengthen the existing observation that work reductions can leave cadence
unchanged. They do not identify a second VBlank, receiver scheduling, serial
cost, a fence defect, exclusive CPU usage or power savings. A conditional fit
is descriptive; no timing model or cause has been established.

[Reproducible offline analysis](analyze_plateau81.py) and
[exact input pins/output](PRESENTATION-81-PHASES.json) retain all four cases.
The599-interval steady rate differs slightly from the whole600-frame duration
reported for actual81 because the initial phase is excluded here. The original
actual81 result remains unchanged.

[Source pins and existing raw-report joins](PRESENTATION-SOURCE-PINS.json),
[owner advice](/Agon/mystuff/agon-vdplet/docs/tasks/VDPL-034/WOLF-ADVICE-2026-11-07.md),
[reopened sprite discussion](../WOLF-PERF-013/REVISIT.md).
