# Four-way headless results — 2026-11-05

All twelve selected trials passed. Both Flexe backends passed their first trial,
so each received five total trials. No asset-loading stall occurred in this
batch. This does not establish a transport repair or resolve the earlier
intermittent loading failures; the new loading UI introduces additional ordered
page updates and may change scheduling.

| Emulator | Renderer | Passed / attempted | Completed render records |
| --- | --- | --- | --- |
| Fab 1.2.5 | Bespoke native VDP | 1 / 1 | 600 |
| Fab 1.2.5 | Native production-source VDPlet bridge | 1 / 1 | 600 |
| Flexe, private FX-153 frontend | Bespoke ESP32 image | 5 / 5 | 600 each |
| Flexe, private FX-153 frontend | ESP32 VDPlet runtime/module | 5 / 5 | 438, 432, 439, 437, 443 |

Every fixture closes at scripted step600: two full turns at E1L1 tile34,36,
center34.5,36.5, with enemies suppressed. The paced fixture coalesces overdue
poses while retaining its final step. Flexe VDPlet's smaller record counts
therefore reflect that existing pacing policy; they are not incomplete turns.
Both Fab runs recorded all600 scripted poses. These emulator counters do not
establish physical FPS.

## What was built and checked

The corrected r07 eZ80 fixtures bind the bespoke map before warmup and show
asset stage/count on both display pages. The six normal task variants share
the same loading helper; benchmark loops and assets remain unchanged. Old
bespoke measurements without map binding remain excluded from comparison.

Fab's fourth combination is a private, single-module source bridge. It compiles
the retained production VDPlet renderer with the existing host-pointer shim,
uses real buffered uploads and live hidden VGA rows, and checks every byte of
the uploaded retained module package. It is **native source execution, not an
Xtensa loader or ESP32 execution**. Its named Fab guest omits unsupported target
CCOUNT diagnostics; Flexe retains the actual ESP32 runtime/module path.

Bridge build22.764s, peak61.25C, boost0. Contract checks report0failures, including
wrong-package rejection, overlapping leases, bounds, duplicate load, invalid
release and busy unload. SO SHA256:
`b416e5e88cdfd6c4abfe76ace44caa3a6dd2807bd1904fe933a17fddb7ecc776`.
Pi161 separately assembled the Fab B guest and released normally.

The full Fab B run recorded one load, one unload,602 renders (two warmups plus
600 poses), zero errors, zero residual leases and no loaded/busy/frame state
after cleanup. Captures show the intended large room; final captures from both
Fab backends show the normal `/wolf3d *` MOS prompt. See
[bespoke room](results/four01/fab-bespoke-room.png),
[VDPlet room](results/four01/fab-vdplet-room.png) and their adjacent MOS captures.

All ten Flexe runs returned normally to MOS, exited0 and reported failed=false,
unhandled=unregistered=unmapped=0. Offline checking confirms every completed
record's step/angle, native sample identity and actual UART pose/render bytes:
24 request bytes plus6 presentation/fence bytes for A;65 plus6 for B. No timing
claim is derived from these byte checks. Both Fab record streams also pass
header, coordinate, step/angle, stage-order and normal-Quit checks.

## Evidence and custody

Frozen controls/profile manifest: `build/four01/freeze.json`.
Per-trial outcomes: `build/four01/controller-results.json`.
Detailed offline checks: `build/four01/verification.json`.
All338 retrieved file hashes verify. Retrieval archive SHA256:
`74c7b75bbe76426dd4b826de02a4d5529531c0baf195bdacab2f22b5715d5709`.
Raw captures, guest results, UART traces and backend statistics are
retained under `build/four01/evidence`; original failures remain untouched.

The initial detached controller disappeared before launching any emulator
(empty log/no run directory). A normal retained tool session then ran the
complete finite cohort. This launch issue is not counted as a guest trial.

Peak CPU temperature across trials62.375C, below the unchanged80C guard; boost
remained0. All owned runners/emulators stopped, and fresh whole-host inspection
reports no emulators. **Oryx generation312 remains held at Smith's instruction;
no release occurred.** No hardware or firmware operation took place.

The four-way functional arc is complete. Corrected CPU/unpaced controls and
physical bespoke-versus-VDPlet timing remain separate open benchmark work.
If emulator problems return, hand their evidence to Flexe and move Wolf to
other useful work: hardware is the game's primary platform. This reminder
does not select a new Flexe build, experiment or repair.
