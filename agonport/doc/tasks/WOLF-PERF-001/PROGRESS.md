# WOLF-PERF-001 development evidence

The first headless baseline is qualified. R06 passes all three benchmark arms
and the intentional timer-abort control, with 83 retrieved files hash-verified.
Oryx generation 277 was released after fresh idle evidence, with no successor.
The physical three-arm cohort subsequently passed; see HARDWARE-RESULTS.md.
Author acceptance and external calibration remain open.
Earlier failures are retained below; none is silently promoted to a baseline.

## Author selections and implementation

1. Tile (34,36), centered stationary player, no enemies; retained canonical
   map/doors/statics. The Author extended the run to 720 degrees/20 seconds.
2. Task-siloed diagnostic module brackets production renderer, row scope and
   full module dispatch with CCOUNT. The PRT1 donor and header/output contracts
   are documented in README.md. No shared source or firmware was edited.
3. CPU, unpaced hidden-render and normal-C3 cadence builds assemble. Three
   independent host checks validate level-section preservation, exact two-turn
   arithmetic, corrupt-output rejection and production-source identities.
4. Compile generation 54 built the initial three arms; generation 58 rebuilt
   register-preserving fixture entry/vector API and diagnostic-buffer cleanup.
   Both reservations were released with all compiler children stopped.

## Rejected target cohorts

1. Oryx generation 270 / r01: old frontend 28f50e87…, backend 0866265b…,
   firmware 8d980025…, interpreter. Stream stalled at 36,513 eZ80-to-VDP bytes
   during shell upload. No benchmark output or timing interval was reached.
   Ordinary SDL Quit stopped the frontend. Fault counters were zero, which
   does not establish transport correctness. Original artifacts remain in
   ignored `build/evidence/r01-cpu/` and the original Oryx profile.
2. Oryx generation 271 / r02: exact Rally direct-row comparison snapshots,
   frontend 7e7d0e1b…, backend 0866265b…, firmware a50eb23a…, JIT. Startup and
   two warm-up frames passed; CPU wrote 600 valid indexed pose samples and
   marked timer-vector restoration. Application teardown then reached RST38
   panic, so the run is rejected as a qualification result. Native/render and
   paced arms were not launched. Artifacts remain in
   `build/evidence/r02-cpu/` and the original Oryx profile. Raw decoding alone
   is not accepted success and must not be advertised as a baseline.
3. Fresh idle inspections released both generations. The second release
   returned 6502 as successor; its scheduling notification was delivered.
   The initial notification denial was resolved by direct Author permission;
   no alternate transport was used to bypass it.

## Third cohort outcome and fourth diagnostic

R03 adds IX/IY preservation around timer-vector API and the fixture entry,
clears task log buffer 0xf000 after readout and before exit, and keeps the same
Rally runtime, workload and timing boundaries. The runner now detects RST38
panic immediately and requests normal SDL Quit before signal fallback. A
manifest self-reference caught by staging was removed; no target launched
with a mismatched manifest. Request 3af0f7123aa0 obtained generation 273 after
a fresh idle checkout. CPU again wrote 600 records, then hit the same panic at
the first normal audio-stop call. Register preservation did not fix it. The
runner detected the panic and ordinary SDL Quit stopped the emulator after
30.72 host seconds. Rendering arms were not run. Source, raw output and logs
remain in ignored `build/evidence/r03-cpu/`. A fresh idle inspection released
generation 273 and the returned Rally successor was notified successfully.

R04 adds full loaded-application snapshots before and after the benchmark,
entry/exit stack-pointer capture and a final stack snapshot, all outside the
timed interval. These distinguish executable corruption from an unbalanced
fixture stack. Pi compile generation 61 completed and was released. Fresh
stopped Oryx profiles retain the same matched Rally runtime; FIFO request
ca258bca56ec followed Rally. Each process remained bounded to 300 seconds and
the first unexpected failure stopped the cohort.

## Proven staging overlap and R05

R04 / Oryx generation 275 reproduced the panic with balanced entry/exit stack
pointers. Before the benchmark even started, its audio executable at 0x0626e6
contained exact Xtensa package bytes from offset 0x26e6. The client's fixed
0x060000 staging address overlaps the growing application. The diagnosis and
raw byte comparison are in STAGING-DIAGNOSIS.md. No production source was edited.
Owned shutdown, retrieval and fresh idle release completed with no successor.

Pi compile generation 62 built R05 with task-only staging at 0x0a0000, a
package-size-specific limit and checked code/staging/stack separation. An
unsupported forward-reference equate was caught by the assembler before any
target use and replaced with the checked fixed range. R05 / Oryx generation
276 passed CPU and all 600 hidden renders, including normal teardown, intact
audio code and balanced fixture stack. Its paced arm returned cleanly too, but
the analyzer rejected 4,563 unused sample bytes containing 0xff. The assembler's
DS padding was not zero, contrary to the initial assumption; CPU/full-count
runs had no unused slots. The rejection was retained rather than bypassed.
All three original profiles and raw evidence remain in build/evidence/r05-*.
Fresh idle release completed with no successor.

## Corrected R06 cohort

R06 explicitly clears all 600 sample slots before the timed interval. It also
stops owned PRT1 on failure and verifies installation of the old vector using
an idempotent exchange. A separate cpu-fail build deliberately aborts immediately
after acquiring PRT1; it produces no performance result. The runner accepts
that control only with its specific timer-restored failure marker and clean
owned emulator shutdown. Ordinary benchmark arms still require complete output
and a normal MOS return. Pi compile generation 63 completed and was released.

The fourth profile initially lacked its remote parent directory; staging failed
before execution. Completed, stopped profiles were hash-verified and retained;
only the missing control was finished. A checkout with an incorrect request ID
was refused, then the actual request 3e2ec70caf7e obtained generation 277 after
fresh idle evidence. No process ran under the refused checkout. All four
processes use the same matched runtime, with a 300-second per-process bound,
ownership asserted before each and first unexpected failure stopping the driver.

All four passed: CPU 600 records; unpaced 600 matching native renders; paced
429 matching presentations through step 600 with 171 coalesced poses; intentional
abort with old-vector restoration verified. The three ordinary arms returned
normally to MOS and retained intact audio code and balanced fixture stacks.
All backend fault counters were zero. Original raw evidence and snapshots are
in build/evidence/r06/; portable raw timing/CSV/JSON, identities and release
records are in results/r06/. Fresh idle release occurred at 14:24:28 UTC.
The final four host checks pass. A three-arm physical kit and runbook are
prepared locally, without deployment, firmware flashing or physical execution.

## Olimex scheduling requested

Smith subsequently requested Olimex time for the hardware suite. Reservation
4361fc8e2b3d, owner wolf3dorig/task WOLF-PERF-001-hardware, is first waiting
behind Rally's active NAT-HW-001 checkout. A 30-minute allowance covers
preparation, three bounded performance arms, retrieval and exact restoration.
Extender received durable mail
2026-11-04_09-34-39_wolf3dorig_wolf-perf001-hardware-reserve-one and an accepted
immediate chat notification. No physical checkout or bench operation has begun.
Installed compatibility is to be reconciled before grant; no firmware change
was selected. The current hardware runbook records the scheduling scope.

Extender's pregrant compatibility note was read and resolved without device
contact. The actual retained r2 image hashes to 8ade1e7d…; historical INFO0 is
0x0100 and INFO1/discovery capabilities are 0x011f. Eleven retained-source ABI
typedefs match the task SDK. Source reproduction and fresh live capability
claims remain distinct; the actual consumer's mandatory interface/fit guards
still control admission. All task replies use the Eirene-forwarded ten-byte
form, with READ16 and public callback APIs. No private Arthur callback binding.

R07 adds only conditional mode acquisition and a 240-MOS-tick setup settling
wait. Its measured fixture body remains identical to R06, and its native module
hash is unchanged. Pi compile generation 67 and successful one-process Oryx
CPU smoke generation 279 are released. The original R06 harness/source remain
preserved; its timing report is not silently relabeled R07.

The explicit-action hardware controller, three fresh payload inventories,
component/tool hashes, compatibility assessment and calibration disposition are
frozen in hardware/freeze.json, SHA
a07f838c27c27e1d3b639d3664f0270fcdad4dc79851728eb337dddfc1f12944.
Five device-free coordinator checks and four fixture checks pass. Pyserial 3.5
was added to the project venv for the maintained passive serial helper.
Extender received readiness mail
2026-11-04_09-59-53_wolf3dorig_wolf-perf001-readiness-freeze-two and an accepted
immediate chat alert. Latest local queue state still has Rally active and Wolf
first waiting. No physical checkout, serial open, network probe or deployment
has occurred. Calibrated speed/optical timing remain pending, and future raw
physical results will explicitly include the installed diagnostic runtime's
per-transaction logging cost. No firmware change is selected.

## Physical cohort completed — 2026-11-04

Generation 26 passed CPU600, hidden-render600 and paced201/final-step600.
Nominal PRT rates: 461.18 updates/s, 12.19 renders/s, 10.02 presentations/s.
All returned binaries reproduce their original reports; code, stack, timer and
mode restoration passed. Diagnostic firmware and uncalibrated clocks limit the
claims as detailed in HARDWARE-RESULTS.md. Lease released 15:40:12 UTC after
clean handback; Extender and queued 6502 chat notified. No active reservation
or device custody remains. Frozen hardware readiness inputs were preserved.
