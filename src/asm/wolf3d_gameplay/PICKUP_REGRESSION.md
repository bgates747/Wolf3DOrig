# Production pickup regression

`src/pickup_regression.asm` is a directed real-eZ80 regression which includes
the production `wolf3d_motion.inc` and calls `w3d_apply_current_pickup`. It does
not substitute a Python pickup implementation.

Run it from the project root with the project virtual environment:

```bash
.venv/bin/python \
  src/asm/wolf3d_gameplay/scripts/run_pickup_emulator_regression.py
```

As with the ClipMove runner, `W3D_STAGED_ROOT` may name a staged source tree
while `W3D_RUNTIME_ROOT` independently names the normal checkout containing
the emulator executable, MOS image, and stock VDP module. The runner assembles
under a short `/tmp/p*` pathname, boots a disposable headless SD-card profile,
reads `pickup_result.bin`, and removes the profile on exit.

The thirteen assembly-resident cases cover:

1. Refused first aid at full health: object remains active and all dirty state
   remains clear.
2. Refused ammunition at full ammo, using static slot 120: object remains
   active and all dirty state remains clear.
3. First-aid health saturation at 100.
4. Clip ammunition saturation at 99.
5. Key-3 inventory-bit mutation.
6. Treasure score crossing 40,000, incrementing the persistent 16-bit treasure
   count, awarding one life, and moving the next threshold to 80,000.
7. Machine-gun ammunition and current/best/chosen weapon upgrade.
8. Full-heal health, ammunition, extra-life, and treasure-count mutation.
9. Treasure crossing 40,000 while already at nine lives: score, threshold,
   and treasure advance, but lives stay capped and the lives HUD bit is clear.
10. Full heal while already at nine lives: health, ammunition, and treasure
    advance, but lives stay capped and the lives HUD bit is clear.
11. Gibs at health 10: health advances to 11 and the pickup is consumed with
    health-only HUD dirtiness.
12. Gibs at health 11: pickup is refused, remains active, and all dirty state
    remains clear.
13. A clip collected at zero ammo while idle: ammo rises to eight and current
    weapon is restored from the chosen chaingun, dirtying exactly ammo and
    weapon while leaving best/chosen weapon unchanged.

Every accepted case additionally requires a `FFFF` consumed shapenum, exactly
one targeted per-static dirty byte, the exact HUD dirty mask, world dirty set,
player-pose dirty clear, and the exact persistent `uint16` treasure count.
Refused cases require the inverse. The harness also sums the complete 121-byte
dirty array so a stray neighboring mutation is not hidden by a correct target
byte.
