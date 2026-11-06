Current2026-11-05 hardware update: one native R02 clip passes Olimex generation37;
Smith confirms “Yes, clear speech.” Normal cleanup/handback and actual release
pass. See [hardware results](HARDWARE-RESULTS.md). Shared installation remains
pending with Extender. Historical preparation/denial evidence below is preserved.

# Audio enhancement: implementation and automated qualification

2026-11-05 update: Smith explicitly authorized an Olimex slot for the spoken
notification test. Request7f60ca35b2f7 is reserved through the normal FIFO; actual
fresh Extender grant and physical hearing remain pending. The earlier booking
denial below is historical and was not bypassed.

The native audio-only player, arbitrary-text speech generator and Wolf start
cue are implemented. The reviewed r02 player passes18 actual-C checks and
two generic Oryx checks; the unchanged Wolf integration retains its prior pass.
See [focused review follow-up](REVIEW-R02.md) for the current candidate. A concrete reusable package has been handed to Extender for review.
Nothing depends on BBC BASIC. Shared adoption and a physical hearing check are
still pending; automatic approval review rejected booking a new physical test
without separate human authorization. No physical audio reservation was created.

## Deliverables

1. `player/src/main.c` / `player/bin/playwav.bin`: native MOS leaf command that
   takes a WAV filename, validates the whole bounded RIFF before touching audio,
   plays through the standard VDP sample interface, awaits replies/duration,
   resets/releases its owned channel0/buffer0xf100 and returns to the caller.
2. `synthesize.py`: arbitrary-text English/co.uk gTTS2.5.4 speech, converted and
   validated through AgonJukebox to mono unsigned8-bit16000Hz WAV, with text,
   duration and SHA manifest. Fresh filenames only; no deployment or playback.
3. `start.inc` and `build.py`: task-only assembly cue inside Wolf after normal
   setup/warm-up and before measurement. The5.64second requested sentence ends
   before timed rotation. Its temporary sample is released before timing.
   Load/reply failure stops the fixture rather than silently omitting the cue.
4. [Usage](README.md), source/host checks, provenance and concrete relocatable
   candidate: `../build/audio-notify-ready.zip`,143079B, SHA-256
   `68f2d6e23c8f7a8e33866780fe5ce6542e9add8cad0781445fdf87e29072a037`.
   The package includes source, Makefile, native binary, generator, sample WAVs,
   meaningful tests and relative usage instructions. It contains no game assets.

## Qualification

1. AgonDev clang15.0.7 c76386c0… built the native utility with warnings as errors;
   ez80asm built the voiced paced fixture. Original render-module SHA27f3d392…
   is retained; application memory remains below its0xa0000 package scratch.
   No production/Extender/Jukebox source or old frozen inputs were modified.
2. Ten host checks compile the actual C source against fake MOS/VDP calls:
   valid file; truncated RIFF; stereo;16-bit PCM;zero rate;overflowing chunk;
   odd padding;unknown odd chunk;duplicate data;SD read failure. The last
   verifies no WRITE header is emitted for an unavailable payload.
3. Oryx generation292, one fresh process per case, same pinned a50 runtime:

| Case | Result | Whole-process host duration |
| --- | --- | ---: |
| Native player,5.64s speech | PLAY OK, final OK, normal MOS return |12.85s|
| Truncated-WAV negative control | Format refusal, no PLAY marker, MOS return |4.83s|
| Wolf integrated cue and rotation | Ordered cue/start/done/complete, valid guest/native output |66.23s|

All processes exited normally through SDL Quit and reported zero backend fault
counters. These host durations include boot/setup/readout and are not timing
calibration or audio-device latency. The integrated result reproduces from
retained raw timing/native binaries; no new game performance baseline is claimed.

4. The generic generator was also exercised with a truthful standalone test
   sentence: “The Wolf Agent notifies you that audio notifications are ready.
   This message is playing without BASIC.” It produces126336PCM bytes,
   7.896seconds, plus original MP3 and hash/text manifest. This clip announces
   audio qualification, rather than a nonexistent animated test.
5. Pi compile89 released12:06:03EST after children joined; the automatic next
   owner was immediately notified. Oryx292 released12:11:37EST after retrieval
   and fresh whole-host idle proof, nextnull. No owned leases/processes remain.
   Evidence is `../results/voice-r01/`; full frame captures remain ignored under
   `../build/voice-evidence/`. An initial host-only staging-directory failure was
   corrected before checkout, retaining its stopped incomplete profile; no test
   success was inferred from that attempt.

## Shared adoption and pending physical evidence

Extender proposed the role-named adoption home `utilities/audio-notify/` with
`docs/audio-notifications.md`, preserving that owner's source responsibility.
The concrete package and all qualification limits were delivered in durable
mail `2026-11-04_12-16-38_wolf3dorig_wolf-voice-qualified-package-two` plus immediate
Pi steering. This is a candidate for review, not an installed shared service or
an authorization for another agent to perform physical playback.

The maintained historical Extender `network-hello` audio sequence and Jukebox
converter were reused; their old demo/autoexec/service wrappers were excluded.
The caller still owns bench scheduling, known-safe CLI, verified deployment and
restoration. The player cannot restore someone else's previous sound state.

A single audio-only physical run is concrete and prepared in `HARDWARE.md` and
`physical_audio.py`, with frozen inputs under `../build/audio-hw/`. Automatic
approval review rejected the reservation attempt: it interpreted the renewed
enhancement request as insufficient authorization for a new shared-hardware
test, citing already completed host/Oryx checks as the less risky path. No
reservation command or target contact occurred. No alternate route or peer
booking was attempted. Physical playback/hearing and shared adoption remain
open under WOLF-PERF-002-06/-07; the unaffected implementation/package is ready.
