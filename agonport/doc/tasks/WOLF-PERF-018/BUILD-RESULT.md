# Scaling setup cache: host and target-code qualification

The one-entry full-height cache passes **5,376 independent scalar wall cases**
and the existing renderer, module, span and600-pose frame/state parity checks.
The target control reproduces exact accepted a926. No hardware speed result or
production adoption is claimed.

| Arm | Package bytes | SHA256 | Resident data |
|---|---:|---|---:|
| Original |24420|a926b48ab3207b59773cc8283d59cc687f274ef2af00017451567449a4c69656|13348|
| Cache |24480|2a249f85e6e88559e1e32d7c9af6906a4f543a693f97f07aa5b0799a53505ed8|13348|

Cost is **60 package bytes**, no resident-data increase. Both emitted renderer
frames are352B with draw_walls inlined. The selected synchronous wall/acquire
path is896B module frames plus384B native prefix and64B native acquire,
**1344B against4096B task stack**, unchanged between arms. This selected path
is not a universal exception/ISR/foreign-callback peak; actual cumulative INFO
watermark and first-fault limits still apply before physical results.

The target equality branch at2139 jumps to2178, bypassing the scaling arithmetic
and QUOS at2166 for identical full heights. The original column sampler/read/
store order is retained. Compiler flags, ABI1.6, capabilities257, PIC, PSRAM
workaround, local providers, section/export/size and individual-frame gates
pass under the existing safe SDK policy. No library/provider/runtime change.

The scalar oracle covers repeated and split heights, equal clipped extents with
different full heights, nonpositive through INT32_MAX heights, every encoded
tile and doors/invalid IDs, null statistics, arbitrary/overlapping masks, mapping
bias/XOR, guards, null/short/refused assets and release failure. It explicitly
exercises identical and partially overlapping destination rows and aliased
source/frame storage. Exact original lease order, error precedence, pixels and
statistics agree; this avoids the row-major grouping alias problem.

Existing six-scenario host parity metadata contains153600 valid wall columns.
119190 setups could be reused (**77.60%**), leaving34410 evaluations;151–249
reuses per frame. This count is from host parity scenes, not the physical E1L1
room, and is neither native hit instrumentation nor a speed measurement.
A separate source-bound canonical-room census now passes: exact E1L1 W3L map,
door seed and camera(34,36),600 scripted poses through the unchanged original
cast_walls. It finds113434 eligible reuses of153600 wall columns (**73.85%**),
leaving40166 setup evaluations;153–236 reuses per frame. This is host opportunity
classification, not native hit instrumentation or timing. Compiler359 completed
in4.062s, children joined, normal release13:06:58.156903UTC. No test was added to
active PERF017/actual85. [Raw census receipt](results/room-count01/receipt.json).

Both actual uncapped eZ80 room guests also assemble and independently qualify.
Original reproduces exact accepted c43e7; candidate differs only in the bytes
of six actual linked package-size/strict-limit operands, matching24480/24481.
SP label addresses and presentation calls remain unchanged. Compiler361 children
joined; normal release13:09:36.929585UTC, no next. This producer check does not
stand in for resident RAM verification after a future actual hardware run.
[Producer receipt](results/guests01/receipt.json).

Actual serial compiler354 completed in105.765s; all children exited and normal
release completed2026-11-07T12:57:52.262887UTC, with no next request.99 selected
input identities were snapshotted before checklist disposition. Full source,
SDK, target packages/ELFs/commands/static frames, logs, scalar test, output hashes
and release are retained in [results/build01](results/build01/SHA256.json).
The large host frame dumps remain local with their verified output hashes.
