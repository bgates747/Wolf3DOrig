# Original WL1 HUD asset build

This staged addition is intended to be copied into
`agonport/tools/wolf3d_assets/`:

- `formats/vgagraph.py` — strict VGAHEAD/VGADICT/VGAGRAPH picture decoder;
- `formats/hud.py` — stable original-chunk names, dimensions, and buffer IDs;
- `scripts/build_hud_assets.py` — extraction, Agon64 conversion,
  manifest/include generation, and AGNB packing;
- `tests/test_vgagraph.py` and `tests/test_hud_contract.py` — focused decoder
  and real-data/container checks.

The script reuses the already-vendored `formats/palette.py`,
`agnb/container.py`, `palettes/Agon64.gpl`, and the project `.venv`'s
`agonutils`/Pillow installation.

## Stable VDP IDs

- Original chunk 98 (`STATUSBARPIC`): `0x4062`.
- Original chunks 103 through 144: `0x4000 + chunkId`, hence
  `0x4067` through `0x4090`.

The generated container has exactly these 43 original chunks. Chunk 98 remains
the archive's original 320x40 image; the build does not synthesize, override,
or pack an extended status panel.

## Screen composition assumed by this milestone

- The raycast viewport is 256x160, centered at screen `x=32`, `y=20`.
- The 320x200 play area supplies the surrounding border on all four sides.
- Original chunk 98 is plotted directly at `x=0`, `y=200`, occupying the final
  40 rows of Agon mode 8.
- Splash/title assets are intentionally out of scope.

## Build and test after copying

Run with the project-local Python environment from the repository root:

```bash
.venv/bin/python agonport/tools/wolf3d_assets/scripts/build_hud_assets.py
.venv/bin/python -m unittest discover \
  -s agonport/tools/wolf3d_assets/tests -v
```

Generated output lands in
`agonport/assets/generated/wolf3d/hud/`: `hud.agnb`, `hud_assets.jsonl`,
`hud_buffers.inc`, source/converted PNGs, and individual `.rgba2` payloads.
The default palette method is nearest-colour RGB with no dithering, matching
actors and static sprites; walls and doors use Floyd-Steinberg. Other HUD
methods remain available via `--method` for visual comparisons.
