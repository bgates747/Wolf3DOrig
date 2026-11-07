# Correct the full-game diagnostic's held-turn seam

Actual Oryx358 with corrected owned package storage completed250 real game
submissions, normal MOS return, three valid WPF1 blocks115/120/15,250 native
joins, zero discarded samples, timer retired, equal entry/exit SP and native
INFO17 margins2120/1780. All47 retrieved hashes verified; normal release before
analysis. Frontend0/fault counters0. The original harness verdict stays FAIL:
its required changing-heading assertion correctly rejected one static heading.
No physical performance conclusion is selected.

Source finding: private wp_test_steer writes w3d_controls after the outer
foreground poll, but ordinary w3d_sample_controls reconstructs that value from
w3d_keyboard_masks before each physics step. Thus it never creates a held key.
Correct only the disposable guest to latch Left-arrow bit1 at keyboard byte3
on EVERY w3d_poll_keys entry, including fixed-step catch-up polls. Reuse actual
keyboard sampling, normal physics, actors, renderer and profiler. Preserve
250-submission drain-and-return, two INFO17 calls, source/module/storage pins.
No direct pose edits, shipping input change, native mock or new pause/cap.

Build a distinct hardware-guest04 under normal finite Pi FIFO. Require actual
linked call at w3d_poll_keys and actual ldHL/memorySET sequence at wp_test_steer;
retain original private control-mask mistake as a rejection control. Run six
existing packet/ownership/result checks against04. Qualify once, stop children,
release/notify next. Then ONE separately frozen Alexe04 case via normal Oryx
FIFO: same runtime/firmware/module/assets/250frame/300s bounds/guards/cleanup,
now require >20 distinct recorded degree headings, changing scene capture,
valid WPF native joins and clean completion. No runtime rebuild or physical
contact; original358 evidence/result stays unchanged.

Compiler473 PASS19.52s: actual guest322539bytes SHA96d6e7d4fce6a1f357b55d862ee75ebcbe9eee1dcdf37438229c29f3d5d21d84.
All seven checks pass, including actual poll CALL/latch operands and old-seam
rejection. Same size/module/storage as03; shipping game source unchanged from
its storage correction. All owned children joined, compiler released normally.
Run04 is now selected with that exact guest and the unchanged original bound.

Admission note: first04 checkout refused while VDPlet359 still held Oryx.
A local shell command sequence erroneously continued copying into Wolf's own
separate unexecuted profile and ran prepare despite that refusal. It launched
no emulator and touched no peer profile. Subsequent dependent commands use
fail-closed sequencing. After actual359 release, fresh whole-host idle and
actual360 checkout/assert passed; the original runner rehashed all28 inputs
before its first/only child. Original admission refusal is distinct from the
actual run. Future prepare now requires/asserts the actual lease too, before
copying runtime files. This local guard change is not applied to running360;
its exact original pinned runner remains preserved.
