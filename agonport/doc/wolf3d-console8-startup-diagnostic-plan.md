# Console8 intermittent startup diagnostic

## Trigger

The production VDPlet-direct candidate at commit `2262783` is repeatably
playable once started on Console8, but two intermittent failures remain:

- an automatic attract-loop advance returned to MOS before Episode selection;
- a later run became unresponsive while loading SFX after Episode selection.

The Console8 SD card contains no application postmortem.  Diagnosis therefore
uses the Olimex Extender bench with live VDP serial evidence rather than
speculative retries on the user device.

## Frozen incoming candidate

- application: `wolf3d.bin`, 286,521 bytes, SHA-256
  `10ca8312defa10857fa768de54f216ed1655d754d7496f47bcd24bf690f3a69d`;
- VDPlet module: `wolf3d.vdpl`, 18,636 bytes, SHA-256
  `266f809ff76e56733251da202e5c4747cd9c12d247d799d486471a262c0404b7`;
- native VDP candidate: SHA-256
  `a50eb23acf6b3edfb44d3c1bb44858a213be696d68c06a696da7767170ac6f9a`;
- package: the standard-map `pause-resume` acceptance deployment, with no
  diagnostic map and no `autoexec.txt` change.

## Diagnostic build

Prepare a separate, clearly named diagnostic candidate.  Preserve game logic,
asset bytes, timing, music/SFX policy, normal startup, and the VDPlet module.
Add only bounded breadcrumbs at these ownership boundaries:

1. application shell entry and each sign-on/PG13/title/menu handoff;
2. Episode/Difficulty acceptance and level-load phase entry;
3. SFX container open, each sample definition and buffered-command install,
   and final SFX-load completion;
4. video-mode fence, VDPlet discovery/load/run, first prepare/render request,
   and every failure/teardown route;
5. VDP parser receipt and completion for mode, audio, buffer, discovery, and
   VDPlet selectors, emitted only to the VDP USB diagnostic serial stream.

The first candidate deliberately retains the exact accepted native VDP.  Its
existing `BUFFERED_DEBUG_INFO` command already produces an unconditional USB
serial line, so the application emits reserved `D0xx` lifecycle IDs and
`D1xx` finalized-SFX IDs through that command.  This localizes the last good
application-to-VDP boundary without first introducing a second firmware
variable.  Use `scripts/decode_startup_trace.py` on the captured serial log.
Only if that evidence ends inside an indivisible VDP operation should the
next candidate add parser-internal firmware breadcrumbs.

Breadcrumbs must be fixed-size or rate-bounded and must not add waits to the
production wire path.  Preserve the uninstrumented candidate for A/B testing.

## Finite physical run

After an explicit Olimex lease grant and fresh Extender handoff:

1. preserve the incoming firmware, startup file, current directory, modes,
   listener state, and resource ownership exactly as the bench grant records;
2. install the diagnostic native VDP and standard-map diagnostic application;
3. open one VDP serial reader before launch and retain its raw timestamped log;
4. perform at most six cold application starts, covering both unattended
   attract advance and direct key-through to Episode/Difficulty;
5. stop on the first reproduced unexpected exit, lockup, parser fault, or
   incomplete asset load; do not retry an uncertain operation;
6. if no fault reproduces, run one music-disabled-during-asset-load A/B only
   after freezing that derivative and its exact hashes;
7. exit listeners/readers, restore or explicitly adopt the agreed native VDP,
   restore normal CLI/input and every preserved component, collect fresh idle
   evidence, release the lease, and notify Extender plus the next waiter.

No graphical emulator is launched by this task.  The SD card is never
unmounted.  No startup file is changed.

## 2026-11-03 allocation-order result

The valid physical r13 experiment used the required `vdplet-direct` backend
and the production module above. Its diagnostic application is
`diagnostic-r13-wolf3d.bin`, SHA-256
`7782aa718a5b0c2bafdb0d00d6ad3d4a1d9370937d47cad387308fef79b70045`.
Both application and module were read back byte-identical from
`/mystuff/wolfdiag/` before execution.

r13 selected mode 136 once, before music, shell, SFX, level buffers or VDPlet
allocation, then retained it for the process lifetime.  Its passive trace
reached `D00A/D00B` around that early selection, completed all asset loading,
reached `D06B/D06C` around VDPlet open/configuration, and reached `D06D` after
the first render submission.  This is a successful startup/render-boundary
result for the allocation-order mitigation.

The subsequent timeout was not the former startup failure.  The runner sent
Escape after `D06D`; Escape now enters the source-correct in-game control
panel.  That shell had not yet been converted from single-buffer assumptions,
so it remained on the hidden page and an IMF voice sustained while the runner
incorrectly waited for application-exit marker `D009`.  The follow-up keeps
mode 136, mirrors complete shell/intermission pages across both framebuffers,
and navigates the actual Quit confirmation in the runner.

Diagnostics r06 through r11 accidentally selected the standalone backend.
They are retained as evidence of the diagnostic-pipeline mistake but are
invalid for VDPlet behavior or root-cause conclusions.  The accepted Console8
failures plus valid r13 make early final-mode allocation a strong mitigation,
not definitive proof of the firmware trigger.

Golem received durable report
`2026-11-03_23-43-45_wolf3dorig_wolf-mode136-allocation-hardening-one` and
accepted generic task `VDPL-023`.  Its source review independently found
unchecked allocation/rollback gaps in the mode-change path.  Firmware
hardening and Wolf's consumer mitigation remain separate tasks; no additional
physical experiment was requested by Golem.

## r14 retained-surface candidate

The follow-up implementation is now assembly-qualified.  It keeps mode 136
for the process lifetime and makes complete shell, modal, high-score and
intermission states coherent on both framebuffer surfaces.  The gameplay hot
path is unchanged.  The exact production application is 288,634 bytes with
SHA-256
`ac8498fb834efa8bada84e74610d21092515bd9e83ada9e8e2a3f7a8656b9777`;
the exact 18,636-byte module has SHA-256
`266f809ff76e56733251da202e5c4747cd9c12d247d799d486471a262c0404b7`.

The focused shell, intermission and high-score fixtures assemble with hashes
`186bba23745c0ebd9464dfa753e00f3457a465fc91c468e7e89edcf768940441`,
`8a710ff58db92bafab8bfdd1176543d6e6e08f54215b36caa860b23d8f75e7fd`,
and `296ab4cbc5f3235f5069fb234eb70691079f83abacacaa148126a627793cc61c`.
They were not executed because the authorized Pi generation explicitly
excluded emulator and hardware work.  The next run must therefore remain a
bounded qualification: exact deployment and read-back, one startup through
`D06D`, visible Escape control panel, Down/Enter/Y quit confirmation, and
clean `D009` MOS return.  The user reset the prior target after the sustained
note; that reset ends r13 and is not evidence for or against r14.

### r14 physical result

The exact application/module pair was read back from the target with the
hashes above.  One bounded direct run reached `D06D` after completing all
startup, asset, VDPlet-open and first-render boundaries without an application
failure marker or reset.  It did not reach `D009`: the runner issued Enter only
about 262 ms after Down and `Y` only about 265 ms after Enter.  A retained-mode
menu action and the subsequent randomized confirmation each redraw both
surfaces, so those keys were not safely paced.  The result qualifies r14's
startup/render boundary but does not qualify its scripted Quit path.  The
runner now leaves one second after each redraw-triggering action; no second
physical run was made.

The exact incoming native VDP was restored and its entire retained 4 MiB image
verified with SHA-256
`17caa5b0b2ede84bb627e207f10994b13dd3abfa2d04fc807ec393414fe33378`.
A fresh listener start/status/EXIT proved the restored actual CLI.  The bench
was returned neutral, listener-offline and holder-free, then released to the
Golem waiter.  Evidence is rooted at `physical-r01/r14-direct-01/` and
`physical-r01/r14-release-observation.json`.

Automated retained-page semantics were subsequently qualified on Oryx
generation 239.  The production shell passes 756/756 checks, intermission
154/154, and high scores 62/62.  The only corrections found were stale fixture
assumptions: semantic text counts must ignore the replayed physical page, and
complete ordinary/secret intermission reconstructions include BJ's portrait
as plot 36/21.  Exact logs and runtime identities are preserved in
`agonport/emulator/evidence/mode136-retained-ui-g239/`.  A human visual review
is still required before claiming the retained-page presentation accepted.

## Interpretation guardrails

- Music is live synthesis from the original IMF/OPL event streams, translated
  to nine standard VDP oscillator channels; SFX are uploaded PCM on channels
  0-2.  A failure near SFX loading may therefore involve overlapping audio
  command traffic, but that is a hypothesis, not a conclusion.
- A MOS return and a hard unresponsive state are distinct outcomes until the
  last observed ownership boundary proves otherwise.
- A successful warm retry does not clear the defect and must not replace the
  first failing trace.
