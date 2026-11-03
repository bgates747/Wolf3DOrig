# Wolf3D original-parity target batch

This directory owns the finite headless batch used to qualify parity work that
spans several direct eZ80 fixtures. Each constituent runner assembles a fresh
copy of the production include tree, starts its own stock emulator, waits for
the fixture's MOS result file, and terminates that emulator before returning.
The batch never launches a graphical review and never overlaps two emulators.

Run from a staged project root with an Oryx checkout. The current stock Flexe
artifact locations and required engine environment are owned by the canonical
`agon-dev-env/codex/default-flexe.md`; do not copy those host-specific paths
into this project. Point the runners at that profile through these overrides:

```bash
W3D_ASSEMBLER=/home/smith/.local/bin/ez80asm \
W3D_EMULATOR=<stock Flexe executable> \
W3D_MOS=<stock MOS image> \
W3D_VDP=<stock Flexe VDP adapter> \
W3D_FIRMWARE=platform \
AGON_FLEXE_FIRMWARE=<stock ESP32 firmware image> \
AGON_FLEXE_ENGINE=jit \
python3 src/asm/wolf3d_parity/scripts/run_direct_emulator_regressions.py \
  --result batch-result.json
```

Each constituent runner creates its own default Flexe artifact directory under
its temporary work tree. A caller may instead set `AGON_FLEXE_ARTIFACTS`; the
runner creates that directory before launching Flexe. `W3D_STAGED_ROOT` selects
the immutable source under test, while `W3D_RUNTIME_ROOT` may identify the
working tree that owns large generated/runtime inputs intentionally omitted
from a staged archive.

The JSON receipt records the exact staged-source hash, every command, captured
output, return code, and aggregate result. Oryx scheduling remains governed by
the canonical FIFO instructions in
`agon-dev-env/cross-agent/vdplet-rollout/README.md`.
