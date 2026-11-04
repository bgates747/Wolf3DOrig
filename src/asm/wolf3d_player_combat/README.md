# Wolf3D player-combat regression

This project has two deliberately independent regression layers.

`scripts/player_combat_oracle.py` is a pure-host specification grounded in
the bundled shareware `WL_AGENT.C`, `WL_STATE.C`, `WL_ACT1.C`, and
`WL_ACT2.C`. Its directed unittest suite covers all four weapon timelines,
held/repressed fire and ammo fallback, weapon selection and presentation
coherence, projected/line-clear target ordering, exact knife and gun RNG draw
semantics, dormant damage and every ordinary pain/death chain, per-class
scores and extra lives, and the complete stable runtime-drop allocator,
collection, capacity, and reseed lifecycle. Symbolic C state and shape names
keep that model independent of the assembly's compact numeric representation.

Run the host oracle from the repository root:

```sh
.venv/bin/python -m unittest discover -v \
  -s src/asm/wolf3d_player_combat/scripts \
  -p 'test_player_combat_oracle.py'
```

`src/player_combat_regression.asm` separately executes the production eZ80
weapon timeline, target selection, ordinary-enemy injury/death transitions,
scoring, and runtime pickup drops. Its full hitscan-path boss case prevents a
shootable Hans from being filtered before the already-tested boss death path.
It also pins the original release/repress
behavior of automatic weapons, synchronous occlusion, the `GiveAmmo`
attack-frame guard, and first-person weapon-shape dirty edges.

Run it from the repository root:

```sh
.venv/bin/python \
  src/asm/wolf3d_player_combat/scripts/run_player_combat_emulator_regression.py
```

For a staged source tree, set `W3D_STAGED_ROOT`; set `W3D_RUNTIME_ROOT` when
the emulator links live in a different Wolf3DOrig checkout.

The residual Episode 1 parity audit records three intentional Agon policies.
The accepted aiming cone is 16 projected pixels instead of the DOS
`viewwidth/10` value. Full `transx` and renderer-owned `FL_VISABLE` are not
available across the write-only renderer boundary, so targeting uses reduced
Q8 depth plus current CPU projection and `CheckLine`; equal reduced depths
retain live-list order, and a clear farther actor is not masked by an opaque
nearer one. Player input and attack animation still advance on the fixed
2,2,3 original-tic cadence used by the rest of the 30 Hz simulation.
