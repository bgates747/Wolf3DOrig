# Wolf3D audio précis and Agon implementation constraints

Status: design reference, 2026-07-31. This document records the original
Wolf3D audio behavior and the Author's initial port decisions. It does not yet
authorize or describe a completed sound implementation.

## 1. Authority and reuse boundaries

The original game remains authoritative for logical sound IDs, call sites,
priority, interruption, positioning, and music selection:

- `orig/src/WOLFSRC/ID_SD.C` and `ID_SD_A.ASM`: device backends, priority,
  timers, digitized playback, positioning state, and AdLib music sequencing;
- `orig/src/WOLFSRC/ID_SD.H`: sound structures and the 70 Hz timing base;
- `orig/src/WOLFSRC/WL_MAIN.C`: logical-to-digitized `wolfdigimap`;
- `orig/src/WOLFSRC/WL_GAME.C`: listener-relative positioning and attenuation
  tables;
- `orig/src/WOLFSRC/WL_ACT1.C`, `WL_ACT2.C`, `WL_STATE.C`, `WL_AGENT.C`, and
  `WL_PLAY.C`: gameplay call sites and music selection; and
- `orig/src/WOLFSRC/AUDIOWL1.H`: shareware sound/music IDs and archive ranges.

Two existing Agon projects provide implementation mechanics rather than new
gameplay policy:

1. `~/Agon/mystuff/agon-utils/examples/agnb` owns the canonical AGNB 0.2 audio
   container and synchronous streaming loader conventions.
2. `~/Agon/mystuff/AgonWolf3D` contains known-working Agon sample creation,
   playback commands, container generation/validation, and loading UI idioms.

The older AgonWolf3D round-robin playback policy is not automatically adopted.
It is a working transport example to be reconciled with original behavior.

## 2. Original sound-effect representations

Wolf3D has three distinct sound-effect paths.

### 2.1 Digitized effects

The high-fidelity effects and voices are raw, headerless, unsigned 8-bit mono
PCM stored after `soundstart` in `VSWAP.WL1`. The final VSWAP page contains the
start-page and byte-length directory used to reconstruct effects which span
multiple 4096-byte pages.

The Sound Blaster backend programs a nominal 7000 Hz DAC rate:

```c
timevalue = 256 - (1000000 / 7000);
```

Because the DSP time constant is integral, the effective rate is approximately
7042.25 Hz. The original payload nevertheless contains only roughly 7 kHz of
information.

Author decision: do not upsample original audio. It cannot restore fidelity and
would consume extra VDP memory, SD transfer time, startup time, and UART
bandwidth. Preserve the original unsigned PCM bytes and create Agon samples at
7000 Hz unless direct audible comparison establishes that using the effective
7042 Hz clock is materially more faithful. Both values fit AGNB's u16 rate.

The existing canonical 22-record `sfx.agnb` is proven at 16,384 Hz, but it is
an older Agon-oriented effect collection and is not automatically the new
asset authority. The Wolf3DOrig pipeline should extract or otherwise validate
native-rate effects against the original shareware data and logical DigiMap.

### 2.2 PC-speaker effects

Each PC-speaker sound in `AUDIOT.WL1` contains `SoundCommon` (`u32 length`,
`u16 priority`) followed by pitch-control bytes. It is not PCM. Approximately
every 1/140 second, the service routine consumes a byte: zero silences the
speaker; a nonzero value selects a timer divisor through `pcSoundLookup`, whose
entries are `index * 60`.

### 2.3 AdLib synthesized effects

Each AdLib effect contains `SoundCommon`, a two-operator OPL2 instrument, a
block/octave value, and a byte stream which updates the effect voice's
frequency. It is synthesized and serviced at approximately 140 Hz, not PCM.

For the first Agon phase, native digitized replacements are preferred wherever
the original shareware DigiMap supplies them. Synthesizing PC-speaker or AdLib
fallback effects can be evaluated only for logical sounds without suitable PCM.

## 3. Original priority and concurrency policy

Every logical sound carries a priority in its `SoundCommon` header.

1. A requested sound whose priority is lower than the active sound is rejected.
2. Equal or higher priority interrupts and replaces the active sound.
3. Digitized and synthesized effects have separate current-sound and priority
   state when the selected hardware supports both paths independently.
4. The original digitized path is essentially one effect stream, not an
   unrestricted multi-channel round robin.
5. Background music uses separate OPL voices and continues under effects.
6. A few call sites explicitly query or wait for sound completion; these must
   be inventoried rather than treating every effect as fire-and-forget.

The first port should reproduce the one-stream digitized priority semantics.
Additional simultaneous environmental voices are a deliberate extension, not
an assumed modernization, and require an explicit audible/gameplay decision.

## 4. Positional sound

Doors, actor voices, enemy weapons, dog attacks, and other world-originated
effects call `PlaySoundLocGlobal`. Player weapons, pickups, UI sounds, and
player-local damage are generally unpositioned.

The original implementation:

1. subtracts the current view position from the sound origin;
2. rotates the delta by the view sine/cosine into listener space;
3. reduces it to tile-scale coordinates and clamps it to `ATABLEMAX=15`;
4. looks up left and right attenuation in fixed 15-by-30 tables;
5. submits attenuation values from 0 (loudest) to 15 (quietest), rejecting
   `(15,15)`; and
6. retains the world origin of the accepted positioned sound and recomputes its
   attenuation every gameplay frame while it remains active.

Wolf3DOrig should preserve the original transform and lookup tables. The Agon
backend may translate them to one-channel distance volume initially. True
left/right presentation, if supported and worthwhile, may use two synchronized
channels or another proven VDP mechanism without changing the gameplay-space
calculation.

## 5. Music is a separate phase

Wolf3D music is IMF-like register sequencing, not PCM and not MIDI. Each
`AUDIOT.WL1` music chunk is a `MusicGroup` containing a u16 byte length followed by
four-byte events:

```text
u8 OPL2 register
u8 register value
u16 delay in 700 Hz ticks
```

The sequencer performs exact OPL2 register writes, advances its clock at
700 Hz, and loops at the end. It therefore resembles MIDI in being a timed
musical event stream, but it is lower level: MIDI expresses notes, programs,
controllers, and channels; IMF expresses the already-rendered OPL2 register
programming.

The Author has a heavily modified MIDI playback system for Agon. A later music
phase must inspect that event format, timing resolution, looping, instruments,
and channel budget before choosing between IMF interpretation, offline
IMF-to-MIDI-like conversion, or independently validated higher-level music
sources. Music is explicitly outside the initial sound-effect implementation.

## 6. Initial implementation scope

The first phase focuses on sounds which materially inform current gameplay:

1. environment: door open/close, locked/no-way feedback, and pushwall where
   supported;
2. combat: knife, pistol, machine gun, gatling gun, enemy shots, dog attack,
   actor alert/pain/death voices, player damage, and player death; and
3. pickups: ammo, weapons, health, treasure, keys, and extra life.

Menus, intermission narration, bosses, projectiles not yet implemented, and
music remain later phases. Original call sites and priorities should be ported
only as their owning gameplay behavior exists.

## 7. AGNB loading contract

AGNB 0.2 audio records are RIFF `LIST BUFR` records containing:

```text
BHDR  u16 exact VDP buffer ID
AUDI  u8 format=0x09, u16 explicit sample rate
DATA  nonempty unsigned 8-bit mono PCM
```

The canonical loader validates all metadata and enclosing bounds before reading
PCM, streams through its image-owned 8 KiB transfer window, consolidates the
buffer, and creates the VDP sample. It is synchronous and non-reentrant.
`agnb_load_audio_with_callback` provides a per-finalized-sample loading hook.
Playback, channel ownership, priority, and sound IDs remain application policy.

Wolf3DOrig already vendors the canonical image API dependencies. Audio support
should be incorporated without duplicating labels, adding another transfer
window, or regressing the known ADL-width fixes. In particular, every u16
buffer ID and sample rate loaded through a 24-bit register must keep its upper
byte controlled; the proven `dec reg` / `inc.s reg` idiom may be retained.

## 8. Buffered playback optimization

The VDP Buffered Commands API can reduce per-effect UART traffic and eZ80 work.
A normal sample start sends at least:

1. a set-waveform command containing channel and sample buffer ID; and
2. a play-note command containing channel, volume, frequency, and duration.

Those commands can be uploaded once into VDP command buffers. Runtime playback
then invokes a command buffer with:

```text
VDU 23,0,0xA0, commandBufferId; 1
```

This is six wire bytes and causes the VDP to execute the stored multi-command
sequence locally. The approach uses the ordinary Buffered Commands API and
does not require a Wolf-specific firmware opcode.

The design must keep sample-data buffers distinct from callable command
buffers. With original one-stream semantics, one fixed effects channel permits
one small command buffer per sample. If multiple channels are later approved,
the build can emit a small sound-by-channel command-buffer matrix or use
carefully validated offset calls.

Dynamic attenuation requires separate treatment because volume changes while a
positioned sound plays. Candidate designs, to measure rather than assume, are:

1. send one short ordinary set-volume command and one six-byte buffered call;
2. patch a writable command template with buffered adjust operations, then call
   it; or
3. select among a modest prebuilt set of quantized-volume command buffers.

Option 1 is the simplest baseline and still removes repeated waveform/sample,
frequency, and duration fields from the hot path. The implementation should
measure bytes emitted and eZ80 time for direct versus buffered playback before
choosing a more elaborate template scheme.

## 9. Required validation

1. Independently validate every generated AGNB record against the authoritative
   logical catalog, native PCM bytes, buffer ID, sample rate, and duration.
2. Unit-test original priority acceptance/rejection and completion clearing
   without requiring audible output.
3. Test logical-event generation independently from VDP command emission.
4. Verify buffered command streams byte-for-byte and confirm they neither alias
   sample buffers nor conflict with existing image/HUD/Wolf/Pingo IDs.
5. Exercise environment, combat, pickup, death, and Escape shutdown in the
   bespoke emulator, followed by explicit Author audible acceptance.
6. Repeat on physical hardware; emulator audio success is not hardware audio
   acceptance.
7. Record VDP memory, container size, startup time, UART bytes per event, and
   eZ80 timing before expanding concurrency or asset quality.
