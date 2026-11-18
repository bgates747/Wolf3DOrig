# Physical profiling readiness

**Historical hardware01 kit: retired after actual101. Do not relaunch.**
Actual101 failed before guest LOAD/RUN and restored/released cleanly; see
[RESULT101.md](RESULT101.md). Subsequent Alexe work fixed the actual producer's
INFO17 opcode, full-game package/code overlap and test-only held-key seam.
These are not covered by the old341-pin kit below. Current emulator findings
and remaining physical/motion qualification are in [ALEXE-RESULTS.md](ALEXE-RESULTS.md).
Any future hardware case needs a new immutable kit/current binding/fresh grant.
The historical commands/pins below are retained as provenance only.

Frozen kit `build/hardware01/kit.json` is copied byte-for-byte to
HARDWARE-KIT.json. SHA256 `0f774a0c138e26e0edd63aa7e89ede9ca64616afd78d163cf4c48a4757c861b5`.
341 inputs,16 staged files. One299967-byte actual full-game guest
`fda77dfd4f13e8d824f10fa371759ec5ad7f6e81bd1786161b5607b22579ea22`,
linked listing `0e7f1d863f6e14240586874f55930effe2789e5888b8b6b78c0af581639754e2`,
real22572-byte module8d3d. No synthetic reader or visibility hold.
Five offline host/producer checks pass under released compiler437; initial436
metadata expectation failure retained. Actual package-byte operands are22572;
normal client's unchanged strict ceiling is131072, not the old fixture22573.

Mandatory controller, normal foreground:

```
/Agon/mystuff/agon-extender/.venv/bin/python /Agon/mystuff/Wolf3dOrig/agonport/doc/tasks/WOLF-PROFILE-001/launch02.py --context ACTUAL_FRESH_CONTEXT
```

Mandatory separate observer, normal foreground; start as soon as the controller
publishes `build/hardware01/observer/session.json`:

```
/usr/bin/python3 /Agon/mystuff/Wolf3dOrig/agonport/doc/tasks/WOLF-PROFILE-001/observe.py --context ACTUAL_FRESH_CONTEXT --folder /Agon/mystuff/Wolf3dOrig/agonport/doc/tasks/WOLF-PROFILE-001/build/hardware01/observer --lease ACTUAL_NEW_LEASE
```

For all Olimex bench procedures, use the sole authoritative [bench guide](/Agon/mystuff/agon-extender/docs/operations/olimex-bench/README.md).
