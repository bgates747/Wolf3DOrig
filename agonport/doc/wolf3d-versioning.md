# Wolf3DOrig version and compatibility contract

Wolf3DOrig deliberately versions four things independently:

- upstream Agon VDP firmware;
- the Wolf3DOrig VDP extension;
- the Wolf3DOrig eZ80 application;
- the application/renderer wire ABI.

The first release using this contract identifies the application and Wolf VDP
extension as `0.1.0 Alpha 1`. The inherited upstream firmware is `2.16.0`.
Matching semantic versions are useful provenance, but they are not the runtime
compatibility rule. The wire ABI begins at `1.0`.

## Boot branding

A combined firmware retains all upstream identity and appends each installed
extension on its own line:

```text
Agon Platform VDP Version 2.16.0 Bistromathics
Pingo 0.1.0 Alpha 1
Wolf3DOrig 0.1.0 Alpha 1
```

The standalone Wolf firmware uses the same upstream and Wolf3DOrig lines. The
eZ80 program identifies itself as `Wolf3DOrig App 0.1.0 Alpha 1` so application
and renderer releases remain unambiguous even when their versions happen to
coincide.

## Payload-free version query

The implemented client query sends this buffered Wolf3D command:

```text
23,0,A0h, bufferId:u16le, 4Ah, 40
```

Subcommand 40 carries no payload. That does not make the command compatible
with a VDP that lacks the custom Wolf parser; it merely avoids leaving arbitrary
payload bytes in an older stream parser. This compatibility check is a contract
for consumers of Wolf3DOrig-aware custom firmware.

The VDP replies through the standard keycode callback packet with this 20-byte
payload:

| Offset | Size | Meaning |
|---:|---:|---|
| 0 | 4 | ASCII `W3DV` |
| 4 | 1 | reply schema, currently 1 |
| 5 | 1 | wire ABI major |
| 6 | 1 | wire ABI minor |
| 7 | 2 | capability bits, little-endian |
| 9 | 3 | Wolf VDP semantic major/minor/patch |
| 12 | 1 | prerelease kind: 0 release, 1 alpha |
| 13 | 1 | prerelease number |
| 14 | 3 | upstream VDP major/minor/patch |
| 17 | 1 | reserved, must be zero |
| 18 | 2 | fixed completion cookie `A55Ah`, little-endian |

The fixed cookie detects a complete response without requiring request payload.
The callback consumes W3DV packets so MOS cannot mistake them for keyboard
events.

## Capabilities and acceptance

ABI 1.0 defines these capability bits:

| Bit | Capability |
|---:|---|
| 0 | world renderer |
| 1 | actors |
| 2 | HUD and view weapon |
| 3 | asynchronous rendering |
| 4 | death fizzle |
| 5 | inherited Enhanced Audio API |

The current client requires all six. It accepts a renderer only when:

- the response schema, reserved byte, and completion cookie are valid;
- the ABI major equals the required major;
- the ABI minor is at least the required minor;
- every required capability bit is present.

Wolf extension and upstream semantic versions are recorded for diagnosis but
are not equality gates. Thus compatible future ABI minors pass, while a missing
feature fails even if semantic versions happen to match.

When enabled, the client waits one second (120 MOS ticks). A timeout, malformed reply, or
incompatible ABI produces a readable diagnostic, waits for acknowledgment,
restores the caller's original single-buffered display mode, clears the screen,
and returns to MOS.

## Temporary shipping deferral

The first end-to-end emulator attempt exposed a transport seam not covered by
the native VDP or direct-eZ80 tests: the custom VDP receives subcommand 40, but
the application does not accept the W3DV reply through the real MOS keycode
callback path and therefore reports a false incompatibility. The startup call
site is commented out for the current build at the Author's request so the
otherwise working game can ship tonight. The responder, client parser, failure
UI, and automated unit regressions remain intact.

Before reenabling the gate, add a minimal emulator fixture that records the raw
callback bytes to an SD mailbox, compare them with the intended 20-byte W3DV
packet, repair the callback transport or parsing mismatch, and validate both a
successful custom-VDP startup and a clean stock-VDP timeout.

## Release traceability

Application and VDP tags evolve independently. The initial tag forms are:

```text
wolf3dorig-app-v0.1.0-alpha.1
wolf3dorig-vdp-v0.1.0-alpha.1
```

Release notes must record the tested counterpart commit hash and wire ABI. A
tag does not imply that future application and renderer semantic versions must
remain numerically synchronized.

## Regression obligations

The VDP native smoke test verifies the exact W3DV response. The real-eZ80 death
regression includes production callback and validator code and covers a valid
record, a future compatible minor, semantically different renderer versions,
missing capabilities, wrong ABI major, malformed schema, and callback packet
consumption. Emulator release validation must additionally exercise both a
successful startup and the visible timeout/error path with incompatible
firmware.
