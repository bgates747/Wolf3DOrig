# Wolf3D durable-config regression

This target directly exercises production `wolf3d_config.inc` on an eZ80
emulator. It covers missing-file defaults, all four SFX/music flag
combinations, checksum/footer/reserved-bit rejection, a production MOS-file
round trip, and rejection of both trailing and truncated data.

Run from the repository root:

```sh
python3 src/asm/wolf3d_config/scripts/run_config_emulator_regression.py
```

Use `--prebuilt PATH` on an emulator host which does not carry an eZ80
assembler.

Build that transferable target without launching an emulator with
`--assemble-only PATH`.
