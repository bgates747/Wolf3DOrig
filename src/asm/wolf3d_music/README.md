# Wolf3D music direct regression

This project executes the production IMF-derived sequencer on the real eZ80
emulator. It checks the canonical track table, OPL frequency/volume/waveform
translation, exact emitted VDP bytes, 120 Hz scheduling, looping, mute/resume,
all ten Episode 1 floor assignments, and channel shutdown independently of the
full game. The fixture intentionally leaves upper eZ80 register bytes dirty so
ADL-unsafe table indices or two-byte command writes fail visibly.

Run with:

```bash
.venv/bin/python src/asm/wolf3d_music/scripts/run_music_emulator_regression.py
```

The generated `wolf3d_music_assets.inc` remains owned by
`agonport/tools/wolf3d_assets/scripts/build_music_assets.py`.
