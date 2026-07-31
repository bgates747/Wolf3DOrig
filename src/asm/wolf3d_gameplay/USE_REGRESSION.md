# Production door-use regression

`src/use_regression.asm` is a directed real-eZ80 regression which includes
the production `wolf3d_motion.inc` and directly calls
`w3d_use_adjacent_door` and `w3d_handle_use_edge`. It does not substitute a
Python implementation of the interaction logic.

Run it from the project root with the project virtual environment:

```bash
.venv/bin/python \
  src/asm/wolf3d_gameplay/scripts/run_use_emulator_regression.py
```

As with the ClipMove and pickup runners, `W3D_STAGED_ROOT` may name a staged
source tree while `W3D_RUNTIME_ROOT` independently names the normal checkout
containing the emulator executable, MOS image, and stock VDP module. The
runner assembles under a short `/tmp/u*` pathname, boots a disposable headless
SD-card profile, reads `use_result.bin`, and removes the profile on exit.

The thirteen assembly-resident cases cover:

1. The player at the E1L1-reproducible near-well step (`tile+0x2000`) operates
   the current tile while facing toward its center plane.
2. The player at the corresponding far-well step (`tile+0xE000`) operates the
   same current tile from the opposite side.
3. A player immediately west of a door operates it while facing east.
4. A player immediately east of a door operates it while facing west.
5. A player immediately north of a door operates it while facing south.
6. A player immediately south of a door operates it while facing north.
7. An ordinary current floor tile falls through to a facing-adjacent door.
8. An invalid current-cell door index fails closed even when a valid door is
   adjacent in the facing direction.
9. A key-1 door refuses a player without key bit 0.
10. The same key-1 door opens for a player carrying key bit 0.
11. Operating a door already opening is ignored without dirty state or timer
    mutation.
12. Operating a fully open, unobstructed adjacent door starts it closing.
13. The held Space state causes exactly one operation per rising edge: after
    the first operation the harness deliberately resets the door and dirty
    state behind the still-set latch, proves a second held sample does
    nothing, releases Space, and proves the next press operates it again.

Every case checks the selected door index, exact action, targeted dirty byte,
sum of the complete 22-byte dirty array, world-dirty state, and both door
timer bytes. The edge case additionally checks the persistent key latch after
press, hold, release, and re-press. This makes a stray neighboring dirty byte
or a hidden repeat operation fail deterministically.
