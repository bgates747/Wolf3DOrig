# Corrected Olimex profiler — historical hardware02 readiness

**Retired after actual105. Do not relaunch this kit.** Selected game/data
checks and separate complete restoration/release are recorded in [RESULT105.md](RESULT105.md).
Future helper fixes change the source pins and require a new freeze/admission.
The original readiness description below is preserved as history.

Direct Smith authorization on November7,18:20Eastern; old optimization goal
paused. Request47bae5199a9c, taskWOLF-PROFILE-001-hardware02. Frozen local
build/hardware02/kit.json is copied exactly to HARDWARE02-KIT.json; SHA256
a0a6aa96d725793752f7b573277399f5c9570bce4243447cfe7c8f48a57e0e5b.
345 pinned inputs/16 staged files, same corrected322539B guest96d6e7d4,
22572B module8d3d. All24 offline checks passed under released compiler485.
Source-only host/kit verification passed; no target access yet.

Mandatory normal foreground controller:

```
/Agon/mystuff/agon-extender/.venv/bin/python /Agon/mystuff/Wolf3dOrig/agonport/doc/tasks/WOLF-PROFILE-001/launch02.py --context ACTUAL_NEW_CONTEXT
```

Mandatory separate normal foreground observer, after new session record appears:

```
/usr/bin/python3 /Agon/mystuff/Wolf3dOrig/agonport/doc/tasks/WOLF-PROFILE-001/observe.py --context ACTUAL_NEW_CONTEXT --folder /Agon/mystuff/Wolf3dOrig/agonport/doc/tasks/WOLF-PROFILE-001/build/hardware02/observer --lease ACTUAL_NEW_LEASE
```

For all Olimex bench procedures, use the sole authoritative [bench guide](/Agon/mystuff/agon-extender/docs/operations/olimex-bench/README.md).
