# WOLF-PROD-001 — Production updated; current runtime check passed

Smith's direct instruction is implemented. Plan4806492 was committed/pushed
before code; amendment7fd14c1 records the first compiler-memory stop and bounded
correction. The old optimization goal remains paused.

## What the normal game now uses

The maintained production renderer now contains the completed combined021
algorithms, rather than leaving them available only through an experimental
module selection. The new ordinary wrapper has no WPN1 timing array/RUN100.
The normal CLI, normal optional profile, verified payload and deployment manifest
now select this exact production module:

| Output | Identity / size |
| --- | --- |
| Production VDPlet | `7490d81c2f1e6aed85142d9604a0cad9a3949c03ec236cc818d1c6a339602463`,21852B |
| Resident text / data | 15004B /11172B; ABI1.6/caps257, PSRAM workaround enabled |
| Normal complete-game binary | `1634f87d0ebee00e9e2ac3918c675a8e62d1b83d3755eb091690e98d793b9cb9`,310096B |
| Optional profile binary | `953a4495c24c941a44e4a6788d97864c50d143bd7638384a2a0a2a76433451a9`,320896B; same7490 renderer |
| Default deployment payload | `tgt/wolf3d-production-optimized-async-r1`,68 hash-verified files, all10 levels |

The module is3216B larger than older production266f (18636B), and720B smaller
than the diagnostic combined8d3d package (22572B). This includes the faster
original tangent ray walker, hoisted byte-span helper, corrected background
extent, exact degree table, guarded narrow division, full-height scaling setup
reuse and texture-column chains. Unmeasured PERF023 and unpromoted sprite013
are excluded. Production-local tables avoid breaking the older bounded scenes'
fine-angle quarter-wave table. Normal simulation/render scheduling is unchanged;
this is not the separately discussed independent async/newest-pose rewrite.

The native-profile command deliberately selects retained diagnostic8d3d with
the same renderer algorithms; it remains explicitly named because7490 has no
native WPN1 recording interface. Old prepared payloads and frozen controls remain
untouched. Future module builds fail closed on source/output/SDK/package drift.

## Signed-shift repair

The new active ray walker has no `fixed_div` and no negative signed-left-shift
scaling. The test-only older renderer reference and both maintained bounded
scene helpers now multiply the widened numerator by65536 instead of shifting it.
All three actual function bodies pass16 negative/sign/truncation/INT32 boundary
cases under UBSan. The existing nonzero denominator and int32 quotient domain
remain; no saturation, alternate zero behavior or geometry change was added.
The corrected legacy renderer's full six-scene pixels/geometry match retained
pre-promotion output exactly. Historical frozen copies were not rewritten.

## Original-code lineage

[INTEGER-LINEAGE.md](INTEGER-LINEAGE.md) and ORIGINAL-SOURCE-PINS.json verify the
original source's16.16 positions,360/3600 angle domains, precomputed tangent
intercept traversal, integer projection and scaling. Our mostly integer frame
pipeline derives from that design; it is not a new floating-to-integer rewrite.
Original sine values use signed magnitude, while our C++ representation uses
two's complement/widened multiplication. Original initialization used floating
point to build tables; ours does that offline. View size/height units, borrowed
RGB222 rows, modern helper/cache optimizations and MOS scheduling are port
choices. This does not claim every original DOS rounding decision is identical.

## Executed qualification

Compiler815 completed in63.86s (peak55.1C, minimum629552KiB available) after the
first attempt813 stopped at the unchanged512MiB guard. Host GCC debug/GC controls
resolved the memory issue; target O2/PSRAM flags and algorithms were unchanged.

- ASan/UBSan mirror, renderer, asset/refusal/capacity/pushwall and module
  lifecycle/retry/direct/copied/fizzle checks pass; maximum asset leases3.
- Exact saved combined021 equality:460800 fixture pixel bytes,10752 geometry,
  76800 published-frame bytes,46080000 pixels across600 alternating-page frames,
  1081200 associated state bytes and51971104 span-output bytes. The600-frame
  script covers300 heading values, not all360 or all possible gameplay states.
- 98727 span/rectangle cases,65536 mask pairs, guarded rows/pages/world/leases;
  900 original tangent entries,34 explicit arithmetic cases,89987 analytic room
  rays (13 near-corner cases excluded),4 door and4 moving-wall orientations;
  six hand-derived original crossing transcripts pass.
- 1000576 unsigned+signed actual helper-body pairs pass. Native O2 output contains
  the guarded hardware QUOU path in divide_u64 at0x3b04; no undefined imports.
  The selected module-owned wall/acquire path is1360/2048 stack bytes. This is
  not a new whole-runtime/ISR/foreign-callback peak measurement.
- Compiler816 assembled normal/profile/native-profile clients and verified their
  actual package storage/address operands against the selected image lengths.
  All37 preparation/profile tests and fresh complete payload verification pass.
  Current release checks verify dc43ecb8 BIN,576b69f3 ELF, all SHA256SUMS entries,
  and exact RC3 MOS ZIP member. Neither build session touched an emulator/device.

[EVIDENCE.json](EVIDENCE.json) retains actual results, source/package/client joins,
stack frames and complete payload file identities. Compiler children joined and
both successful slots released normally; no compiler lease is retained.

## Completed current-release runtime check

The frozen public-wire lifecycle/pixel leaf passed once on actual Oryx419 on
November9 at7:20PM Eastern, using production7490d81c, dc43ecb8 firmware,
576b69f3 ELF and the existing d77a7305 backend. All41 input identities and the
actual backend loader/library closure matched before execution. No source,
firmware, backend or test input changed after the freeze; there was no replay.

- Public capabilities799; CONFIG/full APPLY/render and every76800-pixel frame
  oracle matched. Hidden frames remained hidden until C3.
- Missing-HUD refusal, altered-retry refusal, exact successful retry and the
  second full-frame oracle passed. All five expected error cases matched.
- The60-slice app-paced fizzle matched its five whole-frame checkpoints and
  final surface synchronization. Overlap/after-completion errors matched.
- RESET, FINI/unload, stale-handle rejection, reload and final empty slot passed.
- Native execution reported no failed/unhandled/unregistered/unmapped faults.
  INFO17's minimum reported free stack after the exercised path was2036B;
  this is scoped runtime evidence, not a universal maximum-stack proof.

The complete worker took6.727 host seconds; supervisor8.353 seconds, peak58.375C,
boost OFF. These durations/cycle counters are emulator correctness evidence,
not a physical framerate comparison. All native worker threads/process groups
joined;21 returned evidence files were retrieved and hash-verified. Fresh
canonical whole-host inspection was empty and419 released normally at7:21PM
Eastern. The actual next TRS-80 request was immediately notified. No lease,
process, target access or ongoing reservation is retained.

[RUNTIME-RESULT.json](RUNTIME-RESULT.json) records the raw result, input/retrieval
identities, entry/release proof and resource observations. RUNTIME-QUEUE.json
retains the earlier queued observation as history. This backend-only test did
not run MOS, the eZ80 client, full gameplay, a GUI or physical hardware. It adds
current-release module qualification to the completed production build checks;
full-game acceptance across all10 levels remains a separate scope.

The historical combined20.90ms drawing and30.06fps presentation measurements
remain historical evidence, not newly measured performance for7490. The
optimization goal stays paused; WOLF-VIEW-001 remains task preparation only.
