# r06: correct bespoke map binding and visible loading breadcrumbs

WOLF-PERF-003-11 [x] Loading progress implemented on both task apps.
WOLF-PERF-003-12 [x] Scene discrepancy traced and corrected; Fab visual passes.

The old A task warmup called w3d_submit_dirty_world_render after setting dirty
flags, which replays objects/pose but never sends INIT_LEVEL. Native world map
ID stayed zero; GetTile treated the missing buffer as solid wall. Correct wire
camera coordinates alone therefore did not establish the intended scene.
B's initial batch reset binds its map; no B renderer geometry change is needed.

Fix: A's first setup frame now uses ordinary w3d_submit_level_reset, waits for
completion, presents/fences, then performs the second ordinary warmup. The
future standalone_bench generator and reproducible r06 derivative builder both
contain the correction. Old snapshots/results are unchanged. All pre-r06 A
runtime performance results are disqualified as a canonical-room baseline;
their transport/timer observations remain retained. Host parity had initialized
the map directly, so it did not cover this actual guest initialization defect.
Reopen -04 for corrected native runtime qualification; -05 remains incomplete.

Both apps retain the game's per-finalized-image/per-audio-sample dot callbacks.
A setup-only present and ordered ingress fence now make each breadcrumb visible
instead of leaving it on the hidden page. Assets-loaded/preparing-room cue added.
Two full warmups clear both pages before measurement. Timed loops for all six
positive guests compare byte-for-byte as source; all non-executable payload
bytes/module/assets remain identical. No timed logging/audio/SD introduced.
Seven eZ80 builds pass on Pi153, released20:35:36UTC,nextnull. Tool path failure
and partial preparation anchor failure retained separately; no tool installation.

Fab visual check uses exact corrected A producer and retained userspace native
Wolf5c4e4b9/Fab1.2.5. A named visual-only guest omits task CCOUNT reset/dump,
which that userspace library does not support. It is not a timing artifact.
Completed600poses/two turns, normal Quit0, whole54.719s including loading,
peak63.875C.62retrieval hashes verify. Loading and room screenshots under
results/r06; raw captures/result/driver/input pins in build/r06/fab-result.

B's source is corrected for loading progress and assembled. Existing exact
production host eight-heading pixel/geometry parity remains applicable to its
unchanged renderer. There is no ready Fab adapter executing its Xtensa module;
owner review2026-11-05_15-36-50_vdplet_wolf-perf003-fab-visual-advice-return-one
explicitly confirms that gap. This work neither substitutes a fake module nor
claims a new B Fab/runtime/hardware qualification. No generic runtime changes.

Fresh STOPPED review fixtures on Oryx:
.emulator/wolf-perf003-fixed-review/bespoke-fab (Fab visual-only),
bespoke-flexe and vdplet-flexe (corrected native benchmark guests). Previous
human01 runs preserved. To review Fab from Wolf root:
.venv/bin/python agonport/doc/tasks/WOLF-PERF-003/fab_visual.py run --visible --profile .emulator/wolf-perf003-fixed-review/bespoke-fab
Do not reuse the already-consumed automatic r06a profile without preserving outputs.

Oryx312 remains held at Smith's explicit instruction. No GUI launched on his
behalf, no lease release, host changes, hardware/flash or publication performed.
