# Hand-edited wall and door overrides

This tracked directory is the durable home for manually retouched,
already-palettized wall and door PNGs. Keep only intentional hand edits here.

- Original extracted PNGs: `agonport/assets/generated/wolf3d/orig/walls/`
- Mutable palettized PNGs to copy from:
  `agonport/assets/generated/wolf3d/processed/`
- Rebuilt PNG/RGBA2222 targets: that same ignored `processed/` directory
- Build script:
  `agonport/tools/wolf3d_assets/scripts/convert_assets.py`
- Packed targets:
  `agonport/assets/generated/wolf3d/levels/level_*/tiles.agnb`

Copy the desired processed file here without renaming it, for example
`wall_001.png` or `door_normal.png`, then edit this tracked copy. On later
builds a matching file here replaces automatic Floyd-Steinberg conversion;
assets absent here continue to be generated normally. Dimensions must remain
unchanged. The override is treated as final palettized artwork and is encoded
to RGBA2222 without applying dithering again.
