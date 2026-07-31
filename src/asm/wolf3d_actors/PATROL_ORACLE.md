# Patrol host oracle and vector ABI

The scripts in `scripts/` are the independent executable specification for
the first actor state-runner and path-patrol slice. They model externally
visible world behavior rather than eZ80 register flow.

Authoritative original-source cross-references are:

- `orig/src/WOLFSRC/WL_PLAY.C`: `DoActor`;
- `orig/src/WOLFSRC/WL_ACT2.C`: path state declarations, `SelectPathDir`, and
  `T_Path`;
- `orig/src/WOLFSRC/WL_STATE.C`: `TryWalk` and `MoveObj`;
- `orig/src/WOLFSRC/WL_ACT1.C`: `OpenDoor` and door animation;
- `orig/src/WOLFSRC/ID_US_A.ASM`: deterministic initial random phases.

The settled port contract keeps original 70-Hz state durations and speed
units. One global 30-Hz cadence emits `2,2,3` original tics, beginning with
two. Actor records remain 39 bytes. Movement is exactly `speed * tics`, with
no per-actor fractional remainder. The original zero-`ticcount`
non-transitional latch is intentional and tested.

Run all host checks from any directory:

```sh
cd src/asm/wolf3d_actors/scripts
../../../../.venv/bin/python -m unittest -v \
  test_actor_oracle.py test_patrol_vectors.py
```

Generate a binary or ez80asm include:

```sh
python generate_patrol_vectors.py --out /tmp/patrol_vectors.bin
python generate_patrol_vectors.py --out /tmp/patrol_vectors.inc
```

Both encodings begin with a 16-byte `W3PV` version-1 header. It contains
magic, version, record size (192), record count, and deterministic seed. Each
fixed record has this layout:

| Offset | Size | Meaning |
|---:|---:|---|
| 0 | 2 | case id |
| 2 | 2 | fixed-frame count |
| 4 | 1 | initial actor-clock phase |
| 5 | 1 | initial door-clock phase |
| 6 | 1 | actor slot id |
| 7 | 1 | door index, or `0xff` |
| 8 | 4 | player X, signed 16.16 |
| 12 | 4 | player Y, signed 16.16 |
| 16 | 39 | complete initial actor record |
| 55 | 39 | complete expected actor record |
| 94 | 10 | initial door record, or zeroes |
| 104 | 10 | expected door record, or zeroes |
| 114 | 2 | initial door timer |
| 116 | 2 | expected door timer |
| 118 | 1 | expected actor dirty boolean |
| 119 | 1 | expected door dirty boolean |
| 120 | 1 | final actor-clock phase |
| 121 | 1 | final door-clock phase |
| 122 | 1 | expected actor-present boolean |
| 123 | 1 | sparse patch count, maximum eight |
| 124 | 4 | reserved zeroes |
| 128 | 64 | eight 8-byte sparse cell patches |

A sparse cell patch is
`x,y,tile,path,area,static-blocked,actorat-in,actorat-out`. Unspecified
interior cells are open area zero, have no path arrow (`0xff`), no static, and
no actor. This lets a direct eZ80 fixture initialize and compare occupancy
without reproducing patrol decisions in test assembly.

The eleven durable cases cover the `2,2,3` cadence, zero-tic latch, same-shape
pause dirtiness, shape-changing dirtiness, dog residual movement through a
path arrow, dog rejection of a non-open door, guard door reservation/wait,
door-before-actor ordering, inclusive player overlap, and real medium E1L1
slot 11 crossing door 8 after 92 fixed frames. The final corruption case feeds
the signed wait value `-257` while door zero exists and proves that the complete
int32 value fails closed at `NODIR` instead of aliasing door zero through its
low byte; the actor remains live, neither object becomes dirty, and the door is
unchanged.
