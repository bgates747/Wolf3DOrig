# Frozen plan: startup host-ring stopped preparation

This task prepares one isolated, stopped Wolf diagnostic profile. It does not
launch an emulator, open an audio device, join the Oryx FIFO, or authorize a
capture. Any later run requires a separate central selection.

## Frozen cohort and only changes

- Preserve application `5723cd60...`, module `12449bab...`, frontend
  `7e7d0e1b...`, firmware `8d980025...`, firmware ELF `1a7c4448...`, MOS
  `d5642432...`, all media, helper source `215bd248...`, helper binary
  `7d9f52a...`, reader `584e9d2a...`, and oracle `ea4f7e64...`.
- Preserve the accepted finite supervision, ordinary loader/four-Enter input,
  structural gameplay readiness by 85 seconds, real PulseAudio with dummy video,
  Space at 92 seconds, Escape at 103 seconds, farewell/MOS by 150 seconds,
  15-second normal process exit, and 180-second whole-session ceiling including
  reserved owned-process cleanup.
- Replace only the old observer backend with corrected private candidate
  `943f432fecb96689f3a0d2ae80c72d08e20903dfe2a58a00ba88d8c7727ad400`,
  which initializes under the existing audio lock and publishes `armed` last.
- Use a fresh profile and output path with `FLEXE_RING_WINDOW_AFTER_MS=0`.

## Startup measurement contract

The observer window is actual observer SETUP through SETUP plus ten seconds,
not process `Popen` time. A valid startup measurement requires complete reader
output and an initial-history witness from the first saved row:
`produced_before == 0` and `before == 0`. Missing or different initial state is
terminal incomplete evidence; the runner must not invent earlier samples.

The real Space write at runner `T0+92s` is expected not to overlap the startup
window. Its actual bracket is retained with overlap `false`; this is eligible
for a passing STARTUP measurement and must not trigger a retry or fabricated
overlap. Startup-window validity remains separate from event, parser, mixer,
device, DAC, speaker, and total audible latency.

All original identity, structural gameplay, finalization, normal-cleanup, and
finite-supervision gates remain mandatory. Cap hits, incomplete reader/window,
unknown initial history, source/runtime drift, or forced cleanup are terminal.
The earlier generation-71 evidence and its disclosed initialization limitation
remain immutable.

## Preparation and evidence

Device-free tests will cover valid startup eligibility with expected shot
non-overlap; missing/wrong initial history; incomplete reader/window; unchanged
functional and cleanup failures; real-audio enforcement; finite waits; and the
no-launch/no-reservation staging boundary. Staging will pin the complete runtime,
source, helper, reader, oracle, runner, wrapper, compiler, SDL/Pulse dependencies,
fresh output absence, and current Oryx context while leaving the profile stopped.
