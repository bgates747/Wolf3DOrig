# Actual correctness results

The permanent profiler and BJ-portrait disk cue are implemented. With profiling
disabled both normal binaries are byte-identical to their pre-change builds:
standalone276641B (`063f7ab7`), VDPlet288240B (`ab860121`). Five configurations
assemble, including explicitly pinned native-profile22572B module8d3d. Seventeen
decoder/format failure, wrap, gap and unavailable-native checks pass.

Oryx actual346 ran the four frozen Fab cases once each:

| Case | Result | Records/file |
|---|---|---|
| Actual profiler writer | PASS |240 /15424B|
| Injected short write | PASS expected disk-error3; torn file retained |120 attempted /31B|
| Native-data assembly join | PASS, synthetic provider explicitly marked |240 /15424B|
| Normal populated game, bounded held turn | PASS |250 /16096B,120+120+10|

All four owned emulator children returned0, entry/exit guest stack matched and
profiler timer ownership was retired. All704 retrieved files rehashed before
normal346 release20:36:07UTC; fresh whole-host idle passed, next null. Exact
source snapshots, results, raw files/captures and retrieval manifest are under
`build/oryx346`; this is correctness evidence, not a hardware performance result.

The full-game captures contain12 exact disk-icon crops in BJ's rectangle and71
subsequent face-restored HUD captures. `frame-0210.ppm` and `frame-0214.ppm` were
also viewed directly. The cue uses physical bitmap coordinates, avoiding the
retained3D viewport clip. Disposable correctness fixtures hold the cue200ms to
make capture reliable; the shipping implementation adds no hold. The native
join test runs real eZ80 join logic against synthetic WPN1 data; actual native
READ16/reset integration remains the separately frozen Olimex qualification.

Current normal-game builds keep their existing simulation scheduling and
render/presentation ownership. This task does not implement the independently
discussed newest-pose asynchronous pipeline or resume the optimization goal.
