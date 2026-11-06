# Focused audio adoption review follow-up

Extender's requested failure-path evidence now passes against the actual C
player. The revised binary also passes valid and malformed-WAV Oryx checks.
The original candidate/source/results remain preserved. No physical booking,
playback or shared adoption has occurred; prior approval denial remains in force.

1. Added eight focused checks: missing audio reply, audioSuccess0, wrong channel,
   missing cleanup reset reply, rejected cleanup reset, failed ingress fence,
   partial upload plus cleanup timeout, and partial upload plus fence failure.
   Missing-reply execution is asserted to reach the240-tick bound and return.
   All18 actual-player parser/transport/failure checks pass.
2. Cleanup failure now prints `PLAYWAV CLEANUP UNCONFIRMED` and
   `cleanup=unconfirmed`. A preceding primary error remains unchanged (e.g.5 for
   short SD read); otherwise cleanup failure returns6. Tests inspect both return
   values and emitted text. Cleanup still attempts buffer release and ingress
   fencing after a reset-ack failure. No false final success is printed.
3. Removed `vdp_adv_consolidate` from the generic player. Official local
   agon-docs `Buffered-Commands-API.md`, “Using buffers for sound samples”,
   documents multiblock sample playback without consolidation. The revised
   player creates the sample directly from its uploaded blocks; the normal
   sample-create acknowledgment remains. Host checks assert no consolidation.
4. Reusable Makefile now resolves the normal `agondev-config` convention unless
   the caller supplies `AGONDEV_TOOLCHAIN`. Generic synthesis requires an
   explicit `--jukebox` or `AGON_JUKEBOX_ROOT`; missing-root and existing-output
   refusals were checked without network calls. Wolf-specific generation paths
   remain task-local and are outside the generic adoption package.
5. Serial Pi build93 compiled the revised native binary with warnings as errors
   and ran18 host checks; released12:22:30EST, nextnull. Oryx293 ran exactly two
   bounded fresh processes (valid playback and malformed refusal), both normal
   MOS return/SDLexit0/zero reported backend faults. Results retrieved, fresh
   whole-host idle proof and release12:24:40EST, nextnull. Wolf's unchanged
   integrated cue retains its previous Oryx292 pass, without a redundant rerun.
6. New candidate `../build/audio-notify-r02.zip`,143594B, SHA-256
   `4cfc99e124f0f26811401ef0e36ba54b4d5dcc4b7a29b7fa4c8a8e33ef6ac8d7`.
   Exact source/tool hashes, host output, native build log and both emulator
   results are under `../results/voice-r02/`. R01 zip/source/evidence remain
   immutable, and its prepared-but-unbooked hardware freeze is retained as
   `../build/audio-hw-r01/`. The current unbooked freeze points to the r02 binary.

The artifact is a candidate for Extender-owned adoption, not an installed shared
utility or a hearing claim. No alternate reservation route, peer booking,
physical action or firmware change was selected. The outstanding human decision
about the brief audio hardware test remains separate.

## Runtime/bench owner review resolved

Extender independently verified the exact r02 archive and internal hashes,
compared packaged sources, and closed its requested findings at12:27:49EST.
No further source changes or expanded tests are requested. This is source-review
acceptance only; shared import/installation/promotion and Smith's human
acceptance remain separate. Physical booking/playback is still unapproved.
The substantive disposition is retained in results/voice-r02/owner-review.json.
