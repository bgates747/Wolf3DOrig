# Wolf3DOrig VDPlet UART observer readiness

This freezes one diagnostic successor to the generation-57 transport stall.
The Author lifted the Oryx shutdown hold on 2026-11-01 and authorized stopped
profile staging. This document still does not authorize an Oryx process, FIFO
reservation, emulator launch, automatic input, or repair claim.

## Evidence boundary

The second generation-57 run stopped during a valid buffered load for buffer
`0x1001` (`wall_001`). Its 4,096-byte payload header was complete, followed by
333 correct RGBA2222 bytes. The next unsent asset byte is `0xea`. More than one
second apart, two live snapshots had identical ingress, delivered/reply, and
console sizes although the frontend and emulated VDP continued running. The
module had not opened, and all captured asset bytes match the generated file.

This establishes sender nonprogress during a valid texture payload. It does
not establish a blocked host call, CTS state, FIFO state, receiver state, IRQ
state, PC, or cause.

## Frozen cohort

The accepted profile remains untouched at
`/home/smith/Agon/mystuff/Wolf3dOrig/.emulator/wolf3d-vdplet-app`. The observer
profile is separately named
`/home/smith/Agon/mystuff/Wolf3dOrig/.emulator/wolf3d-vdplet-app-observed-r01`.
Application, module, assets, MOS, firmware, backend, launcher policy, and user
input remain identical. The only declared changes are:

- host frontend `f7951314...` to sealed FX-114 r02
  `7e7d0e1bc89af72bde7ffbd6c06446aaefda4d1803f89eb1faf3167307ee1e01`
  (1,954,496 bytes);
- one child environment variable,
  `FLEXE_UART_OBSERVER_OUTPUT=/home/smith/Agon/mystuff/Wolf3dOrig/agonport/emulator/evidence/uart-observer-r01/wolf3d-uart-observer.jsonl`.

The stage helper refuses an existing record, verifies the observer frontend and
reader hashes, prepares only a stopped profile, and never launches it. The
ordinary preparation path retains the accepted profile name and frontend.

Stopped staging completed on 2026-11-01. The durable receipt is
`wolf3d-vdplet-uart-observer-staging.json`. A fresh canonical whole-host
inspection reported no emulator process. The staged 73-entry runtime manifest,
wrapper, application, module, backend, firmware, MOS, reader, autoexec, and
fresh absent JSONL path were independently verified. No FIFO request or process
was created.

The observer contract is `fx114-sender-v1`: 50,000 ms stasis trigger, 100 ms
poll, samples at 0/250/500 ms, 630,000 ms maximum lifetime, and at most five
JSONL lines. The offline reader is pinned to
`12817411df487931407d1ec7cf4e51c9742a5f350582af2efce5db3fb4a96cde`.
MOS is pinned to release v3.0.2 (`d5642432...`) with map `d69e60bb...`.
The display font used here is embedded in the maintained backend and is
therefore frozen by backend identity `0866265b...`; there is no separate font
file in this profile or application package.

## Deferred execution

When Oryx returns, first stage the stopped cohort:

```bash
.venv/bin/python src/asm/wolf3d_vdplet_app/scripts/stage_observer_oryx.py
```

After a separate self-service FIFO checkout and fresh whole-host idle proof,
the human-visible command is:

```bash
cd /home/smith/Agon/mystuff/Wolf3dOrig/.emulator/wolf3d-vdplet-app-observed-r01
./flexe-agon-emulator
```

GUI startup and reproduction input remain manual because no exact deterministic
input driver has been admitted for this history. Do not retry automatically.
The later manual review has a 180-second whole-session ceiling. The Author
launches and closes the GUI. No keys are pressed during asset loading. If
visible loading stalls, leave the process open at least 55 seconds after its
last progress so the fixed 50.5-second observation window can finish. If the
scene loads, observe it briefly without gameplay input and close normally. At
180 seconds the Wolf custodian requests closure and reports an overrun; elapsed
time alone never authorizes forced teardown.

Wolf3DOrig retains the FIFO lease during review. On completion it preserves the
first JSONL and existing UART/console/frame/stats evidence, runs the pinned
reader using the project environment:

```bash
/home/smith/Agon/mystuff/Wolf3dOrig/.venv/bin/python \
  /home/smith/Agon/mystuff/flexe-agon-emulator/build/fx114/contract-r02/read_record.py \
  /home/smith/Agon/mystuff/Wolf3dOrig/agonport/emulator/evidence/uart-observer-r01/wolf3d-uart-observer.jsonl
```

It then proves the whole host idle, releases, and immediately notifies the next
FIFO owner. The observer's 630-second reader lifetime does not stop the emulator
and is not the session deadline.

The three valid result classes are: a reproduced stall with a complete window;
functional progress or changed timing with a finalized record; or an incomplete
record. None alone proves CTS/FIFO/IRQ/PC state or a repair. No timeout,
block-size, pacing, firmware, backend, payload, or consumer change belongs in
this cohort.

## Generation-64 result

The Author launched the frozen observer profile manually under Oryx FIFO
generation 64. The complete application loaded, entered playable E1L1, accepted
gameplay input, and exited cleanly to MOS. The finalized observer record is a
valid shutdown record with zero stall samples: its sender completed 2,086,850
bytes in 134.669 seconds, ended in `returned_cts` with CTS true, and recorded no
50-second completed-send stasis window. This run therefore did not reproduce
the generation-57 startup transport failure. It does not prove a transport
repair or any CTS, FIFO, interrupt, or PC cause.

The delivered stream contains 2,578 `VDPL` record signatures and the client
stream contains 2,577 VDPlet-selector signatures, approximately 19.1 per
second over the whole session. The same client capture contains 440 raw audio-
selector signatures. During the
playable review the Author heard conspicuously late gunshot, door, and pickup
effects. The eZ80 audio path requests effects inside each 30 Hz simulation
quantum and flushes the newest accepted batch before subsequent render
submission. These untimestamped raw counts establish neither individual
command boundaries nor maximum native-call, parser-queue, or audio-delivery
latency; their roughly 52 ms mean interval cannot exclude long renderer or
serialized-queue outliers. This run did not carry the Flexe audio producer/
delivery/SDL queue instrumentation, so the latency is recorded as a separate
audio defect rather than attributed to the game, VDPlet renderer, firmware
mixer, or host audio queue.

Evidence is retained outside Git under
`agonport/emulator/evidence/uart-observer-r01/gen64/`. The observer JSONL SHA-256
is `e4a525a722aeaa98f0ed18d3930b2079ba31add56a9476d0d196d9608aad0133`.
Oryx was freshly observed idle, the lease was released normally, and the next
FIFO owner was steered immediately.
