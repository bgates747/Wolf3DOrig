# Presentation and profiling discussion — 2026-11-07

Smith observed uneven rotation and asked whether mixed one-refresh/two-refresh
cadence could explain it. This has NOT been ruled out by software timestamps.
Earlier wording that implied a 60 Hz display necessarily limits a 20 ms
renderer to 30 fps was too broad.

The strongest completed combined renderer measured about20.90ms inside
`render_world_direct`: computations AND actual framebuffer pixel writes,
including background, walls, sprites, weapon, HUD and palette processing.
The measurement ends before presentation. It is not just queued drawing setup.
Measured completed-presentation software intervals were33/34ms and about30.06fps.
Those fences wait for executed swap code and an ordered reply, not observation
of a whole physical raster. Extra sequential work between successive end stamps
is included in the interval; attributing that interval and observing displayed
frame identity remain separate questions.

A strict render-then-wait-for-flip-then-render loop can quantize a20ms draw to
33.33ms at60Hz. With sufficient independent image ownership and scheduling,
20ms production can instead approach50distinct images/s with uneven refresh
durations. This is a mathematical possibility, not Wolf's measured capability
or a promise that direct-row double buffering alone can achieve it.

The older CPU-only room test measured roughly1.1ms for scripted pose+packing
(about900/s), or roughly2.16ms including VDPlet serializer bookkeeping (about
460/s). Neither includes populated-world AI/movement/collision simulation.

Smith's desired architecture: eZ80 input/physics runs independently as fast as
practical, preserving actual game time; publish latest coherent poses; VDP
takes the newest complete pose whenever it can render. Maximum-rate uneven
presentation must be available; optional even30Hz presentation must not throttle
input/physics. Fsim consultation/source verification is in FSIM-SOURCE.md.

Smith says Fsim is now consulting VDPlet about the missing port overlap. Wolf's
separate profiling work must not assume that dependency has been resolved.

Smith requests a permanent compile-time full-game profiler, RAM buffering and
periodic disk writes, with logging intervals excluded from throughput analysis.
He explicitly understands and accepts visible disk hitches. His selected cue
is to replace BJ's HUD face with a disk icon during writes, restoring the
appropriate current expression afterward. The cue must actually be presented
before blocking disk I/O in double-buffered mode. Gameplay time keeps running;
real elapsed time and logging gaps remain recorded. See WOLF-PROFILE-001.

Smith then explicitly instructs committing/pushing these task/discussion notes
and proceeding directly with the profiling task. This does not resume the
earlier paused optimization goal or assign implementation to Fsim/VDPlet.
