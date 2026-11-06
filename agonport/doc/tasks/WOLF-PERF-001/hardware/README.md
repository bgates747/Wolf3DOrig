# Explicit Olimex actions

`physical.py` performs one explicitly selected action. It has no firmware or
reset action, no test autorun, no uncertain retry and no implicit next case.
The central grant, expected component identities, payload/runner/tool hashes
and supported Legacy/native-mode-0 entry are checked before target operations.
Extender must grant actual custody first. Paths and private connection values
are resolved from its maintained handoff, not this public document.

After grant, create a fresh private context JSON under ignored
`build/olimex01/` containing `grant` (actual grant JSON path), `output` (new
directory under `build/olimex01/evidence/`), `url`, `port`, `ports` (mainboard
and P4 serial device paths), and `entry_route: "legacy"`. The URL and stable
devices come from Extender's current machine-local record. No constructor or
host test contacts the hardware.

Invoke with the project virtual environment:

```text
.venv/bin/python agonport/doc/tasks/WOLF-PERF-001/hardware/physical.py CONTEXT entry
.venv/bin/python agonport/doc/tasks/WOLF-PERF-001/hardware/physical.py CONTEXT stage
```

Then select `run --case cpu`, `retrieve --case cpu`, `run --case unpaced`,
`retrieve --case unpaced`, `run --case paced`, `retrieve --case paced` as
separate actions, checking each receipt before dispatching the next. `stage`
only uploads and independently reads back files and explicit command scripts;
it never invokes an application. Runs use one EXEC of CD/LOAD/RUN/SAVE/listener,
with a 300-second capture bound and actual terminal/listener evidence.

Only after all three successful retrievals select `handback`. It verifies
startup/listener bytes, native mode 0, original cwd and fresh mirrored CLI,
issues text/visible/flashing cursor restoration, exits the listener, disables
the diagnostic mirror and checks neutral input, idle workers and free ports.
Its fresh observation is consumed by the central lease release; then send
Extender and any actual successor the handback before extended analysis.

Unexpected failure stops dispatch and retains journals. A missing completion
does not authorize collection, a repeat, a guessed reset or the ordinary
success handback. Close owned readers and report the precise operation/state
to Extender for the maintained recovery or exclusive repair lifecycle. The
30-minute planning allowance is not lease expiry or takeover authority.

Host-only checks:

```text
.venv/bin/python agonport/doc/tasks/WOLF-PERF-001/hardware/test_host.py
```

Results remain uncalibrated physical counters on the retained diagnostic native
image; see `COMPATIBILITY.md` for exact ABI/reply and calibration dispositions.
