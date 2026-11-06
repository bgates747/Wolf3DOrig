# Initial headless qualification: r04 / native02 / q01

Task plan frozen and pushed as5599f43. No graphical launch or physical device.
Oryx FIFO request089fb1ff77db; actual fresh idle checkout/assert still required.
Pi builds141/142 finished and released; successor143 notified immediately.

Run at most eight processes, sequentially, each with300-second bound:

| Order | Backend | Arm |
| --- | --- | --- |
|1|bespoke|cpu|
|2|vdplet|cpu|
|3|bespoke|unpaced|
|4|vdplet|unpaced|
|5|bespoke|paced, diagnostic framebuffer captures|
|6|vdplet|paced, diagnostic framebuffer captures|
|7|bespoke|intentional owned-timer abort|
|8|vdplet|intentional owned-timer abort|

Stop on first unexpected failure. Do not promote partial runs. Invoke each
profile's own generated Flexe wrapper, fresh result files only; assert actual
Oryx ownership before each launch. Require normal guest teardown and actual MOS
return (or the specific intentional restored-timer failure marker), ordinary
SDL Quit, joined backend children and zero backend faults. After retrieval/hash
and fresh whole-host idle inspection, release/notify before analysis. Necessary
fixes use a new identified preparation/qualification revision and FIFO request.

Both firmware inputs are newly built task copies, not firmware installed on a
board. Source/dependency receipts: build/r04/inputs.json and native02-inputs.json.
Build/output hashes: build/r04/native02-build.json, guest-build.json and each
payload/expected.json. Harness freeze is build/r04/qualify-freeze.json. Native
BIN A685cba92 and B7593b9cf; ELF Ac192bb13/B092bacc3. Graphics exactlyac2dd598
in both; standard240MHz configuration is metadata, not measured calibration.
The safe SDK module is1907ce17,19876bytes, cap257/minor6. Preserve compiler
Os/PIC/manual-helper versus O2/builtin/layout and Canvas versus direct-row
implementation differences. New module-only brackets cannot substitute for the
added native fully-received-command bracket.

PF3 guest schema retains PERF-001 fields, with backend1/2 in header byte32.
Native WPN1 stores index/angle/draw/scope/dispatch: A scope equals its complete
draw/drain; B scope includes row acquisition/end, and native instrumentation
replaces the final word after invoke return. This broader B interval includes
module record bookkeeping but excludes UART reply formatting/transmission.
All counters are raw/nominal pending clock qualification. Capture-enabled
qualification timings are perturbed; use only the later capture-free matched
cohort for performance comparison. No physical or ordinary-game FPS claim.
