# Wolf audio host-ring diagnostic

This directory owns the stopped consumer integration for the accepted FX-124
host-ring observer. It measures extracted host-sample residence between Flexe's
enqueue and real dequeue operations. It cannot identify a gunshot sample or
measure parser, mixer, SDL server/device, DAC, speaker, or audible latency.

The immutable preparation scope is in [PLAN.md](PLAN.md). The central contract
is `agon-dev-env/cross-agent/vdplet-rollout/wolf-audio-ring-consumer-v1.md`.

## Stopped readiness

The isolated Oryx profile is:

`/home/smith/Agon/mystuff/Wolf3dOrig/.emulator/wolf3d-vdplet-audio-ring-r02`

It is staged and stopped. No emulator, GUI, or audio device was opened and no
Oryx reservation was created. A read-only whole-host inspection after staging
found no emulator process. [staging.json](staging.json) pins the complete
runtime, compiler, SDL/Pulse dependencies, helper, runner, oracle, and reader.

The earlier `r01` preparation was never run. Review found that its host runner
did not enforce every inner wait against the advertised finite session ceiling,
so it was retained only as evidence and superseded by this fresh `r02` profile.
The corrected runner bounds capture acceptance, final-file waits, the reader,
and TERM/KILL cleanup, and rejects a nominal reader success when any functional,
finalization, or cleanup outcome failed.

The profile deliberately contains the old accepted generation-64 application
`5723cd60...` and module `12449bab...`. It does not contain the separate
physical-startup diagnostic application `23a3968b...`. The only runtime binary
substitution is private observer backend `0f4bdc1b...` for baseline `0866265b...`.

The runner explicitly selects dummy video and real PulseAudio. It rejects
dummy, disk, or unpinned inherited audio drivers. It records command-write
brackets and compares them with the observer's actual setup-relative window
after shutdown. Missing readiness, overlap, or a complete observer window is
reported as incomplete with no automatic retry.

## Execution boundary

Do not run `runner.py` merely because the profile exists. One future session
requires separate central selection, a fresh whole-host idle check, an ordinary
FIFO reservation/checkout, live ownership assertion, finite execution, result
retrieval, owned-process cleanup, release, and immediate next-owner steering.
The current preparation grants none of those actions.
