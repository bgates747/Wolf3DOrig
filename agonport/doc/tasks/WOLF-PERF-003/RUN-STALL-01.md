# s01: bounded observation of intermittent setup stalls

q01 and q02 both stopped on a300-second pre-render timeout, at different
upload boundaries. Keep those failures and their literal frozen harnesses.
The unchanged bespoke CPU binary passed q01 and stalled q02. No rendering
comparison or UART repair follows from those observations.

Use Flexe's existing host-qualified FX-152 observer frontend625d08b7d2c119ab149ad63ec696af0a03808dca0ae78b66a8fe35755dfaed84
and matching read_record.py c5701735631da1b1cf5bc74874bfef4da1c4cd50118809f8cd2d80c90e0fa85b.
Preserve backend0866265b, each task firmware/ELF, MOS3.0.2, input shim and all
guest/assets. This is a private diagnostic selection within the authorized
benchmark investigation; no shared runtime adoption or owner build is selected.
FX-152 adds observation to the old7e7d0e1b baseline, not a transport repair.
Its retained source/tests, resource limits and interpretation contract remain
owned by flexe-agon-emulator/docs/tasks/FX-152/IMPLEMENTATION.md and CONTRACT.md.

Prepare fresh stopped profiles by verifying/copying the complete inputs from
these two owned stopped profiles, in this exact order:

|Order|Source|Purpose|
|---|---|---|
|1|q02/02-bespoke-cpu, r05 guest|Observe the most recent SFX upload stall|
|2|q01/06-vdplet-paced, r04 guest|Observe the original zero-log upload boundary|

At most two sequential headless JIT invocations. No screenshots/audio/GUI.
Each has a300-second outer bound including ordinary setup; an observer's
complete three-sample stasis window ends the diagnostic early. Normal guest
completion also ends a case. Stop the tranche at the first observed stall or
unexpected failure; only a normally completed first case permits the second.
No rescue bytes, replay, transfer chunking/pacing change, firmware correction,
guest change, interpreter substitution or additional cases are included.

Enable only FLEXE_TX_OBSERVER_OUTPUT at a fresh absolute private output path.
Retain fixed50s no-completed-send trigger,100ms poll,0/250/500ms samples,
630s observer lifetime,<=5lines/20KiB and existing one reader thread/no new
observer process. The shorter outer bound may produce interrupted/null/late
evidence; preserve that as unavailable/incomplete. Validate the final JSONL
with the exact versioned reader after normal Quit/join. A complete window
locates published producer/TX/CTS state, not guest intent, parser state or a
hardware cause. A no-stall pass provides no live stall diagnosis. Observer
execution may perturb timing; discard all such timings for speed comparison.

Freeze scripts, plan, reader and both complete profile manifests before launch.
Use a fresh normal Oryx FIFO reservation/whole-host idle checkout and assert
the actual token before each process. Ordinary Quit/join first; bounded own
process-group termination only as fallback. Retrieve/hash raw results and
observer records, verify owned workers gone and fresh whole-host idle, release
and immediately notify the actual successor before extended analysis. No Pi
compiler or Olimex work is part of this diagnostic.

Owner advice2026-11-05_12-48-19_flexe_wolf-perf003-fx152-advice-106 confirms
source compatibility, no stronger retained alternative and the need to keep
target qualification distinct. It permits no new scope. This plan explicitly
selects case2 only conditional on case1 normal guest completion without an
observed stall; the consumer owns that selection under Smith's existing
benchmark/debug authorization. Neither source profile is changed. Exact full
firmware/ELF/guest/assets/wrapper identities are frozen by profiles.json and
build/s01/freeze.json, not inferred from abbreviated names here. Cumulative
backend stats alone do not establish progress during a stalled interval.
