# Audio-only Agon notifications

A native MOS utility plays a short speech WAV and returns to its caller. It
uses ordinary MOS/VDP sample commands and the established Jukebox PCM format.
There is no BBC BASIC dependency, demo screen, mode change, keyboard capture,
startup edit, listener launch or reset. Wolf's separate assembly integration
plays its cue after warm-up and before the timed rotation.

## Generate speech on the host

Use a project virtual environment with `requirements.txt` installed, and a fresh
output filename. The generator uses the existing AgonJukebox converter and its
virtual environment; provide `--jukebox` or set `AGON_JUKEBOX_ROOT`. gTTS uses an
online speech service, English/co.uk; no gender selection is asserted.

```sh
.venv/bin/python /Agon/mystuff/Wolf3dOrig/agonport/doc/tasks/WOLF-PERF-002/voice/synthesize.py \
  --text 'The Example Agent notifies you that your review is ready.' \
  --output /absolute/task/output/example-review.wav \
  --jukebox /path/to/AgonJukebox
```

Outputs are the validated unsigned8-bit mono16000Hz WAV, original MP3 and a
text/duration/hash manifest. Existing outputs are refused. Maximum speech length
is15seconds; choose a shorter sentence if generation exceeds it. Synthesis does
not contact the bench or invoke anything there.

## Build and invoke the native player

```sh
make -j1 -C /Agon/mystuff/Wolf3dOrig/agonport/doc/tasks/WOLF-PERF-002/voice/player \
  AGONDEV_TOOLCHAIN=/Agon/agondev/release
```

This creates `voice/player/bin/playwav.bin`. Use the normal compile reservation
when required on your host. Deployment/invocation requires actual current bench
custody and the maintained Extender transport procedure. The following is MOS
syntax after the caller deploys to its own approved task directory:

```text
LOAD /test/your-task/playwav.bin
RUN . /test/your-task/example-review.wav
```

The player requires exclusive caller ownership of audio channel0 and buffer
0xf100; it resets channel0 and clears that buffer. Invoke only from a known-safe
MOS CLI, not over a running game. It does not reconstruct a previous sound's
channel state. It returns a process result and text receipt; it does not write
shared receipt files, change cwd, start a service or restore an unrelated caller.

The bounded parser accepts RIFF/WAVE PCM format1, mono,8-bit, sample rate1..65535Hz,
maximum15seconds/300000RIFF bytes. `fmt` must precede a single `data` chunk.
Unknown chunks and odd padding are handled. The entire declared RIFF validates
before any audio write; a short subsequent SD read stops before declaring a
WRITE payload it cannot supply. This is a bounded notification player, not
Jukebox's general media UI or WAV decoder.

| Result | Meaning |
| --- | --- |
|0|Playback commands acknowledged, duration elapsed and cleanup fenced|
|2|Wrong arguments|
|3|File unavailable or unsupported/malformed WAV; audio untouched|
|4|Audio-command reply timeout/refusal|
|5|Seek/read failure while preparing playback|
|6|Cleanup failed after otherwise successful playback|

`PLAYWAV CLEANUP UNCONFIRMED` reports a reset/fence failure separately. A prior
error remains the primary result; otherwise cleanup failure returns6.

`PLAYWAV PLAY OK` means the play command was acknowledged; final `PLAYWAV OK`
means cleanup also succeeded. Neither proves that a person heard the speaker.
Normal scheduling, startup/listener preservation and safe serial rules remain
with the caller. No automatic retry, hardware discovery or bench takeover is
embedded in this leaf utility.

## Qualification and ownership

The revised C code passes18 host parser/transport/failure checks. It plays
multiblock samples directly, avoiding a redundant full-sample consolidation.
Oryx generation293 passes valid/rejected-WAV checks for the revised binary;
Wolf's unchanged integrated cue retains its generation292 pass. Generation292
originally passed valid speech playback, malformed-file refusal with no play marker, and
Wolf's integrated speech-before-rotation sequence; all return normally with
zero reported backend faults. The exact generated Wolf clip is5.64seconds.
No firmware or production-game source was modified. Physical hearing remains
a separate qualification step; emulator command receipts cannot establish it.

The generic implementation is prepared for Extender ownership at the proposed
`utilities/audio-notify/` and `docs/audio-notifications.md`, after reviewed
adoption. It is currently task-owned here, not installed as a shared service.
The historical donor is Extender's `examples/network-hello/src/main.c` audio
portion. Its demo/autoexec/service wrappers must not be revived. AgonJukebox's
maintained converter supplies the WAV contract; Wolf's AGNB writer/loader is
used only by the integrated assembly cue, not by the generic CLI player.
