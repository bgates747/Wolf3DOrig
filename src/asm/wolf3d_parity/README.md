# Wolf3D original-parity target batch

This directory owns the finite headless batch used to qualify parity work that
spans several direct eZ80 fixtures. Each constituent runner assembles a fresh
copy of the production include tree, starts its own stock emulator, waits for
the fixture's MOS result file, and terminates that emulator before returning.
The batch never launches a graphical review and never overlaps two emulators.

Run from a staged project root with an Oryx checkout:

```bash
W3D_ASSEMBLER=/home/smith/.local/bin/ez80asm \
python3 src/asm/wolf3d_parity/scripts/run_direct_emulator_regressions.py \
  --result batch-result.json
```

The JSON receipt records the exact staged-source hash, every command, captured
output, return code, and aggregate result. Oryx scheduling remains governed by
the canonical FIFO instructions in
`agon-dev-env/cross-agent/vdplet-rollout/README.md`.

