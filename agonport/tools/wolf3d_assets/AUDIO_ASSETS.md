# Wolf3D sound-effect assets

This directory's audio path turns the original shareware sound inventory into
one deterministic AGNB 0.2 container. It preserves original digitized bytes
and sample rates without upsampling or normalization. Thirty currently used
effects omitted from the shareware digitized set are rendered offline from
their original PC-speaker pitch streams; no runtime synthesis is required.

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
`orig/src/WOLFSRC/AUDIOWL1.H`/`WL_GAME.C`. The former temporary test-pack
mapping remains an explicit contingency at
`../agon-utils/examples/agnb/audio/assets/processed`, but no current producer
selects it. `--no-fallbacks` therefore generates the same production assets.

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

## Original PC-speaker effects

Production requests thirty original effects which have no VSWAP digitized
mapping. They include the shell/intermission effects (`HITWALL`, `MOVEGUN1`,
`MOVEGUN2`, `SHOOT`, `ESCPRESSED`, `DONOTHING`, `LEVELDONE`, `ENDBONUS1`,
`ENDBONUS2`, `NOBONUS`, and `PERCENT100`) plus the formerly generic player,
combat, actor, and pickup effects (`NOWAY`, `PLAYERDEATH`, `DOGDEATH`,
`GETKEY`, `ATKKNIFE`, `GETMACHINE`, `GETAMMO`, `HEALTH1`, `HEALTH2`,
`BONUS1` through `BONUS4`, `GETGATLING`, `BONUS1UP`, `AHHHG`, `SPION`,
`NEINSOVAS`, and `DOGATTACK`).
Their authentic `PCSound` streams are stored in the first 69 AUDIOT chunks.
Each byte is a PIT pitch (or zero for silence) held for one 140 Hz service
tick; `ID_SD.C` uses divisor `pitch*60`.

The generator deterministically renders those streams as unsigned 8-bit mono
PCM at 7000 Hz. Every original tick is exactly 50 output samples, pitch changes
restart the integer phase accumulator, and silence remains sample 128. The
manifest labels these records `pc_speaker_original`, retains their source
chunk and original AdLib arbitration priority, and keeps runtime playback on
the same buffered-sample path as every other effect.

## Test-pack contingency inventory

The tool retains explicit mappings for nineteen samples from the canonical
22-effect AGNB transport-test collection. Production no longer selects any of
them: every corresponding logical sound resolves first to the authentic
PC-speaker stream above and is labeled `pc_speaker_original` in the manifest.
The dormant contingency mappings are:

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

If a future non-WL1 logical effect explicitly promotes one of these files, its
native 16384 Hz rate is preserved. They are not claims of original-game
fidelity. `wilhelm.wav` remains excluded and reserved for a future easter egg.

The WL1 archives alone now supply every current environment, combat, actor,
player-death, pickup, elevator, and intermission producer. `TAKEDAMAGESND`
remains a byte-exact native WL1 record because it appears in `wolfdigimap`,
but the shareware source never requests it; visual palette/HUD feedback owns
ordinary player damage. Logical
sounds outside that scope remain durable unavailable manifest entries rather
than being silently discarded.

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
