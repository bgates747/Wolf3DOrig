# Generation 78 corrected late-window terminal result

The selected single invocation ended before measurement. The exact accepted
original runner checks `PROFILE/ring-output` before spawning the canonical
emulator. The staged profile instead created the separately named
`PROFILE/ring-output-late-corrected` directory and configured the wrapper to use
it. Consequently `Path.iterdir()` raised `FileNotFoundError` for the absent
`ring-output` path and the runner returned 1.

No emulator process was spawned, no audio device was opened, no observer output
was created, and no host-ring data was measured. This is a staging-path
integration failure, not an incomplete audio window and not evidence about
latency, depth, fill, drops, the corrected backend, or playback behavior.

The no-retry rule was honored. A fresh whole-host inspection found no emulator
process, and Oryx generation 78 was released with no next request. The frozen
staged receipt remains preserved for diagnosis; correcting the runner/output
path integration and selecting any successor require separate authority.
