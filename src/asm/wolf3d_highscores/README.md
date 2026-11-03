# Wolf3D high-score regression

This project exercises the production high-score implementation in
`../wolf3d/src/wolf3d_highscores.inc` directly on a real eZ80/MOS execution
path. It covers the original seven-row ordering and tie break, overlap-safe
insertion, name bounds and editing, unsigned 32-bit decimal formatting, and
the versioned/checksummed `scores.w3h` persistence image including real MOS
file round trips and corruption recovery.

Run it only through the shared Oryx reservation process documented in
`agon-dev-env/cross-agent/vdplet-rollout/README.md`:

```bash
python scripts/run_highscores_emulator_regression.py
```

The runner creates an isolated temporary SD card and removes it after the
finite test. A successful mailbox begins with `W3H1` and reports zero errors.
