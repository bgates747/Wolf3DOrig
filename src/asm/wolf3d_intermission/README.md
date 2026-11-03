# Wolf3D intermission regression

The production lifecycle is split so destination I/O overlaps presentation:

- `w3d_intermission_begin` captures the completed floor's immutable totals,
  derives the exact final bonus and durable `LevelRatios` record, draws the
  zero-valued start of the original count-up, and returns `A=0`, carry clear;
- `w3d_intermission_loading_tick` is an abortable AGNB completed-image
  callback. It advances the score/ratio count-up and BJ animation while
  polling nonblockingly, returns `A=0`, carry clear for ordinary progress
  (including a latched skip-to-final acknowledgment), and returns `A=2`,
  carry set for Escape;
- `w3d_intermission_finish` paces any count-up remaining after loading and
  returns after a loading-time acknowledgment has subsequently been released,
  or after a complete release/fresh-press/release cycle, with the same Escape
  result;
- `w3d_intermission_escape_is_requested` exposes the durable Escape latch so
  an owner can distinguish AGNB's generic callback-abort result from an asset
  failure and route it through the application's common exit; and
- `w3d_intermission_set_application_exit_query_hook` installs a predicate for
  callback-latched/application-global exits. It is queried before each live
  keymap poll, preserving short Escape taps which begin and end during a
  synchronous load. The corresponding resetter restores a local no-exit
  predicate.

This focused regression executes the production `wolf3d_level_time.inc` and
`wolf3d_intermission.inc` directly on the eZ80 emulator. It checks:

- level-time reset and the 29/30-tick second boundary;
- `59:59` rolling to `60:00`, entry into the `99:00` display clamp, and the
  clamp remaining stable;
- kill-total derivation from `FL_SHOOTABLE`, including exclusion of an inert
  actor record;
- the exact original treasure-total item set: 9, 10, 11, 12, and 18;
- zero-denominator percentage behavior, truncating `2/3` to 66%, equality at
  100%, and over-total capping at 100%;
- E1 par-time arithmetic, 500 points per second under par, 10,000 points per
  perfect ratio, exact 32-bit final bonuses, and the persistent ordinary-floor
  ratio/time record;
- immediate, nonblocking ordinary-floor presentation with its base, status
  bar, floor number, time, E1L1 par, zero-valued count-up fields, and bonus
  digit at their exact production coordinates;
- immediate, nonblocking secret-floor base/status-bar presentation;
- the time/kill/secret/treasure count-up state sequence, original logical
  tally/terminal sound choices, one-shot final award, and idempotent finalize;
- the production 32-bit score path's 135,000-point increment across four
  40,000-point extra-life thresholds (covered by the pickup/score regression);
- the four-completed-image portrait cadence, alternating original BJ pictures
  `$4037` and `$4060` at `(0,16)`;
- release-gated acknowledgment, including rejection of the held elevator key
  and durable latching of a fresh press while destination assets still load;
- finish after a loading-time acknowledgment's subsequent release, and
  blocking finish after an explicit release/fresh-press/release sequence;
- Escape abortion from both loading and finish, including Escape before input
  arming and Escape overriding an already-latched ordinary acknowledgment; and
- hook-only loading and finish abortion with an empty live keymap, proving a
  short callback-latched Escape cannot fall through the transition.

The drawing and shell seams are deterministic recorders, and the keyboard seam
returns scripted sixteen-byte MOS keymaps. All arithmetic, seed scanning, par
lookup, digit selection, lifecycle state, input interpretation, and animation
orchestration come from the production includes.

Run from the repository root:

```sh
.venv/bin/python src/asm/wolf3d_intermission/scripts/run_intermission_emulator_regression.py
```

The runner copies the production assembly directory into a short isolated
temporary path before assembling, avoiding `ez80asm`'s legacy path limit and
remaining safe alongside a production build.
