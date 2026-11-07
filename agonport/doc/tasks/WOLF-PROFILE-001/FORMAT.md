# Full-game profiler interface (WPF1)

Build the normal client with `--profile` using
`src/asm/wolf3d/scripts/build.py`. This works with `standalone` or `vdplet-direct`;
the latter retains its required explicit `--module` argument. For VDP drawing
cycles as well, add `--profile-native` and supply the pinned combined021 timing
module (22572B, SHA8d3d19bb74e1f2ea862b2154c038dfd23de2fd741fd1831d1880d849b5ad838b).
Unknown native timing providers are refused before assembly. The ordinary
selector remains unchanged. Each output has a JSON build receipt including the
exact module identity and separate `-p`/`-pn` executable name.

Examples from the project root, under the normal compiler FIFO:

```bash
.venv/bin/python src/asm/wolf3d/scripts/build.py --backend standalone --profile
.venv/bin/python src/asm/wolf3d/scripts/build.py --backend vdplet-direct --profile --profile-native --module agonport/doc/tasks/WOLF-PERF-021/results/build01/candidate/module/wolf_perf.vdpl
.venv/bin/python src/asm/wolf3d/scripts/decode_profile.py WOLFPROF.BIN
```

The dedicated `WOLFPROF.BIN` in the game's working directory is overwritten on
the first successful flush of a new program run and appended thereafter. Copy
an earlier run before starting another. No save/config/asset file is used for
recording. Record buffer8192B plus code/state/icon is compiled out entirely
when profiling is off. Flush after120 completed renders or5nominal seconds at
the next normal completed frame; a final idle shutdown flush drains leftovers.
No record is emitted for fizzle-only operations, and unusual render purposes
defer the periodic icon/flush to avoid disrupting their presentation sequence.

PRT0 uses the retained nominal1ms donor, only if inactive, and is restored at
program exit. Its24-bit count wraps after roughly4.66hours. Busy timer status1
disables ordinary eZ80 recording; a native-profile build cannot safely run its
finite logger without collection and refuses that gameplay session. Disk error3
stops ordinary recording; the native-profile game exits through its existing
drained error path rather than eventually overflowing the finite VDP log.
Protocol/uncertain ownership status4 stops safely and retains unflushed RAM;
status2 is a full buffer and5 a timer-vector restoration mismatch. There is no
until-success retry. A short/torn disk write is preserved for explicit decoding
failure or `--salvage` of preceding complete blocks. MOS fclose supplies no
filesystem durability status; byte-count checking is not a power-loss guarantee.

## Blocks

Little-endian32B header followed by `count`64B frame records:

| Offset | Bytes | Meaning |
| --- | --- | --- |
| 0 | 4 | `WPF1` |
| 4 | 1 | version1 |
| 5 | 1 | backend0 standalone,1 VDPlet |
| 6 | 1 | clock1: nominal1ms PRT interrupt |
| 7 | 1 | bit0 native timing present; upper nibble status |
| 8 | 2 | count1..128 |
| 10 | 2 | record size64 |
| 12 | 4 | monotonically increasing block number (low24 used) |
| 16 | 4 | previous logging gap start (low24) |
| 20 | 4 | previous logging gap end (low24) |
| 24 | 4 | previous disk open/write/close start (low24) |
| 28 | 4 | previous disk open/write/close end (low24) |

A write cannot contain its own eventual completion time. The next block carries
the previous flush's complete gap; the terminal gap is explicitly open-ended
on disk if there is no subsequent block. There are no later frame measurements
to contaminate after that terminal gap. Real elapsed fence intervals across
blocks retain prior logging cost; active-rate estimates use only contiguous
within-block intervals, excluding cue frames, failed-attempt gaps and sessions.
This does not erase later catch-up/cache effects or instrumented-build overhead.

## Frame records

| Offset | Bytes | Meaning |
| --- | --- | --- |
| 0 | 3 | attempted frame sequence; gaps identify discarded incomplete attempts |
| 3 | 3 | prepare entry, before visibility promotion/serialization |
| 6 | 3 | submission bookkeeping finished |
| 9 | 3 | IRQ callback receipt; may precede submission return |
| 12 | 3 | validated completion consumed, before cue/presentation |
| 15 | 3 | C3 synchronous sender returned |
| 18 | 3 | ordered INFO fence returned; not optical scanout |
| 21 | 3 | maximum input-service interval since previous preparation, excluding logging gap |
| 24 | 3 | cumulative inclusive input/clock/physics foreground elapsed milliseconds |
| 27 | 3 | simulation credit at preparation; not completed physics-step count |
| 30 | 4 | native draw cycles (unavailable unless flag set) |
| 34 | 4 | native row/resource/draw scope cycles |
| 38 | 4 | native dispatch cycles |
| 42 | 1 | bits0 cue/logging,1 native valid,2 callback observed,3 submitted,4 completed fence,5 session start |
| 43 | 1 | zero |
| 44 | 1 | backend |
| 45 | 1 | submission's semantic render purpose |
| 46 | 2 | player heading in degrees |
| 48 | 4 | signed16.16 player X |
| 52 | 4 | signed16.16 player Y |
| 56 | 3 | cumulative discarded incomplete attempts |
| 59 | 1 | zero-based native/frame index in this block |
| 60 | 4 | native raw PRID, zero when unavailable |

Native collection checks WPN1/version/exact count, per-row index and exact
heading before attaching cycles; it uses the actual loaded module handle.
Collection and RUN100 reset occur only after owner release. A fresh profiled
game allocates F000/12056B and EF00/768B icon storage; clean shutdown clears them.
There is no periodic read/query during an in-flight draw.

Disk cue is an opaque24x32 image in BJ's existing rectangle at136,204. The stock
physical-coordinate bitmap command avoids any retained3D clip. It is drawn
onto the completed hidden page BEFORE its ordinary swap; an ordered INFO fence
precedes collection/write. Ordinary full rendering reconstructs current face/HUD
on each page afterward. No extra production hold or software FPS cap is added.

All native cycle conversions assume the explicitly configured240MHz reference;
preemption/service time is included. PRT interrupt delay/coalescing and profiler
hook/fence overhead remain measurement limits. No combination of these fences
is an optical timestamp or a promise of maximum uninstrumented gameplay FPS.
