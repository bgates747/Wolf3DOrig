# WOLF-PIPE-001 — Independent simulation and newest-pose rendering

Draft source/design task, 2026-11-07. Smith wants Wolf to try Fsim's approach:
the eZ80 services input and advances physics independently, while the VDP draws
the newest complete state whenever it can. Maximum-rate presentation must be
available; an optional even 30 Hz presentation policy must not pace input or
physics. This task records that direction before implementation. The earlier
WOLF-GOAL-001 optimization goal remains paused; no build, run or bench reservation
is selected by this draft.

## Immutable subtasks

- [x] WOLF-PIPE-001-01 — Consult Fsim and verify its exact current Agon source:
  producer/input/physics scheduling, pose staging/commit, render worker, output
  buffer ownership and VGA presentation. Distinguish bespoke, VDPlet and host
  implementations, and supported behavior from a proposed design.
- [ ] WOLF-PIPE-001-02 — Review Wolf unit by unit against the target runtime
  before coding. Record supported methods and explicit incompatibilities; do
  not silently replace unsupported services or threading with workarounds.
- [ ] WOLF-PIPE-001-03 — Freeze the consumer/owner design, state ownership,
  presentation modes, elapsed-time semantics, finite qualification and resource
  requirements before implementation. Identify any required VDPlet-owner work.
- [ ] WOLF-PIPE-001-04 — Implement and qualify the selected independently
  scheduled input/physics producer and newest-state publication path, once the
  pre-code support gate is resolved. Preserve gameplay speed and ordered events.
- [ ] WOLF-PIPE-001-05 — Implement and qualify supported VDP receipt/staging,
  coherent snapshot selection and rendering/presentation overlap. Retain the
  fastest measured renderer as the drawing reference; report buffering costs.
- [ ] WOLF-PIPE-001-06 — Qualify uncapped and optional paced presentation with
  input service independent in both. Measure completed draws, actual buffer
  changes/cadence, pose age and input service gaps separately, including overload.
- [ ] WOLF-PIPE-001-07 — Publish matched results and a usable rotating-room
  review fixture, with exact identities, resource bounds and honest visibility
  limits. Any physical work requires its own frozen finite suite, current owner
  bindings, actual checkout, exact restoration and clean handback.

## Required behavior and design questions

The current benchmark performs pose preparation, submission, RUN completion,
C3 swap and an ordered INFO fence sequentially before the next pose. Removing
that eZ80 wait is only one part of the requested change: a VDP render worker
also needs an available drawing destination while a finished image awaits
presentation. Two VGA pages alone do not establish that freedom. Inspect Fsim's
actual separate render-output buffers and copy/presentation ownership before
choosing a Wolf design; extra memory/copy work must be counted.

Service input promptly even while drawing or waiting for presentation. Advance
movement, collisions and game time using defined elapsed-time/fixed-step
semantics, not one arbitrary movement increment per maximum-speed loop. Preserve
the original gameplay time scale; report any overload/backlog policy explicitly.

Publish only complete coherent snapshots. When a draw can begin, take the
newest available complete pose rather than replaying every obsolete queued pose.
Freeze that draw's state until completion while receipt can stage newer state.
If the supported protocol only allows one immutable RUN buffer, or blocks the
parser during rendering, record the incompatibility and owner dependency.
Latest-pose coalescing must not discard ordered gameplay events, world/map
changes, resource lifetime transitions or unacknowledged delta baselines. Specify
which state is replaceable and how nonreplaceable updates are committed.

Support maximum safe drawing/presentation throughput without a software FPS
cap. Optional 30 Hz presentation is a separate policy, not a simulation throttle.
Do not promise a rate above 30 from asynchronous poses alone: buffer ownership,
copy bandwidth, swap timing and scanout determine what can actually be shown.

Record sequence/time joins for produced, admitted, selected-for-render,
render-complete and displayed frames. An ordered query or swap acknowledgement
is not a timestamp of a complete physical raster. Report frame-interval
distribution and repeated scanout images where observable, rather than relying
on average FPS or calling draw capacity visible FPS.

## Consultation record

Smith directly requested consultation with the Fsim agent. The maintained Pi
sender accepted delivery `wolf-fsim-pipeline-consult-20261107-one` to Fsim thread
`01a11ddb-2f53-7700-b39f-eecc801e14b0`, turn
`01a1b786-01d8-7103-a337-b606b083e2cd`, at 2026-11-07T19:39:35Z.
Fsim returned substantive mail
`2026-11-07_14-43-02_fsim-pingo_wolf-independent-physics-newest-pose-source-one`.
Independent source reading and all five supplied SHA-256 pins match. See
[FSIM-SOURCE.md](FSIM-SOURCE.md) for the verified ownership/scheduling precedent
and explicit VDPlet gaps. Wolf's own unit-by-unit target-support review remains
pending; Fsim's bespoke worker is not a drop-in generic VDPlet service.
