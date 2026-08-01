# Wolf3D positional-audio regression

This isolated project specifies and directly exercises the production mono
positional adapter in
`../wolf3d/src/wolf3d_audio_spatial.inc`. Nothing here is included by the game
application.

`scripts/spatial_oracle.py` is an independent executable contract for the
port's reduced version of the original `SetSoundLoc` behavior:

1. Subtract authoritative full 16.16 source and player coordinates, then
   arithmetically reduce each difference to signed Q8. Fractional bytes take
   part in the subtraction, including borrow across the discarded byte.
2. Load the normalized 0..359-degree `(cos,-sin)` Q12 basis represented by the
   production 360-entry motion table. Each signed product truncates toward
   zero independently before the two terms are combined.
3. Rotate into listener-forward/lateral coordinates and add the original
   `FOCALLENGTH=0x5700` listener displacement, reduced to `0x57` Q8, to the
   forward result.
4. Index the original table as
   `min(abs(forward>>8),14)*30 + clamp(lateral>>8,-15,14)+15`.
5. Use the generated 450-byte mono collapse of the original 15x30 left/right
   attenuation tables. Submit `A=logical sound id`, `B=gain`, and positioned
   metadata `C=1` to `w3d_audio_request`.

The actor entry receives `IX -> W3D_ACTOR_*` and preserves the complete 24-bit
IX register. The tile entry receives `B=tile x`, `C=tile y` and spatializes the
exact `.5,.5` tile center. Other GP registers and flags are caller-saved.

## Host regression

From the repository root, using the project virtual environment:

```sh
.venv/bin/python -m unittest -v \
  src/asm/wolf3d_audio_spatial/scripts/test_spatial_oracle.py
```

The host suite checks all 360 generated motion-table values, reconstructs the
450 gain bytes from the original C attenuation tables, pins fractional-borrow
boundaries, cardinals, diagonals, focal displacement, front/back behavior,
lateral and distance clamps, per-product truncation, and compares 25,000
deterministic randomized actor/tile cases through an independent byte model.

## Direct production-eZ80 regression

Regenerate the durable assembly vector corpus after a deliberate contract
change:

```sh
.venv/bin/python src/asm/wolf3d_audio_spatial/scripts/generate_spatial_vectors.py
```

Then assemble and run the real production entry points under the stock VDP
emulator:

```sh
.venv/bin/python \
  src/asm/wolf3d_audio_spatial/scripts/run_spatial_emulator_regression.py \
  --timeout 60
```

The direct fixture captures the final request ABI, relative Q8 values, table
row/column, call count, and actor IX across directed and deterministic random
vectors. It uses the same short-path staging and fixed MOS-file mailbox
convention as the other direct Wolf3D regression projects. The generated
expectations are derived from `spatial_oracle.py`, not from production
assembly state.
