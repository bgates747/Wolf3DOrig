# Wolf3D audio précis and Agon implementation contract

Status: approved design reference, 2026-07-31. This document records the
original Wolf3D audio architecture and the decisions governing the initial
Wolf3DOrig sound-effects implementation. Music remains a separate phase.

## 1. Sources of authority

The original shareware game is authoritative for logical sound IDs, gameplay
call sites, priorities, positional origins, and music selection:

- `orig/src/WOLFSRC/ID_SD.C`, `ID_SD_A.ASM`, and `ID_SD.H`: sound structures,
  backends, timers, priorities, digitized playback, and music sequencing;
- `orig/src/WOLFSRC/WL_MAIN.C`: logical-to-digitized `DigiMap`;
- `orig/src/WOLFSRC/WL_GAME.C`: listener-relative positioning and attenuation;
- `orig/src/WOLFSRC/WL_ACT1.C`, `WL_ACT2.C`, `WL_STATE.C`, `WL_AGENT.C`, and
  `WL_PLAY.C`: gameplay call sites; and
- `orig/src/WOLFSRC/AUDIOWL1.H`: shareware sound and music IDs.

Existing Agon projects provide proven implementation mechanics:

1. `~/Agon/mystuff/agon-utils/examples/agnb` defines the canonical AGNB 0.2
   audio container and loader API.
2. `~/Agon/mystuff/AgonWolf3D` contains known-working sample playback idioms.
3. Jukebox under `~/Agon/mystuff/AgonVideo` contains client-side breadcrumbs
   for the Author's custom VDP gain/mixing calls. The corresponding firmware
   implementation lives in an Author VDP fork, possibly alongside Pingo, and
   should be traced only if ordinary playback proves inadequate.

Wolf3DOrig retains its existing breadcrumb-style loading presentation. Loader
UI conventions from the other applications are not imported.

## 2. Original audio representations and port assets

### 2.1 Digitized effects

Digitized effects in `VSWAP.WL1` are raw, headerless, unsigned 8-bit mono PCM.
The final VSWAP page supplies their start-page and byte-length directory. The
Sound Blaster backend requests a nominal 7000 Hz rate; integer DSP timing makes
the physical result approximately 7042.25 Hz.

Wolf3DOrig preserves the original PCM bytes and declares them at 7000 Hz. It
does not upsample: upsampling cannot restore fidelity and would waste VDP SRAM,
container space, loading time, and bandwidth. The original VSWAP/DigiMap data
is authoritative wherever it supplies a digitized effect.

The existing 22-effect `sfx.agnb` collection is a proven transport test set,
not the primary asset source. Its samples may fill required gaps—especially
pickup effects which were synthesized in the original—at their existing sample
rates and without resampling merely for uniformity. Any glaring uncovered gap
must be reported before inventing or synthesizing a replacement.

The collection's Wilhelm scream is reserved for a future easter egg. It does
not replace an original death sound in the initial implementation.

### 2.2 PC-speaker and AdLib effects

PC-speaker effects in `AUDIOT.WL1` contain a priority and length followed by a
pitch-control byte stream serviced at roughly 140 Hz. AdLib effects contain an
OPL2 instrument, block/octave value, and frequency byte stream at roughly the
same service rate. Neither representation is PCM.

The initial Agon implementation uses native digitized effects where available
and suitable existing PCM fallbacks for required gaps. Runtime emulation of
PC-speaker or OPL2 sound effects is outside this phase.

## 3. Runtime event and concurrency contract

Sound is subordinate to simulation. Gameplay produces logical sound requests;
the audio backend translates the accepted requests to VDP playback commands.
It never waits for playback and keeps no completion state in the first pass.
Samples run to completion unless superseded naturally by reuse of their VDP
channel.

The original sound priority values remain useful for arbitration, but its
hardware-limited single-effect behavior is not reproduced rigidly. VDP can
play multiple streams, and ordinary environment, combat, and pickup sounds may
overlap when gameplay calls for them.

Requests are arbitrated as one batch per 30 Hz simulation quantum. Conflicts
within that batch use original priority and deterministic event ordering. If
render delay causes several simulation quanta to be processed before output,
only the newest quantum's accepted requests are emitted. Sounds from earlier
catch-up quanta are discarded rather than played late. This prevents stale
audio bursts and keeps sound synchronized with the current world state.

The initial channel allocation is a small fixed pool of three ordinary VDP
audio channels. Exact assignment—dedicated roles or general-purpose
allocation—is chosen after the authoritative effect catalog and concurrency
sites are inventoried. The allocation must be deterministic, must not interfere
with later music channels, and must permit expansion without changing gameplay
event call sites.

The backend is fire-and-forget. No original completion queries or waits are
ported unless a future gameplay feature demonstrably depends on them. Long
samples receive no special lifecycle management in this phase.

## 4. Mono positioning and attenuation

Agon output is monaural. Wolf3DOrig therefore implements distance attenuation,
not stereo panning.

World-originated sounds retain their source coordinates. The backend uses the
original listener-space transform, tile-scale distance reduction, clamping,
and attenuation tables as the fidelity reference, then collapses the result to
a single mono gain. Player weapons, pickups, UI feedback, and player-local
damage remain unpositioned at their intended gain.

The first pass selects gain when the playback request is emitted and does not
continually update a playing sample as either source or listener moves. Custom
per-channel gain/mixing support is deferred until audible testing demonstrates
a need for it.

## 5. Initial gameplay scope

The first phase covers sounds belonging to gameplay already implemented:

1. environment: door opening and closing, locked/no-way feedback, and
   pushwalls where supported;
2. combat: knife, pistol, machine gun, gatling gun, enemy shots, dog attacks,
   actor alert/pain/death voices, player damage, and player death; and
3. pickups: ammunition, weapons, health, treasure, keys, and extra life.

Menus, intermission narration, unimplemented bosses/projectiles, and music are
later work. Logical IDs and priorities stay stable so later coverage does not
require rewriting gameplay call sites.

## 6. AGNB asset and loading contract

Each AGNB 0.2 audio record is a RIFF `LIST BUFR` record containing:

```text
BHDR  u16 exact VDP sample buffer ID
AUDI  u8 format=0x09, u16 explicit sample rate
DATA  nonempty unsigned 8-bit mono PCM
```

Mixed sample rates are valid. Native Wolf effects use 7000 Hz; fallback assets
retain their existing rates.

The canonical AGNB loader validates metadata and record bounds, streams PCM
through its image-owned 8 KiB transfer window, consolidates the buffer, and
creates the VDP sample. Wolf3DOrig reuses that transfer window and API without
duplicating labels. Every u16 ID and sample rate handled through a 24-bit eZ80
register must have its upper byte controlled using the repository's proven ADL
idioms.

Loading remains synchronous and uses the fixture's existing breadcrumbs. A
failed sound asset must not prevent the game from starting: record the failure
in the loading breadcrumbs, leave that logical effect unavailable, and continue
silently when gameplay requests it.

Sample IDs and callable command-buffer IDs occupy documented, nonoverlapping,
stable ranges which do not collide with Wolf image/HUD IDs or shared firmware
facilities. The generator emits a manifest mapping logical sound, source,
sample rate, byte length, sample ID, and playback-command IDs. The build records
total resident sound bytes, container size, and loading time so SRAM growth is
visible well before it becomes dangerous.

## 7. Playback transport

The first implementation uses standard VDP audio commands and the ordinary
Buffered Commands API. It does not require a Wolf-specific firmware command.

For each sample/channel combination needed by the final allocation, setup
uploads a short command buffer containing the proven waveform selection and
play sequence. Runtime playback invokes it with:

```text
VDU 23,0,0xA0, commandBufferId; 1
```

The six-byte buffered call avoids repeatedly sending the multi-byte waveform
and play commands across the UART. Volume or distance gain may be sent as a
small ordinary command immediately before the buffered call. Sample buffers
and command buffers remain distinct.

Direct ordinary playback is retained as a diagnostic fallback while the
buffered path is validated. A custom compact sound-trigger opcode, writable
command templates, quantized-volume command matrices, and the Jukebox
gain/mixing firmware hooks are optimization options only after measurement and
audible testing show that the proven buffered path is insufficient.

The backend counts UART bytes emitted for audio and measures eZ80 dispatch
time. These measurements are diagnostic; audio must not reduce or stall the
fixed simulation cadence.

## 8. Music boundary

Wolf3D music is IMF-like OPL2 register sequencing, not PCM or MIDI. Each music
chunk contains a u16 byte length followed by four-byte events:

```text
u8  OPL2 register
u8  register value
u16 delay in 700 Hz ticks
```

The stream loops and expresses already-rendered OPL2 programming rather than
notes and instruments. The Author has a heavily modified MIDI playback system
for Agon; if its repository is encountered, record its location for follow-up.
A later phase will compare its event model, timing, looping, instruments, and
channel use with IMF. No music channels, conversion, or sequencing are part of
the initial sound-effects implementation, but the sound channel/ID allocation
must leave room for them.

## 9. Validation and acceptance

1. Validate every generated AGNB record against its source PCM, logical ID,
   sample rate, length, stable buffer ID, and manifest entry.
2. Test logical event generation, same-quantum priority arbitration,
   deterministic three-channel allocation, and catch-up suppression without
   requiring audible output.
3. Verify direct and buffered wire streams byte-for-byte, including ID-range
   separation and missing-sample behavior.
4. Exercise environment, combat, pickup, death, and Escape shutdown in the
   bespoke emulator without changing the 30 Hz simulation behavior.
5. Obtain explicit audible approval on emulator and physical hardware;
   emulator success alone is not hardware audio acceptance.
6. Report resident VDP bytes, container size, load time, UART bytes per event,
   and eZ80 dispatch timing before considering more channels, higher-quality
   replacements, custom firmware commands, or music.
