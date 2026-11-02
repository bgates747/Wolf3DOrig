# Frozen plan: corrected late-window Pi-only preparation

This task prepares source and artifact selection for one possible corrected
late host-ring observation. It performs no emulator, audio, Oryx, staging,
build, reservation, hardware, or publication action. A later target profile or
run requires separate central selection.

## Exact retained inputs

- Corrected observer backend
  `943f432fecb96689f3a0d2ae80c72d08e20903dfe2a58a00ba88d8c7727ad400`
  is selected from the independently accepted corrected startup-profile receipt.
- Application `5723cd60...`, module `12449bab...`, frontend `7e7d0e1b...`,
  firmware `8d980025...`, matching ELF `1a7c4448...`, MOS `d5642432...`, media,
  helper source/binary `215bd248...`/`7d9f52a...`, reader `584e9d2a...`, oracle
  `ea4f7e64...`, and finite late-window runner `f0ffe798...` remain unchanged.
- Existing accepted receipts are inputs, not profiles to modify. The old
  generation-71 result and its initialization-race limitation, and corrected
  startup generation-75 evidence, remain immutable.

## Proposed late-window semantics

The proposed private window is actual observer SETUP+90 through +100 seconds.
It retains the original runner's title/four-Enter sequence, structural gameplay
readiness by 85 seconds, one real Space pair at 92 seconds, Escape at 103
seconds, farewell/MOS by 150 seconds, 15-second normal exit, 180-second whole
ceiling, bounded finalization/reader waits, and owned cleanup reserve.

Eligibility requires complete valid observer and reader output, actual overlap
between the saved Space write bracket and the actual observer window, structural
gameplay success, finalization, and normal cleanup. It does not require startup
`produced_before=0` or depth zero; samples already present at the late-window
entrance remain explicitly left-censored. Missing overlap, incomplete output,
cap/error, timeout, or forced cleanup is terminal with no retry, alternate
offset, or successor.

## Differences

Relative to the accepted startup preparation, only the proposed profile/output
identity, window offset (`0` to `90000` ms), and eligibility mode (expected
non-overlap plus empty-history witness to required overlap without an empty-
history gate) change. The corrected backend and all application/runtime inputs
remain the same.

Relative to the old late `r02` preparation, only the proposed profile/output
identity and observer backend (`0f4bdc1b...` to corrected `943f432f...`) change.
The original late runner, oracle, offset, input timing, overlap requirement,
functional gates, and finite supervision remain exact.

Any later result may report only actual known-sample residence, censored counts,
fills, drops, depth, and window completeness. It cannot establish a repair,
matched baseline, shot-sample identity, command/parser/mixer/device/DAC/speaker
delay, or total audible latency.
