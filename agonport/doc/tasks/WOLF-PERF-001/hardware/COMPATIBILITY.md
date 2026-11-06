# Olimex first-cohort readiness

Reservation 4361fc8e2b3d remains ungranted. This assessment uses retained files
and source, not contact with the occupied bench. The first cohort admits only
the verified incoming Legacy CLI, native mode 0, and the five exact component
identities supplied by Extender and frozen in `freeze.json`. No firmware,
startup, routing or listener replacement is part of this scope.

## Installed runtime and mandatory admission

The retained Wolf r2 diagnostic image is 1,094,512 bytes, SHA-256
`8ade1e7dbc8b82cfbb20bfc92bdeb02e909c38c9f93c37723f9c9d409a9af7c4`.
The local `vdp-diagnostic-r2.bin` hashes exactly to that value. Extender's
expected restoration is the corresponding original full flash `17caa5b0…`.
The preserved November 1 physical trace records INFO0 value 256, INFO1 value
287 (0x011f), successful module LOAD and direct-row renders. Discovery IDENT
also carries capabilities: **0x011f is not INFO0's runtime identity**.

The retained source snapshot supports ABI 1.6 colour-row host services, INFO0
0x0100, capability subset 0x0101 and READ16. Its ABI typedef layouts through
the colour-row extension are compared with the SDK header used by the task.
Loader limit declarations are 65,536 text / 16,384 data / 2,048 stack /
131,072 image. The candidate declares those limits and actually links 13,572
text / 9,732 data, in a 19,124-byte package, SHA-256
`27f3d39285a5b49fec8aeed35085b1916ef537154f1d1d53956b075e00174c82`.
It adds local CCOUNT/PRID reads and ordinary buffer access; no new runtime API.

The snapshot's current ELF does **not** reproduce the installed image's
historical embedded ELF identity. Header/source comparison is supporting
evidence, not an assertion of exact source reproduction or fresh capability
discovery. Actual physical admission still requires the unchanged application's
discovery, INFO0==0x0100, INFO1 mask 0x0101, empty-slot, successful LOAD and
typed CONFIG/warm-up/RUN results. Native module service-accessor guards check
the host's ABI/structure/capability before use. Any incompatibility or fit error
stops the suite; it does not select a firmware replacement. The coordinator
binds the captured INFO replies and module build 0x20261104 to the invocation.

## EMOS binding

The expected corrected Eirene ROM is
`f62eed7f6bab8c164dcfe5e700132d289d52352f19d955acccbe1cff81b5e893`.
The task uses public MOS APIs 0x1d for callback ownership, 0x40/0x41 for the
native mode-information fence, 0x08 for sysvars and 0x14 for PRT vector exchange.
It does not install a callback through Arthur's private address. Eirene's
documented screen-mode byte 0x0bc349 is used only by explicit SAVE scripts.

Eirene's retained source forwards exactly ten-byte VDPL/P3DR records to the
callback in Legacy. Every task transaction uses that ten-byte VDPL form.
Native-log extraction uses **READ16 operation 5**, not sixteen-byte READ8.
Its offset is a four-byte little-endian field and the return is a u16 VALUE.
The native mode-reply fence remains before callback installation/discovery.

## Setup-only R07 adaptation

R06's complete measured fixture body and native module are retained unchanged.
R07 adds a task-copy check for an already active mode 136 and an explicit
240-MOS-tick settling wait after confirmed selection, before asset loading and
all timing. This satisfies appliance mode/settling requirements without moving
the measured boundaries. The first physical cohort starts from verified native
mode 0; the application restores mode 0. The coordinator verifies that actual
native byte after every case and at handback, rather than using P4 display state.

Pi compile generation 67 completed and was released. One bounded headless CPU
smoke passed under Oryx generation 279, with normal MOS return; that lease was
released after retrieval and fresh idle evidence. This checks the setup seam,
not hardware compatibility or a new rendering result. R06's original harness
and source are preserved with its evidence, and the new native package hash
is unchanged. No physical access has occurred during preparation.

## Calibration and diagnostic overhead

There is no prepared independent native-video/camera capture. P4 browser video
is a different output; whole-application host elapsed includes startup, readout
and SD writes. Neither will be used as an optical or calibrated denominator.
This cohort retains raw PRT/MOS/CCOUNT, matching completions, both revolutions,
coalescing and nominal rates. Absolute calibrated speed, physical clock MHz
and optical presentation timing remain pending. No new capture hardware,
firmware instrumentation or human optical-review appointment is selected.

The r2 diagnostic logs VDPL_RX/TX for RUNs as demonstrated by its retained
physical trace. End-to-end measurements therefore describe this diagnostic
runtime and include its logging cost. They cannot be relabeled production
Wolf FPS or pooled as a matched-runtime comparison with Rally's temporary a50
image. The local renderer brackets exclude surrounding RX/TX print calls, but
retain service/preemption costs. Firmware remains unchanged under this slot.
