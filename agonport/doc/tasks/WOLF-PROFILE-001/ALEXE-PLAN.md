# Agon Lexe native-profiler check

Smith directly selects Oryx/Alexe after the blocked101 hardware attempt.
Alexe means Agon Lexe, formerly Flexe; local executable names remain `flexe`
until its cutover completes. This run does not rename or rebuild the emulator,
resume the old optimization goal, or contact Olimex/P4 hardware.

One fresh isolated headless profile, one original300s completion bound, stop on
first failure with no automatic replay. Use the previously qualified FX153
frontend c987fafc and backend0866265b through the real `flexe-agon-emulator`
wrapper, selected JIT engine, pinned stock MOS3.0.2 image/map, dummy SDL video
and audio, and existing input/capture helper7d9f52a7. Copy the exact native
firmware7593b9cf and its matched ELF092bacc3, the real full-game profiling guest
fda77dfd and22572-byte module8d3d. No synthetic native provider, added cue hold,
actor suppression or source/algorithm/pacing change. Normal populated floor0,
held turn and250-submission exit are the already frozen diagnostic guest.

Copy the same validated assets into a new private SD directory, with fresh
CRLF startup invoking that guest through the supported `runbin ./wolf3d.bin`
path. Hash all runtime, source, firmware, module, guest, launcher, startup and
asset inputs before and after execution. The ordinary game saves its own
wolf3d.cfg at exit; record that expected mutable output's before/after hashes
separately. All other selected inputs must remain unchanged. Never overwrite a
prior profile/run.

Require actual firmware boot and guest entry, DONE status0/timer retired/equal
entry-exit SP/two native INFO17>=512B,250 completed real-native-joined WPF1
records/zero dropped attempts/multiple disk blocks, changing headings and
normal game/MOS return. Preserve frontend/UART/wire/backend statistics and
sparse captures. Reject native emulator fault counters and incomplete output.
The timed renderer and physical pipeline are not replaced by a host-source
bridge. This can check firmware execution and collector integration in Alexe;
it does not emulate P4 readiness/reset wiring or establish physical admission.

Normal Oryx FIFO/fresh empty-host checkout/assert-before-child. Boost staysOFF,
80C thermal guard and512MiB available-RAM floor at least once per second.
Whole tranche900s including preparation, original300s run and owned cleanup.
Normal quit first, then bounded termination of only this child process group
if necessary; all owned children join. Retrieve/hash evidence and take fresh
whole-host idle proof, then normalrelease/immediateactualnext notification
before offline analysis. No installation, shared profile mutation, physical
firmware operation or new emulator repair follows a failure automatically.
