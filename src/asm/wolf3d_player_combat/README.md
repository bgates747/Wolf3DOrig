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
scoring, and runtime pickup drops. It also pins the original release/repress
behavior of automatic weapons, synchronous occlusion, the `GiveAmmo`
attack-frame guard, and first-person weapon-shape dirty edges.

Run it from the repository root:

```sh
.venv/bin/python \
  src/asm/wolf3d_player_combat/scripts/run_player_combat_emulator_regression.py
```

For a staged source tree, set `W3D_STAGED_ROOT`; set `W3D_RUNTIME_ROOT` when
the emulator links live in a different Wolf3DOrig checkout.
