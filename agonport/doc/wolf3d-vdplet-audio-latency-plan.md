# Wolf3DOrig VDPlet audio-latency diagnostic plan

Status: source analysis complete; bounded Flexe preparation accepted on
2026-11-01. This document authorizes no Wolf build or source change, Oryx
request, emulator process, firmware change, sample-rate change, queue-size
change, pacing change, audio drop policy, or repair.

## Observed defect and present boundary

The generation-64 production-VDPlet review loaded successfully, was playable,
and exited cleanly. The Author heard conspicuous gaps between gameplay events
and their effects, including gunshots, doors, and pickups. The FX-114 sender
observer finalized normally with no startup-stasis window. Audio latency is a
separate defect.

Wolf gameplay creates requests inside each 30 Hz fixed simulation quantum and
flushes the newest accepted batch after the simulation batch, independently of
render completion. Runtime buffered playback emits a six-byte command-buffer
call followed by a six-byte gain command. This source path makes late request
creation less likely, but does not measure when bytes cross the UART, when the
VDP parser executes the stored procedure, when PCM appears, or when the host
delivers it.

Generation-64 raw streams are untimestamped. Counts of VDPlet or audio-selector
byte signatures do not establish parsed-command boundaries, maximum native-call
duration, serialized parser backlog, PCM onset, SDL queue depth, or audible
latency. The roughly 19.1 VDPlet signatures per whole-session second is an
average and cannot exclude long outliers.

## Cohort separation

The existing Flexe audio work is useful instrumentation precedent, not a
matched Wolf result:

| Input | Wolf generation 64 | FX-067 / FX-106 family |
| --- | --- | --- |
| Frontend | `7e7d0e1b...` FX-114 sender observer | `7e78e991...` historical frontend |
| Backend | `0866265b...` current production backend | `928d32da...` audio-instrumented backend |
| Firmware | `8d980025...` current VDPlet/pixels firmware | `6e3e85da...` older stock audio fixture firmware |
| Guest | complete Wolf3DOrig app `5723cd60...` | eight-case audio qualification fixture `437d6390...` |
| Module | Wolf renderer `12449bab...` | audio fixture, no Wolf renderer |
| Host audio evidence | none beyond ordinary output | producer/ring/fill/DMA and SDL observer in armed arms |

FX-067 established that its matched normal-audio fixture produced PCM slower
than wall-clock demand and inserted explicit silence. FX-106 established only
that unarming capture did not produce a clear completion-time improvement; its
unarmed arm has no PCM/ring evidence. Neither result measures the current
Wolf event-to-audible path or proves the cause of the Author's report.

## Required measurement chain

A future diagnostic should retain the exact generation-64 application, module,
assets, MOS, VDP firmware, input semantics, audio commands, sample rates,
channels, renderer, and pacing. Diagnostic derivatives must be separately named
and their differences frozen before execution.

One bounded manual session should record a common monotonic host clock at these
boundaries:

1. SDL key-down admission for Space and Up Arrow. These give reproducible
   gunshot and door stimuli without inventing an automatic gameplay driver.
2. Complete eZ80-to-VDP admission of the corresponding buffered-call and gain
   bytes, with a framing-aware decoder. Raw byte-pattern matches inside payloads
   are not events.
3. VDP stream-parser execution of the command-buffer call and the contained
   reset/waveform/play operations.
4. First changed PCM attributable to that sample at the firmware producer/ring
   boundary, retaining fill/drop/depth and emulated DMA timing.
5. SDL callback request, exact delivered PCM range, stream queued bytes, actual
   source/destination/device formats, and device buffer metadata.

Every stage needs sequence numbers and timestamps sufficient to calculate:

- key admission to complete audio-call admission;
- UART admission to VDP parser execution;
- parser execution to first sample PCM;
- first produced PCM to SDL delivery; and
- SDL queued duration at delivery.

The physical sink after SDL remains outside automated proof. A simultaneous
human listening report can corroborate the measured run but cannot replace
the timestamps.

## Acceptance and stop rules

- Use the first valid gunshot and first valid door event after gameplay begins;
  pickups are corroborating observations, not required deterministic stimuli.
- Preserve all raw observations before analysis. Missing, capped, unmatched, or
  unfinalized stages are unavailable evidence, never zero latency.
- Do not infer latency from whole-session averages or completion duration.
- Do not change renderer cadence, UART chunking, audio rate, queue capacity,
  mixer gain, sample data, or drop/fill policy in the diagnostic cohort.
- A startup load stall remains a transport result and ends the session without
  being relabelled as audio evidence.
- One finite session, no automatic retry. Normal close, fresh whole-host idle
  proof, FIFO release, and immediate next-owner steering precede analysis.

The diagnostic should be coordinated with Golem and the Flexe owner because it
reuses the FX-067 producer/SDL observation concepts while adding Wolf-specific
input, parser, and command-boundary timing. No implementation begins until that
cross-project contract is accepted.

## Accepted first diagnostic preparation

Golem accepted Flexe's smallest first discriminator for preparation only in
`2026-11-01_15-02-02_golem_golem057-firststop-empty-audio-prep-onehundredfortythree.md`.
This deliberately measures less than the full chain proposed above:

1. Derive a private diagnostic backend from the exact production backend
   identity used by Wolf generation 64, with explicit source, object, build,
   schema, and reader provenance. It must not be relabelled as the historical
   FX-067/106 backend or an FX-119 transport candidate.
2. Arm one ten-host-second window holding at most 8,192 fixed-size metadata
   events and one MiB. Record producer and real-sample consumer range IDs,
   monotonic entry/exit brackets, ring depth before/after, fill, and the
   existing overflow/drop counters under the existing audio lock.
3. Preserve sample extraction, ordering, overflow, fill, playback forwarding,
   rates, and all audio content exactly. The cap stops observation only; it may
   not alter playback. No new locks, throttling, per-sample trace, client
   marker, firmware hook, queue policy, or repair is allowed.
4. Prove synthetic producer/consumer range, wrap, drop, fill, window-edge, cap,
   once-only forwarding, and unchanged-PCM behavior before any target staging.
5. Report only bounded host-ring residence and nominal queued duration. The
   result cannot establish gameplay-event-to-wire, parser-to-mixer,
   mixer-to-DMA, SDL/device, DAC, or speaker latency. Missing ranges, capture
   overrun, or incomplete finalization make the window incomplete rather than
   a pass.

Flexe owns this observer preparation. Wolf owns the application and any later
explicit client marker. Golem owns the shared runtime contract and will select
whether a finite Oryx execution is justified after preparation readiness. No
emulator reservation or execution has yet been authorized by this acceptance.

## Prepared finite consumer session

The source-only consumer proposal is frozen in
`2026-11-01_15-12-11_wolf3dorig_wolf-ring-consumer-plan-five.md`. It reuses the
existing SDL3 preload helper rather than adding an input framework. A future
selected run would retain real host audio, use dummy video only, traverse the
ordinary title/New Game/Episode 1/medium flow with injected SDL scancodes,
require loader and captured-HUD gameplay readiness, overlap one pistol input
with a fixed ten-second observer window, then use Escape and the normal VDPlet
unload/MOS-return path before stopping the owned frontend.

The proposed automation proves only that ordinary gameplay and an input
intended to request a pistol attack overlap the host-ring observation window.
Without an admitted client marker and downstream correspondence, it cannot
identify the shot's samples or measure event-to-sound latency. If Flexe cannot
preserve the real audio consumer while delaying its private fixed observation
window, use a stopped manual-Author session instead of changing Wolf. This
proposal authorizes no code, build, staging, reservation, Oryx contact, or run.

Golem's accepted clock clarification supersedes the proposal's shorthand
`T0`: the fixed 90,000 ms delay is measured from Flexe observer setup on
`CLOCK_MONOTONIC`, not from the runner's process-launch timestamp. A future
result must preserve the observer's exact absolute window start/end and the
runner's command-write monotonic brackets separately, then establish overlap
post hoc. The existing helper does not acknowledge key admission, so even a
command-write bracket inside the observer window proves only that the input
was queued then; it does not prove when SDL or the guest admitted it. Failed
readiness, missing absolute bounds, or absent overlap makes the one session
incomplete with no retry. No hidden clock marker, polling hook, or new clock
API is authorized.
