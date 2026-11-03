# Wolf3D shell regression

This focused regression executes the production `wolf3d_shell.inc` directly on
the eZ80 emulator with a deterministic keyboard-reader hook. It checks shell
key normalization and result flags, main/episode/difficulty navigation,
locked-episode refusal, title and victory entry points, and the exact bitmap
IDs and plot coordinates for every selected row, cursor, and difficulty
portrait. It also drives Escape through the title, main menu, episode menu,
locked-episode notice, difficulty menu, victory acknowledgment, and both public
wait helpers. Every one must set the application-global exit latch and return
`W3D_SHELL_RESULT_QUIT`; ordinary acknowledgments and navigation must not set
the latch.
Escape also has priority when another recognized menu key is held in the same
keyboard sample, so a combined press cannot be consumed as ordinary input.
The release gate itself observes Escape as well: entering a title, notice, or
acknowledgment while Escape is already held latches exit and returns as soon as
that key is released. Other held keys are still discarded and cannot serve as
the new screen's acknowledgment.

The fixture also owns a deterministic AGNB seam for the canonical 41-page
Read This article. It checks all original navigation families, first-page
underflow, local Escape, CORNER/WONDERIN music restoration, parser-failure
fallback, callback-time load abort, and exact clearing of buffers
`$4600..$4628`. The AGNB parser and offline article renderer retain their own
format/asset regressions; this target proves their shell lifecycle contract.

The production shell owns the latch and exposes three helpers:

- `w3d_shell_reset_exit_request` starts a fresh application lifecycle.
- `w3d_shell_request_exit` latches an exit request (A=1/NZ).
- `w3d_shell_query_exit_request` returns A=0/Z or A=1/NZ.

`w3d_shell_run` performs the initial reset. Nested screens never clear the
latch, so gameplay and asynchronous loading code can request or query the same
application-wide exit path.

Run from the repository root:

```sh
.venv/bin/python src/asm/wolf3d_shell/scripts/run_shell_emulator_regression.py
```

The runner copies the production assembly source into an isolated temporary
directory, where it names the fixture `s.asm` to stay within `ez80asm`'s legacy
path-length limits. It is safe to run alongside a production assembly.
