# Hand-edited HUD overrides

This tracked directory is the durable home for manually edited Wolf3D HUD
PNGs. Keep only intentional hand edits here; extracted and converted build
artifacts remain under the ignored `agonport/assets/generated/` tree.

`build_hud_assets.py` checks this directory one filename at a time. If a PNG
matches a generated HUD name (for example `weapon_knife.png`, `digit_0.png`,
or `face_1_a.png`), it replaces that source image. Missing names continue to
come from `VGAGRAPH.WL1`. `statusbar.png` replaces only original chunk 98's
320x40 image; no extended status-panel asset is generated.

Overrides must retain the dimensions of the asset they replace. The build
validates dimensions and records the chosen source in `hud_assets.jsonl`.
HUD conversion defaults to nearest-colour RGB with no dithering.
