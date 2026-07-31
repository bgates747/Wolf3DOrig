# Hand-edited sprite overrides

This tracked directory is the durable home for manually retouched,
already-palettized actor, pickup, and static-object PNGs. Keep only intentional
hand edits here.

- Original extracted PNGs: `agonport/assets/generated/wolf3d/orig/sprites/`
- Mutable palettized PNGs to copy from:
  `agonport/assets/generated/wolf3d/processed/`
- Rebuilt PNG/RGBA2222 targets: that same ignored `processed/` directory
- Build script:
  `agonport/tools/wolf3d_assets/scripts/convert_assets.py`
- Packed targets:
  `agonport/assets/generated/wolf3d/levels/level_*/sprites.agnb`

Copy the desired processed file here without renaming it, for example
`sprite_0050.png`, then edit this tracked copy. On later builds a matching
file here replaces automatic nearest-colour RGB conversion; assets absent
here continue to be generated normally. Dimensions and transparent background
must remain unchanged. The override is treated as final palettized artwork
and is encoded to RGBA2222 without applying palette conversion again.
