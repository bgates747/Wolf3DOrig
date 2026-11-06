# WOLF-PERF-002 — Verify and repair benchmark camera rotation

The Author watched the physical benchmark but saw no scene rotation. Prove
that the paced fixture applies changing camera headings and presents changing
frames before using its timings to characterize gameplay. Preserve the original
PERF-001 evidence and label its workload/visual validity provisional.

The root TODO owns immutable IDs WOLF-PERF-002-01 through -07. Source and
results for this investigation stay here; production and original frozen
hardware inputs remain unchanged. The Author authorized implementation and
Oryx testing on 2026-11-04; the subsequent explicit immediate physical selection is recorded in
HARDWARE-VISIBLE.md. That unchanged visible-only repeat passed both turns
with Author confirmation. No firmware flash, commit or GUI launch occurred.

1. Trace scripted heading -> serialized pose -> native mirror -> renderer ->
   displayed page. Check coordinates, scene geometry, camera clipping and
   visible output, rather than accepting matching angle records alone.
2. Reserve normal FIFO Oryx custody for at most three 300-second headless
   invocations, first reproducing the original paced fixture with framebuffer
   captures, then only necessary diagnostic/fixed controls. Stop on unexpected
   runtime failure. Use existing pinned R06/R07 runtime and fresh profiles.
3. Retain sampled displayed framebuffers with timestamps and headings where
   available, prove useful visual differences at separated headings, and
   inspect the actual scene. Captures are diagnostic, not calibrated timing.
4. Make any necessary correction in a fresh task-owned fixture; preserve
   PERF-001 source/binaries and all raw results. Retain a reproducible original
   versus corrected comparison. Check completion, integrity and normal teardown.
5. Release Oryx after owned processes stop, retrieve/hash evidence and notify
   any actual successor before extended analysis. Report root cause, affected
   timing claims, remaining uncertainty and stopped human review instructions.
   Human visual approval remains with the Author.

Status: -01..-05 completed/disposed by results and Author room/rotation
acceptance. -06 audio-only cue source and speech are prepared but compilation/
qualification were deferred for the immediate hardware slot. Live-game spin
comparison remains pending until the Author is ready.

Audio update: renewed Author instruction implemented native playback/generation
and Wolf cue; ten host checks and three Oryx292 cases pass. See voice/RESULTS.md.
Candidate handed off for Extender review; physical audio booking was rejected
by automatic approval review pending separate human authority. No booking or
hardware action occurred; -06/-07 remain open for those acceptance boundaries.
