# AGNB abortable-callback regression

This fixture exercises `src/asm/wolf3d/src/agnb_api.inc` directly on the eZ80
emulator with real FatFS file I/O and both AGNB 0.1 images and 0.2 audio.

The compatibility entry points continue to ignore callback return values.
The explicit `agnb_load_images_with_abortable_callback` and
`agnb_load_audio_with_abortable_callback` entry points interpret callback
`A=0` as continue and `A!=0` as stop after the just-finalized record. A stop
closes the FIL and returns `agnb_error_callback_abort`, retained in
`agnb_last_error`.

The regression proves full continuation, legacy compatibility, exact abort
after the second of three finalized records, early reader position, and closed
file state for both forms.

```sh
.venv/bin/python src/asm/agnb_abort/scripts/run_agnb_abort_emulator_regression.py
```
