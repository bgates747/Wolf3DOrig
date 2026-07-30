# Wolf3DOrig

A modding effort built around the original 1992 Wolfenstein 3D shareware
release. The near-term goal is running and hacking on the actual shareware
`WOLF3D.EXE` under DOSBox — starting with modernized controls (WASD +
mouselook) and working toward a machine-readable (JSON) extraction of its
maps, textures, and audio.

The longer-term goal is a faithful port of Wolfenstein 3D to the
**Agon Light** retrocomputer (ESP32-based VDP + eZ80 assembly application).

See [doc/HANDOFF.md](doc/HANDOFF.md) for full project state and history.

## Layout

- `doc/` — project handoff doc, devlog, research notebook.
- `src/assets/maps/orig/` — reference overview map images (one per floor).
- `src/toolchain/` — Python encoders/decoders for the original WL1 file
  formats (maps, VSWAP, audio) and CLI entry points.
- `src/content/` — authored source assets (maps, textures, sprites, audio)
  for new original content.
- `build/` — compiled WL1-compatible output for testing under DOSBox.
- `dosbox/` — DOSBox config for launching the shareware `WOLF3D.EXE`.
- `orig/` — local copies of the shareware game data and id Software's
  original source release, kept out of git (see `.gitignore`); not this
  project's own code, and not distributed from here.
