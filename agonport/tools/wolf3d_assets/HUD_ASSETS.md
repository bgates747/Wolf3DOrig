# Original WL1 HUD asset build

This staged addition is intended to be copied into
`agonport/tools/wolf3d_assets/`:

- `formats/vgagraph.py` — strict VGAHEAD/VGADICT/VGAGRAPH picture decoder;
- `formats/hud.py` — stable original-chunk names, dimensions, and buffer IDs;
- `scripts/build_hud_assets.py` — extraction, Agon64 conversion, 320x80 panel
  composition, manifest/include generation, and AGNB packing;
- `tests/test_vgagraph.py` and `tests/test_hud_contract.py` — focused decoder
  and real-data/container checks.

The script reuses the already-vendored `formats/palette.py`,
`agnb/container.py`, `palettes/Agon64.gpl`, and the project `.venv`'s
`agonutils`/Pillow installation.

## Stable VDP IDs

- Original chunk 98 (`STATUSBARPIC`): `0x4062`.
- Original chunks 103 through 144: `0x4000 + chunkId`, hence
  `0x4067` through `0x4090`.
- Composed 320x80 mode-8 `status_panel`: `0x40F0`.

The composed panel contains chunk 98 exactly in rows 0–39. Rows 40–79 are a
neutral full-width material band in the same blue/cyan/bevel visual language,
without copying the original labels or readout slots. The build asserts that the
panel's converted RGBA2222 top half is byte-identical to the separately
packed chunk 98.

## Screen composition assumed by this milestone

- The raycast viewport is 256x160, centered at screen `x=32`, `y=0`.
- The original 320x40 `STATUSBARPIC` occupies screen rows 160–199.
- The generated neutral extension occupies screen rows 200–239.
- The resulting 320x80 `status_panel` is therefore plotted once at `x=0`,
  `y=160` in Agon mode 8.
- Splash/title assets are intentionally out of scope.

The lower half is a **deliberate neutral fill**, not newly invented original
Wolf3D artwork and not a claim that the original strip continued for another
40 rows. It reuses only the source strip's established blue/cyan palette and
horizontal bevel language so the otherwise unused mode-8 rows look cohesive.

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
