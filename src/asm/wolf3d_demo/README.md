# Recorded-demo direct regression

This fixture exercises the production Episode 1 recorded-demo parser and
state machine on a real eZ80 target under the stock emulator stack.  It checks
canonical stream selection and wraparound, original button/control decoding,
the exact 70 Hz / four-tic to 30 Hz rational cadence, terminal detection, and
the local-input abort contract.

Run it with:

```sh
python3 src/asm/wolf3d_demo/scripts/run_demo_emulator_regression.py
```

The runner copies the production include tree into a short isolated build
directory before assembly.  This avoids both assembler path limits and races
with concurrent production builds.
