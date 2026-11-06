# Wolf frame-performance fixture

This task builds an isolated E1L1 camera rotation using the production eZ80
serializer and direct-row VDPlet renderer. The player stays at tile (34,36),
turns 720 degrees over 600 nominal 30 Hz steps (20 seconds), and spawns no
enemies. Geometry, doors and static scenery retain the original game data.
No production source, map or Rally source is edited.

The first headless cohort is qualified; see [results](RESULTS.md). The first physical cohort also passed; see [hardware results](HARDWARE-RESULTS.md).
Production-game FPS and external clock calibration remain unresolved. The task also
includes a prepared [physical runbook](HARDWARE-RUNBOOK.md).

## Workload and boundaries

1. `cpu`: generate all 600 poses and prepare/retire the real dirty batches,
   with no per-pose UART or render. Serializer lifecycle bookkeeping is measured
   separately; this is not populated-world simulation or enemy AI capacity.
2. `unpaced`: submit and wait for all 600 hidden renders without per-frame C3.
   Present once after timing. This measures completed hidden-frame capacity,
   not display FPS; it needs no unpaced-swap firmware patch.
3. `paced`: select the latest scripted pose from elapsed MOS ticks, at most
   one render outstanding. Complete, C3 swap and ordered INFO0 fence each
   presented frame. Record coalesced poses and fence-to-fence intervals.
   The camera still completes both turns if the renderer misses quanta.

All modes warm both pages with two frames before timing. Music and sound are
muted during the benchmark. Shell, audio and game assets are loaded through
normal startup, preserving their resident allocation history. Door motion,
random face changes, inventory and weapon animation are frozen for isolation.
All timed batches contain only the 10-byte camera pose plus the production
16-byte header and 2-byte record prefix, i.e. 28 bytes.

The first revolution is steps 1..300 and the second 301..600. Start is a
warm-up pose, not a timed sample. Step 600 is the final timed pose and closes
the second turn at zero degrees. Samples are never silently discarded.

## Timer provenance

The PRT1 setup/stop/IRQ comes from Rally's
`RALLY-28/custom-vdp/paced-road/control/source/prt.inc`: idle timer only,
reload 72, divider 256, nominal 18.432 MHz, 1 ms IRQ counter, and MOS API
0x14 vector install/restore. IX/IY are preserved across that API and the
fixture entry. MOS time is independently retained at nominal 120 Hz.
The 600-iteration empty-loop observation is retained without subtraction.
One-millisecond quantization limits individual CPU stage samples.

Xtensa CCOUNT/PRID reads follow Rally's
`RALLY-28/custom-vdp/incremental/wide-fill/phase_probe.c`. Task-generated module
source adds brackets around the actual production `render_world_direct` call,
the colour-row scope, and the complete production module dispatch. These
nested intervals include service calls and preemption; they are not exclusive
CPU cycles. Raw CCOUNT is retained without asserting calibrated hardware ms.
The task wrapper logs after timing into dedicated buffer 0xf000. The guest
fetches it through the existing READ16 protocol only after the batch ends.
This adds no shared firmware API or runtime source change.

The module remains one freestanding Xtensa translation unit, with the original
renderer and world-mirror source included. The diagnostic entry 100 resets only
its log count after warm-up. Production entry IDs retain their existing meaning.
A core-ID change, overflowing log or failed render returns an error.

The copied client stages its module at checked address 0x0a0000. The original
fixed 0x060000 address overwrote this application's audio code during LOAD;
[memory evidence](STAGING-DIAGNOSIS.md) established the cause. Build receipts
reject application/staging/stack overlap. Sample slots are explicitly cleared
before timing because assembler DS padding contains 0xff.

## Build and qualification

From the project root, after taking the canonical Pi build reservation:

```bash
.venv/bin/python agonport/doc/tasks/WOLF-PERF-001/build.py
.venv/bin/python agonport/doc/tasks/WOLF-PERF-001/test_contract.py
```

The builder uses the pinned SDK and project assembler resolver. Output stays
in ignored `build/`. It copies production assembly, applies checked task-only
entry patches, and writes separate binaries/manifests for the three modes.
Canonical W3L parsing/building validates tile openness and removes only actors
while replacing the pose and deterministic random seed. Host checks compare
every other level section, pin exact endpoints and reject corrupt evidence.

Stage `profile.py`, `run.py`, `analyze.py`, the canonical executable-preflight
snapshot in `build/canonical/flexe_profile.py`, and each payload onto Oryx under
this same task directory. `profile.py` creates stopped, isolated, hash-guarded
profiles via canonical setup and names their entry points Flexe. It uses exact
runtime snapshots, never another project's source or live profile for writes.

Take the shared Oryx reservation/checkout and assert the actual lease before
each process. On Oryx invoke the project venv's Python with `run.py PROFILE`;
the runner changes to PROFILE and runs only `./flexe-agon-emulator`. Both SDL
drivers are dummy. A copied, qualified SDL input shim supplies normal Quit
only after guest completion, teardown and restored MOS prompt. Each run has a
300-second default bound; the first unexpected failure stops its cohort.
Retrieve outputs and take fresh whole-host idle evidence before releasing.

A fourth `cpu-fail` profile intentionally aborts immediately after PRT1
initialization. Run it only with `--expect-abort`; the runner requires the
specific timer-restored marker, then ordinary SDL Quit and zero backend
faults. It is a cleanup control, produces no performance result and is excluded
from the physical kit. The failure path installs the old vector and verifies
it with an idempotent exchange before holding for host diagnostic collection.

The initial old runtime stalled before timing. The next cohort uses the exact
Rally direct-row runtime: frontend 7e7d0e1b…, backend 0866265b…, UART-repaired
firmware a50eb23a…, official MOS 3.0.2 image/map. Full hashes live in each
profile's immutable input receipt. Historical failed profiles remain unchanged.

## Output schema and acceptance

`timing.bin` is 16,233 bytes, little endian. Header: magic `WPF1`, schema byte
1, mode byte (1/2/3), completion byte, vector-restored byte; seven u24 values
(count, PRT start/end, MOS start/end, empty-loop PRT ticks, native-log bytes);
then tile x=34, y=36, enemies=0, reserved=0. The following 600 slots each hold
nine u24 values: step, angle, PRT stamps at pose start/end, packing end,
submission end, requested completion, presentation-fence end, and batch bytes.
Only `count` slots are valid; trailing slots must be zero. Files use MOS
create-new mode, not overwrite.

`native.bin` has four u32 header words (magic `WPN1`, schema 1, count, core ID)
and one five-u32 row per completed render: index, angle, inner renderer CCOUNT,
colour-scope CCOUNT, complete module CCOUNT. All frame identities and nesting
must match the guest record. Header counts exclude warm-up.

`analyze.py DIRECTORY` decodes raw evidence into `samples.csv` and `report.json`.
Its decoding checks do not by themselves prove successful application teardown:
accept results only with a successful `runner.json`, restored MOS prompt,
matching native completions and zero backend fault counters. It reports both
revolutions, mean/median/p95/max, cadence intervals, coalescing and both clocks.
Clock disagreement prevents unqualified milliseconds/FPS claims. Physical
speed and optical refresh require separate hardware evidence.

Full memory/stack snapshots are written before and after the fixture outside
timing. The accepted cohort compares the original audio code against both
snapshots and checks matching entry/exit stack pointers. Captured backend
`frames` counts include startup/refresh; use guest completion records for the
benchmark denominator.

## Remaining boundaries

No graphical emulator, SD deployment, flash, physical run, source publication
or optimization is performed by this fixture. Hardware staging and execution
remain later work under their normal authority. Keep new emulator-related
changes uncommitted until the Author's required review and commit approval.
