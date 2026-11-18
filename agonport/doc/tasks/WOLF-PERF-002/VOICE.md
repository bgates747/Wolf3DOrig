# Wolf animated-fixture spoken start cue

Current status: implementation and automated qualification pass; see
[voice results](voice/RESULTS.md). Reusable candidate delivered to Extender;
physical hearing and shared adoption remain pending.

Use the established Extender/Jukebox-derived unsigned PCM audio path to speak:
“The Wolf Agent notifies you that an animated test fixture is starting now.”
No BBC BASIC program, legacy demo screen, startup replacement or notification
emulator is involved. The cue belongs inside the native test application after
assets, mode selection and warm-up, immediately before the rotation interval.
An external alert followed by lengthy application startup would be misleading.

The Author selected this on 2026-11-04 and explicitly excluded BBC BASIC.
Task-local code and generated speech stay under WOLF-PERF-002. No previous
frozen input is edited. Preload the clip outside timing using Wolf's existing
AGNB audio loader; use ordinary VDP sample select/play/reset commands, await
successful replies and the bounded sample duration, release the sample, then
start the twenty-second paced rotation. Failed load/playback must stop the
fixture; it must not silently proceed without its start cue.

Voice provenance: agon-extender/examples/network-hello/src/main.c supplies the
finite audio-command sequence and acknowledgment contract; its old demo and
startup/service wrappers are excluded. AgonJukebox/scripts/make_wav.py supplies
the maintained16kHz mono unsigned8-bit conversion and validation. Synthesis
uses the same gTTS2.5.4 English/co.uk selection. No gender choice is claimed.
The normal Wolf AGNB container writer packages the validated PCM at dedicated
buffer0xf100; playback is on channel0 and completes before timed rendering.

Preparation checkpoint: exact sentence synthesized as5.64seconds at16000Hz,
validated by Jukebox and packaged to AGNB. Audio-only assembly and build source
are retained. The Author selected an immediate unchanged hardware run instead;
unstarted Pi compile5f7addde99c9 was cancelled. No voice-enabled binary, emulator
qualification, hardware playback or human-hearing acceptance is claimed.

## Renewed preparation and reusable player

The Author explicitly resumed work and requested a reusable non-BASIC utility.
Compile `voice/player/src/main.c` as `playwav.bin` in addition to the integrated
Wolf application. The leaf command accepts one WAV path, validates the complete
bounded RIFF before touching audio, plays unsigned8-bit monoPCM through stock
VDP APIs, acknowledges commands, waits the sample duration and resets/releases
its resources. It does not change video mode, clear the screen, read keyboard,
start an SD service, change startup or reset hardware. Caller must own channel0
and buffer0xf100 and be at a safe MOS CLI. Human hearing remains a separate gate.

## Focused r02 review follow-up

Extender's source review requested explicit reply-timeout/refusal/wrong-channel
and cleanup-failure evidence. Add eight actual-player fake-MOS cases, preserve
primary errors while separately printing unconfirmed cleanup, remove unnecessary
sample-buffer consolidation (official buffered sound API supports multiblock
samples), and use explicit/environment tool roots for reusable tools. Preserve
r01 source/binary/package evidence. Compile one revised C player plus18 host
checks in one serial Pi tranche, then at most two300s Oryx processes for valid
and malformed-file cases. Wolf's assembly integration is unchanged, so do not
repeat that already-passing case. No physical reservation/playback is authorized
by this follow-up; the explicit review denial remains in force.

For all Olimex bench procedures, use the sole authoritative [bench guide](/Agon/mystuff/agon-extender/docs/operations/olimex-bench/README.md).
