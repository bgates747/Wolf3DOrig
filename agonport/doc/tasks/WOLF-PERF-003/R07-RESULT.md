# r07: coherent loading text and counts on both pages

WOLF-PERF-003-11 refinement requested by Smith: double buffering applies to
both the breadcrumbs and the label naming what is loading. Implemented in
both benchmark applications without changing their timed loops or assets.

One authoritative stage pointer, per-stage completed count and total count
own the loading display. Each phase resets its count; each existing finalized
image/audio callback increments it. Paint the entire current hidden page from
that state, present/fence, then reconstruct/fence the other page from the SAME
state. Each future exposure follows the ordinary ordered swap. No per-page
cursor history, half-updated label or alternating dot history is relied on.
Panel identifies shell/audio/tiles/sprites/HUD, decimal completed count and the
pending rotation. Final preparing-room panel uses all-asset total. Two full
room warmups remain before timing. Register state preserved; a fence error is
latched and callback failure follows ordinary loader-abort handling.

Seven assemblies pass under Pi157; released20:49:53UTC. All six positive
benchmark variants share identical loading UI source, preserve r06 bench.inc
byte-for-byte as source, and preserve all assets/module bytes. No native or
VDPlet renderer changes. Setup is allowed extra work; no timing data pooled.

Fab validation01 passes600poses/two turns, normalQuit. A Fab-only proof branch
holds the fifth-asset panel on each side of one intentional swap. Captures004
and006 are byte-identical.68raw hashes verified. An attempted final-counter
read from after.bin was out of bounds because that diagnostic prefix ends at
wp_result_end before appended UI data. Retain inspection-correction.json;
this was not zero counts or a guest failure.

A separate Fab-only validation02 assembly under Pi159 adds one setup-only
loading-state.bin, leaving benchmark binaries untouched. It repeats the same
page flip and completes600poses,normalQuit0,whole59.530s,peak60.5C.68retrieval
hashes verify. Actual guest state reads completed470,total470,ASCII00470,error0.
Independent RIFF container record counts are shell180+audio50+tiles16+sprites135+
HUD89=470. Captures004/006 are again identical. No runtime state inferred from
an out-of-bounds memory view. Raw result:build/r07/validation02-result;
verification:build/r07/verification.json; review image:results/r07/loading.png.
Both captured pages show the same phase label and count, not just a matching
background. Proof pauses exist only in the named Fab visual variant.

Fresh STOPPED manual profiles on Oryx are under:
.emulator/wolf-perf003-loading-review/{bespoke-fab,bespoke-flexe,vdplet-flexe}.
No old profiles/results replaced. Fab review uses the same visible runner:
.venv/bin/python agonport/doc/tasks/WOLF-PERF-003/fab_visual.py run --visible --profile .emulator/wolf-perf003-loading-review/bespoke-fab
B's full Xtensa runtime still has no existing Fab adapter; its normal benchmark
guest is assembled with the identical UI helper, not claimed fully run in Fab.

All owned test emulators stopped; fresh whole-host idle inspection passed.
Oryx312 remains HELD until Smith explicitly says release. No GUI launched on
his behalf; boost0 unchanged, no hardware operations or shared adoption.
