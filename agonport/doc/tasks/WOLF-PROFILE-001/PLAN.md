# WOLF-PROFILE-001 — Optional full-game performance recording

Contract, 2026-11-07. Smith requests profiling the normal game client with
timing fences, RAM-buffered results and periodic disk logging. The facility
should be a permanent compile-time option. He explicitly accepts visible disk
write hitches and asks to replace BJ's HUD portrait with a disk icon during
writes. This supersedes the suggested separate small SD indicator.

Smith directly instructs: once the task and discussion notes are written,
commit/push and proceed directly on this task. This selects profiling
implementation, serial compiler checks and necessary finite correctness
qualification. The earlier optimization goal remains paused. Independent
pipeline work is tracked separately in WOLF-PIPE-001; it is not silently resumed
or implemented as part of profiling. Hardware/emulator use retains normal actual
checkout and concrete finite run/cleanup preparation before dispatch.

## Immutable subtasks

- [x] WOLF-PROFILE-001-01 — Inspect the normal game loop, supported clocks,
  renderer/reply/fence services, disk API, build options and HUD portrait path.
  Resolve unsupported timing/ownership methods before implementation.
- [x] WOLF-PROFILE-001-02 — Freeze the compile-time switch, binary record format,
  record-buffer memory budget, flush policy, measurement boundaries and error/
  overflow/exit behavior. Preserve gameplay time and exact component identities.
- [ ] WOLF-PROFILE-001-03 — Add optional normal-game timing and fixed-size RAM
  recording. Link pose/frame IDs across input/physics, preparation, submission,
  remote drawing and presentation-fence completion where supported. Disabled
  builds omit instrumentation, recording storage and profiling disk operations.
- [ ] WOLF-PROFILE-001-04 — Add bounded periodic batch logging and BJ-portrait
  disk cue. Present the cue before I/O, retain it during the flush, and restore
  the face appropriate to current game state afterward, across both HUD pages.
- [ ] WOLF-PROFILE-001-05 — Qualify normal/profiling builds, record joins, clock
  rollover, disk failures/full-card/overflow and stop/exit behavior. Verify
  indicator visibility, current-face restoration and independent game timing.
- [ ] WOLF-PROFILE-001-06 — Publish a decoder/report and qualified full-game
  review build. Keep real elapsed results and logging-excluded analysis distinct;
  physical testing requires its own finite freeze/current bindings/actual lease
  and exact restoration/handback. Leave the SD card mounted after deployment.

## Measurement requirements

Concrete source support/implementation selection: [PRE-CODE.md](PRE-CODE.md).
Permanent build switches, exact record layout and timing/error limitations:
[FORMAT.md](FORMAT.md). The task's real assembly/decoder qualification precedes
its separately bounded [emulator correctness cases](EMULATOR-PLAN.md).

First implementation targets the real maintained assembly game client and its
supported bespoke/VDPlet backend boundaries. Inspect existing native timing
availability before promising VDP-side durations in an ordinary firmware build.
Unsupported measurements must be marked unavailable, never inferred by
subtracting unrelated clocks or requiring an unannounced firmware replacement.
Use the existing fastest measured module as an explicit separately bound
profiling-review configuration where source/runtime support permits; keep
production renderer adoption separate from adding the build switch.

Compiler qualification is serial under Pi5's canonical build FIFO: finite
assembly/link and focused actual-code/decoder checks, at most 10 minutes per
declared tranche, joined owned children and normal self-release. Resource
budget and exact commands will be recorded after source inspection, before
launch. Emulator and physical suites need separate finite plans/current actual
bindings; no automatic deployment or looped replay follows a failed test.

Use buffered binary records rather than per-frame formatting/file writes.
Flush at a controlled supported boundary with coherent record ownership; never
mutate memory still owned by an in-flight renderer, disk operation or reply.
Specify buffer exhaustion and disk errors explicitly; do not silently discard
samples, hang forever, or mislabel incomplete records as completed frames.

Record the start/end of disk operations and cue/presentation overhead. Those
intervals are excluded from rendering-throughput windows without creating a
false long frame across the gap or subtracting overlapping durations twice.
Retain actual wall time and logging-gap durations so visible hitches remain
explainable. Keep the gameplay clock correct: excluding a logging interval from
analysis must not silently stop simulation time or change movement speed.
Later physics catch-up or changed cache effects cannot be undone by subtracting
the file-write duration; report that limit rather than fabricating a clean run.

Drawing completion, parser/fence completion and actual physical scanout are
separate events. Only claim what the supported clock/fence observes. Profiling
must exercise ordinary gameplay, including movement, enemies and changing views;
the deterministic rotating-room fixture remains a separate comparison.

## Disk icon and double-buffered HUD

While a profiling batch is being written, replace BJ's face in its existing HUD
rectangle with a disk icon. Keep the cue opaque and within that rectangle; no
separate SD text or additional screen region is requested. Make the icon reach
the visible page before starting synchronous disk I/O. Merely drawing it onto
the hidden page and blocking before the flip would fail the requirement.

Keep per-page HUD bookkeeping coherent so the icon neither disappears on a
swap during the write nor remains stale on a later alternate page. Prevent the
ordinary portrait updater from overwriting the active cue. At completion or
write failure, clear the cue state and restore the correct current health/face
expression on each page as it is prepared for display; do not restore an old
saved expression or write into a page owned by scanout. Cue setup/restore and
any required flush fence belong to explicit logging overhead, not renderer
speed claims. Smith accepts the visible write hitch; no artificial minimum
icon hold or additional pacing delay is requested.
