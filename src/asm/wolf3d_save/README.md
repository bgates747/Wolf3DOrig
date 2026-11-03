# Wolf3D save-image regression

This project exercises the production transactional save-image core in
`../wolf3d/src/wolf3d_save.inc` directly on a real eZ80/MOS execution path.
It covers a complete authoritative-world round trip, derived-state rebuild,
header and checksum rejection, and semantic rejection for scalar, area, actor,
door, static, and pushwall corruption. Every rejected image must leave live
state unchanged.

Run it only through the shared Oryx reservation process documented in
`agon-dev-env/cross-agent/vdplet-rollout/README.md`:

```bash
python scripts/run_save_emulator_regression.py
```

The runner creates an isolated temporary SD card and removes it after the
finite test. A successful mailbox begins with `W3S1` and reports zero errors.
