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

## Interpretation guardrails

- Music is live synthesis from the original IMF/OPL event streams, translated
  to nine standard VDP oscillator channels; SFX are uploaded PCM on channels
  0-2.  A failure near SFX loading may therefore involve overlapping audio
  command traffic, but that is a hypothesis, not a conclusion.
- A MOS return and a hard unresponsive state are distinct outcomes until the
  last observed ownership boundary proves otherwise.
- A successful warm retry does not clear the defect and must not replace the
  first failing trace.
