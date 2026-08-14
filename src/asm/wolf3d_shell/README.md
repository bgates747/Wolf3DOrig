# Wolf3D shell regression

This focused regression executes the production `wolf3d_shell.inc` directly on
the eZ80 emulator with a deterministic keyboard-reader hook. It checks shell
key normalization and result flags, main/episode/difficulty navigation,
locked-episode refusal, difficulty Escape backtracking, title and victory
entry points, and the exact bitmap IDs and plot coordinates for every selected
row, cursor, and difficulty portrait.

Run from the repository root:

```sh
.venv/bin/python src/asm/wolf3d_shell/scripts/run_shell_emulator_regression.py
```

The runner copies the production assembly source into an isolated temporary
directory, where it names the fixture `s.asm` to stay within `ez80asm`'s legacy
path-length limits. It is safe to run alongside a production assembly.
