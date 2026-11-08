# Olimex105 — full-game profiling checks passed; cleanly released

The corrected populated floor0 game completed250 render submissions with120
unique headings (819degrees recorded positive rotation), then returned to MOS.
All250 WPF1 samples join real native drawing records with zero discarded
attempts. Three disk batches contain120/120/10 records; WOLFPROF.BIN is16096B,
SHA464505fd03e9c340867a67f95462ee3e6df30bf7e1fe0800c816b9b518adf339.
Actual322539B resident RAM was saved before any later LOAD/reset. Profiler
status0, timer retired/restored, valid equal entry/exit SP and idle native
INFO17 margins2040/1780bytes all pass. No optical observation is inferred.

Native drawing averages22.19ms (median22.30,p9523.29,max23.60), including
preemption at nominal240MHz. The ordinary game loop's logging-excluded fence
intervals are33/34 nominalms, averaging30.06 completions/s. These are ordered
fences rather than measured scanout. This is the normal game with unchanged
fixed-step scheduling; it does not measure a new asynchronous/max-rate pipeline.
The two closed logging gaps are925/893ms, including115/85ms file I/O; most of
the remaining gap is native-log retrieval/cue overhead. The final logging gap
remains open-ended in the format. Logging hitches still affect play/catch-up.

The original controller subsequently FAILED during final listener retirement:
raw_state(post) and final collection reused post-exit-metadata.json across the
intentional listener restart in verify_route. The actual metadata client refused
the old boot BEFORE a new request. Original failure and journal remain intact;
this was after all game/data/state checks and did not invalidate saved samples.
Separate frozen samelease cleanup105 used fresh metadata journals, verified
RECOVER-inspect state1, retired the listener normally, restored the exact incoming
1105920B85f9 native application/touched-tail span and independently read back every
byte. One matched current bootstrap and complete fresh rootCLI/cursor/mode0/
callback0/route0/startup/listener/inputneutral/offlineSD/worker0/freeUSB handback
passed. No game replay or extra recovery reset was needed. All original,
observer/tracer and cleanup actors joined before normal release at18:50:55EST
on November7. Actual next6502 owner and Extender were immediately notified.
SD remains mounted. Original suite verdict stays failed; game qualification
and the separate successful restoration are reported independently.

A second harness evidence issue overwrote the original game serial.bin with
SAVE-only CLI proof. The explicit returned-CLI receipt and actual RAM/DONE/WPF
remain valid; no missing raw transcript is fabricated. Future helper code gives
that proof its own directory and uses a unique final EXIT journal. Original345
inputs were verified unchanged and fully snapshotted before these source edits.
Neither correction is applied retroactively or used to replay105.

Machine-readable result and all250 decoded records: [results/actual105](results/actual105).
Complete raw evidence/all345 selected inputs archive is local
build/actual105-evidence.tar.gz,20,482,823bytes,
SHA06d8223fac0098ec551fc59eaed5e4e957ff05444f757c1d08e6441e36b68c17.
Current P4d9b/EMOSa25f/native5d657/startuped403/listener0566 are restored/retained.
Alexe's earlier loading failure remains a separate investigation; hardware
success does not identify its cause or remove the physical/emulated MOS difference.
Old optimization goal remains paused; no new bench case is selected.

Post-release harness corrections passed27 focused checks under compiler510.
The three real-client lifecycle checks reproduce the original stale-boot
refusal, complete the corrected collection flow across three listener epochs,
and preserve the original transcript during RAM capture. The negative control
also exposed an unclosed metadata handle on refusal; the private helper now
closes it explicitly. The affected three checks were rerun cleanly; original
logs/warning are retained. No network/device or additional hardware run occurred.
