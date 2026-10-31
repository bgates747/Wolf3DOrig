# Wolf3D production VDPlet batch regression

This project exercises the real eZ80 serializer in
`../wolf3d/src/wolf3d_vdplet_batch.inc` under MOS. It does not reconstruct the
wire stream in Python.

The fixture emits and validates:

- a complete generation-1 level snapshot;
- a byte-identical generation-1 retry after simulated RUN failure;
- dirty state accumulated while generation 1 was in flight;
- a generation-2 delta containing player, door, actor removal, static removal,
  complete HUD, and view-weapon records;
- first-submission dirty consumption, retry preservation, successful commit,
  and refusal to fabricate an empty generation.

Run from the repository root with the project virtual environment:

```sh
.venv/bin/python src/asm/wolf3d_vdplet_batch/scripts/run_regression.py
```

On a host without a native Fab/Flexe executable, retrieve the four target
files (`batch.dat`, `full.bin`, `retry.bin`, and `dirty.bin`) into one directory
and run the same byte validator without launching another emulator:

```sh
.venv/bin/python src/asm/wolf3d_vdplet_batch/scripts/run_regression.py \
  --results-dir /absolute/path/to/results
```
