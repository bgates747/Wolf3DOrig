# Wolf3D player-death regression

This project directly exercises the production eZ80 death and asynchronous
render code used by `src/asm/wolf3d`. The fixture copies no implementation:
it includes the live production `.inc` files so protocol or state-machine
changes cannot silently diverge from the application.

Run it from the repository root:

```sh
python3 src/asm/wolf3d_death/scripts/run_death_emulator_regression.py
```

For a staged source tree, set `W3D_STAGED_ROOT`; set `W3D_RUNTIME_ROOT` when
the emulator links live in a different Wolf3DOrig checkout. The runner builds
in a deliberately short temporary path because `ez80asm` retains DOS-era path
and filename limits. It creates an isolated temporary SD card and does not
modify the application build.

The expected result is `182/182` checks. The real eZ80 fixture covers:

- callback-routine routing and complete ten-byte mailbox copying for ordinary
  render and fizzle events;
- one-shot render/fizzle events, purpose latching, wrong-token rejection,
  independent stale-sequence rejection, and fail-closed ownership conflicts;
- the public render-permission gate across every death phase and while another
  asynchronous producer owns the surface;
- cardinal and all four diagonal killer bearings, plus zero, out-of-range,
  inactive, and coincident killer rejection;
- lethal promotion, weapon suppression, shortest-path turning, angle wrap,
  the exact 180-degree tie, and the original-rate `4,4,6` degree cadence at
  30 Hz;
- the direct semantic transition from final-target purpose to target-sync
  purpose and only then to fizzle ownership;
- validated fizzle-event consumption, release-before-new-press acknowledgment,
  and timed hold completion even while a key remains held;
- original signed-life semantics, full 32-bit level-score and extra-life
  threshold restoration across a deliberately destructive reseed hook,
  persistent difficulty, canonical attempt inventory, and the respawn latch;
- the production E1L1 attempt reseed, including rebuilt actor/static/door and
  player-area state, dirty-prefix contracts, and fail-closed level-reset and
  ordinary-render submission preflights that preserve pending state.

The fixture writes a 16-byte `death_result.bin` mailbox with magic `W3D1`, a
case/reason diagnostic, and schema byte `1`. The runner decodes it and reports
the first failing phase.

This is an eZ80 ownership/state regression. The target and target-sync checks
invoke the production purpose-transition API directly; they do not inspect
physical mode-8 back buffers or count VDU `C3` commands. The fizzle-start test
uses a deterministic hook and an injected completion record. Default fizzle
wire-command integration, successful BUFFERED_WOLF3D level-reset replay, and
red-LFSR pixel order require the bespoke VDP implementation. Full application
timing, slow-render, and interactive acceptance remain separate integration
gates.
