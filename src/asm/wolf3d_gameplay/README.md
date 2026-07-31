# Wolf3D eZ80 gameplay regression package

This package is a durable, independent host oracle for the first eZ80-owned
gameplay layer: square-player collision, original `ClipMove` sliding order,
current-well/cardinal use targeting, lock gating, Space rising-edge behavior,
30 Hz door motion/timing, original blocking decorations, mutable pickups/HUD
state, and the complete fixture-generator door/static wire contract.

The directory is ready to live at `src/asm/wolf3d_gameplay`. Run the host
suite from the repository root with the project virtualenv:

```bash
.venv/bin/python -m unittest discover -v \
  -s src/asm/wolf3d_gameplay/scripts \
  -p 'test_gameplay_oracle.py'
```

`W3D_RANDOM_CASES` controls the default 10,000 randomized collision and
ClipMove cases. `W3D_STAGED_ROOT` can select a different Wolf3D worktree;
without it, scripts derive the repository root from their installed path.
For an external staged source tree, `W3D_RUNTIME_ROOT` may independently name
the normal checkout that owns the emulator profile and firmware symlinks.

The host tests deliberately do not import or execute assembly logic. They
compare the public geometry oracle with a separately written brute tile-range
and fixed-point slab implementation, exercise exact boundary cases, and decode
the generated VDU stream independently. `generate_gameplay_vectors.py` can
additionally emit a deterministic, inspectable JSON corpus.

The packed ClipMove suite is also executable on the real staged assembly in
an isolated Fab emulator profile:

```bash
.venv/bin/python \
  src/asm/wolf3d_gameplay/scripts/run_gameplay_emulator_regression.py \
  --random-cases 10000 --include-zero-delta
```

The random eZ80 vectors honor the gameplay routine's valid-start precondition:
the player's initial AABB is clear, centers stay away from the solid perimeter,
and an injected obstacle never overlaps that starting AABB. Destination AABBs
are unrestricted so wall rejection and all three ClipMove attempts are still
exercised. The validated staged result is 10,028/10,028 records. Directed
cases pin door-well entry, inclusive center-plane contact from both sides,
vertical/horizontal orientation, the last gap and first panel fractions, and
the action-independent `FFFF` opening. Four directed cases and randomized
records also exercise the separate blocking-static bit plane.

Pickup effects are also executed directly against production assembly in a
second isolated profile:

```bash
.venv/bin/python \
  src/asm/wolf3d_gameplay/scripts/run_pickup_emulator_regression.py
```

Its 13 directed cases cover refusal at capacity, gibs' exact health boundary,
health/ammo saturation, zero-ammo chosen-weapon restoration, key bits, weapon
upgrades, treasure scoring, the 40,000-point threshold, the original nine-life
cap, full heal, the `FFFF` removed-shape sentinel, exact HUD/world dirty masks,
and isolation of the one changed static slot. See
`PICKUP_REGRESSION.md` for the packed case contract.

Door use is executed directly against production assembly in a third isolated
profile:

```bash
.venv/bin/python \
  src/asm/wolf3d_gameplay/scripts/run_use_emulator_regression.py
```

Its 13 cases reproduce both reachable halves of an E1L1 door well, all four
exterior approaches, ordinary adjacent fallback, malformed-current fail-closed
behavior, locks, action transitions, complete dirty/timer state, and the held
Space latch. See `USE_REGRESSION.md` for the exact contract.

Important model choices match the current port contract:

1. Player collision uses the original `0x5800` square radius.
2. `ClipMove` tries combined X/Y, X only, Y only, then restores the base pose.
3. A valid door tile is a traversable well containing the VDP's zero-thickness
   center-plane slab. Fractions `0..position` are passable and
   `position+1..FFFF` are panel; plane contact blocks, `FFFF` has no panel,
   and action does not override position. Auto-close uses this same predicate.
4. Door travel uses the repeating `0955,0955,0956` 30 Hz increments and an
   exact `FFFF` sum saturates immediately, including after a close reversal.
5. Open wait uses seven third-ticks per update, closes on reaching 900, and
   clamps there while obstructed so per-tick retries cannot wrap the timer.
6. A valid current-cell door takes use priority from either well; otherwise
   angles 45/135/225 change the adjacent sector, with 315 south and 316 east.
   An invalid current door index fails closed rather than targeting a neighbor.
7. Lock values 1..4 use key bits 0..3; normal 0 and elevator-art 5 operate.
8. Blocking decorations live in a separate immutable 512-byte LSB-first
   occupancy bitset. They stop movement but never become DDA wall cells.
9. Pickup contact is a deterministic overlap with the player's square AABB
   after successful translation. Refused pickups remain active; consumed
   records persist with `shapenum=-1` and only dirty static/HUD fields are
   submitted.
10. Original score thresholds advance by 40,000 even when lives are already
    capped at nine; treasure count remains persistent 16-bit eZ80 state.

The runner creates a short, unique isolated profile under `/tmp/g*`; it does not
alter the repository emulator profile or SD image, and removes the temporary
profile when the process exits.
