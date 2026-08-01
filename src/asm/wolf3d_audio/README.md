# Wolf3D audio service regression

This isolated project directly exercises the production
`../wolf3d/src/wolf3d_audio.inc` service without pulling audio into the main
game fixture. The generated `wolf3d_audio_assets.inc` owns logical AUDIOWL1
IDs, active AdLib priorities, and stable VDP IDs. The service consumes that
table and owns loaded-sample state, per-30 Hz batching, deterministic top-three
arbitration, three-channel round-robin replacement, stale catch-up suppression,
direct playback, buffered playback calls, idempotent procedure installation,
shutdown, and byte-count diagnostics.

The host oracle runs 10,000 deterministic randomized batches in addition to
directed policy and wire-format checks:

```sh
.venv/bin/python -m unittest discover -v \
  -s src/asm/wolf3d_audio/scripts -p 'test_audio_oracle.py'
```

The direct fixture includes the production assembly and captures its exact VDU
byte stream before writing a result mailbox from a real eZ80 run:

```sh
.venv/bin/python \
  src/asm/wolf3d_audio/scripts/run_audio_emulator_regression.py
```

For a staged source tree, set `W3D_STAGED_ROOT`; set `W3D_RUNTIME_ROOT` when
the emulator artifacts live in another Wolf3DOrig checkout. The runner uses a
headless stock VDP because it validates eZ80 state and bytes rather than
audible playback. Bespoke-emulator and hardware listening remain explicit
human acceptance gates after application integration.

The same fixture also measures backend CPU dispatch with the established PRT1
hardware stopwatch (`18.432 MHz / 256 / 72 = 1 kHz`). It times 10,000 loaded
`w3d_audio_request` calls into an active, empty-slot batch and 10,000 one-event
buffered `w3d_audio_flush_quantum` calls. The flush benchmark uses capture mode,
re-arming a twelve-byte memory sink on every iteration, so UART transmission,
VDP command execution, and audio-device latency are excluded.

Each measurement has a second PRT run containing the identical fixture re-arm,
argument loads, helper calls, and loop bookkeeping but omitting the production
entry point. The runner reports raw total and baseline timer ticks, their
backend-only difference, and average microseconds per call. PRT vector changes
and 24-bit elapsed-millisecond snapshots are protected with `DI`/`EI`; all
correctness assertions and mailbox I/O remain outside the measured regions.
