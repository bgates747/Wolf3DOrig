# Wolf3D sound-effect assets

This directory's audio path turns the original shareware sound inventory into
one deterministic AGNB 0.2 container. It preserves original digitized bytes
and sample rates; it does not upsample, normalize, mix, or synthesize effects.

## Generated outputs

- `agonport/assets/generated/wolf3d/audio/sfx.agnb` contains one `LIST BUFR`
  record per available logical sound. Each record is `BHDR`, `AUDI`, `DATA`.
- `agonport/assets/generated/wolf3d/audio/audio_manifest.json` records all 69
  `AUDIOWL1.H` logical IDs, including unavailable entries, source provenance,
  original priority, exact PCM hash, size/rate/duration, runtime IDs, totals,
  and source-file hashes.
- `src/asm/wolf3d/src/wolf3d_audio_assets.inc` is the assembly contract. It
  contains logical IDs, the fixed-width asset table, and the 450-byte original
  Wolf3D attenuation table collapsed to monaural VDP gain.

Regenerate all three from the project root with:

```sh
.venv/bin/python agonport/tools/wolf3d_assets/scripts/build_audio_assets.py
```

Run the exact-byte and contract tests with:

```sh
.venv/bin/python -m unittest \
  agonport.tools.wolf3d_assets.tests.test_audio_assets
```

The generator defaults to the repository's `orig/data/*.WL1` files and
`orig/src/WOLFSRC/AUDIOWL1.H`/`WL_GAME.C`. The approved temporary fallback
collection is `../agon-utils/examples/agnb/audio/assets/processed`. Pass
`--no-fallbacks` to audit native-only availability.

## Stable IDs

Every original logical ID reserves these IDs whether or not PCM is currently
available:

- sample buffer: `0x5000 + logicalId`
- playback-command buffer, channel 0..2:
  `0x6000 + logicalId*3 + channel`

Unavailable entries carry zero live IDs in the generated assembly table and
`null`/empty live IDs in the manifest; their reserved formula IDs remain
explicit. This prevents a missing sound from accidentally referring to an
unrelated buffer while keeping the ABI stable when an effect is added later.

## Original shareware inventory

The `#define UPLOAD` DigiMap in `orig/src/WOLFSRC/WL_MAIN.C` maps these 20
logical sounds to native digitized VSWAP effects: `HALT`, `DOGBARK`,
`CLOSEDOOR`, `OPENDOOR`, `ATKMACHINEGUN`, `ATKPISTOL`, `ATKGATLING`,
`SCHUTZAD`, `GUTENTAG`, `MUTTI`, `BOSSFIRE`, `SSFIRE`, `DEATHSCREAM1`,
`DEATHSCREAM2`, `DEATHSCREAM3`, `TAKEDAMAGE`, `PUSHWALL`, `LEBEN`,
`NAZIFIRE`, and `SLURPIE`. `DEATHSCREAM2` and `DEATHSCREAM3` intentionally
share VSWAP digitized index 13.

The terminal VSWAP directory describes 46 digitized indices. In the WL1 file,
indices 0..15, 20..22, and 32 have real pages; the others are sparse. Index 32
is not mapped by the shareware logical enum. Native records are unsigned
8-bit monaural PCM at exactly 7000 Hz and are copied byte-for-byte.

Original effect priorities come from each logical sound's AdLib
`SoundCommon.priority` field in `AUDIOHED.WL1`/`AUDIOT.WL1`, not from guessed
port values.

## Approved fallback inventory

The current environment/combat/pickup producers require 19 logical sounds
that have no mapped native WL1 digitized effect. They use explicit PCM from
the 22-effect AGNB test collection and are always labeled
`test_pack_fallback` in the manifest:

- `NOWAY` -> `gun_empty.wav`
- `PLAYERDEATH` -> `scream.wav`
- `DOGDEATH` -> `dog_yelp.wav`
- `GETKEY`, `HEALTH1`, `HEALTH2`, `BONUS1`, `BONUS2`, `BONUS3`, `BONUS4`,
  and `BONUS1UP` -> `got_treasure.wav` (generic pickup fallback)
- `ATKKNIFE` -> `knife.wav`
- `GETMACHINE`, `GETAMMO`, and `GETGATLING` -> `gun_reload.wav`
- `AHHHG` -> `ahh.wav`
- `SPION` -> `achtung.wav`
- `NEINSOVAS` -> `ugh.wav`
- `DOGATTACK` -> `dog_woof_single.wav`

These fallback WAVs remain at their native 16384 Hz. They are not claims of
original-game fidelity. `wilhelm.wav` is deliberately excluded and reserved
for a future easter egg.

With the approved fallback directory present, every presently planned
environment, combat, actor, player-damage/death, and pickup producer has an
available asset. Logical sounds outside that scope remain durable unavailable
manifest entries rather than being silently discarded.

## Monaural distance gain

`WL_GAME.C` contains hand-tuned 15-by-30 left/right attenuation tables.
`SetSoundLoc` indexes them as `[abs(forward)][lateral+15]` after clamping the
row to 0..14 and lateral to -15..14. The generator parses those source tables,
averages each stereo pair as `(left+right+1)//2`, and maps attenuation to VDP
gain as `round((15-att)*127/15)`.

The resulting 450-byte rows preserve the source tables' exact palindromic
half-cell symmetry (the two central columns correspond to lateral -1 and 0)
and are emitted into the tracked assembly include. This supplies original
spatial falloff without asking the monaural Agon output path to emulate
stereo.
