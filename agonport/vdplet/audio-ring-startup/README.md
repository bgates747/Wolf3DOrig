# Wolf startup host-ring diagnostic

This directory owns a stopped-only consumer preparation for the corrected
FX-129 ring observer. It asks whether the host-ring backlog is present or forms
during observer SETUP through SETUP plus ten seconds. It does not identify a
shot sample or measure parser, mixer, PulseAudio/device, DAC, speaker, or total
audible latency.

The immutable scope is in [PLAN.md](PLAN.md). The central contract is
`agon-dev-env/cross-agent/vdplet-rollout/wolf-ring-startup-preparation-v1.md`.
The generation-71 result and its [initialization limitation](../audio-ring/results/generation-71-r02/LIMITATION.md)
remain unchanged.

## Stopped readiness

The isolated Oryx profile is:

`/home/smith/Agon/mystuff/Wolf3dOrig/.emulator/wolf3d-vdplet-audio-ring-startup-r01`

It is staged and stopped. No emulator, GUI, audio device, FIFO reservation, or
capture occurred. A post-stage whole-host inspection found no emulator process.
[staging.json](staging.json) pins the complete runtime and dependencies;
[stopped-inspection.json](stopped-inspection.json) records the empty host.

The profile preserves application `5723cd60...`, module `12449bab...`, frontend
`7e7d0e1b...`, firmware `8d980025...`, its matching ELF, MOS `d5642432...`,
media, helper `215bd248...`/`7d9f52a...`, reader `584e9d2a...`, and accepted
finite supervision base `f0ffe798...`. The corrected observer is `943f432f...`.
Its output directory is fresh, the window offset is zero, and a later eligible
session must prove first-row `produced_before=0` and `before=0` while retaining
the real 92-second shot bracket as expected non-overlap.

## Execution boundary

The profile prepared by these files must remain stopped. Do not invoke its
runner merely because it exists. A later run requires a separate central
selection, exact pin and output revalidation, fresh whole-host idle evidence,
ordinary FIFO checkout, live ownership assertion, finite execution, retrieval,
owned cleanup, release, and immediate next-owner steering.
