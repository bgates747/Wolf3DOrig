# Correct the disposable stack query after actual Alexe353

The direct Author-selected Alexe run booted native7593, loaded real module8d3d,
then emitted VDPL operation0/field17 and received ERROR status9. Source pins
confirm INFO is operation4. This is a consumer test-guest encoding mistake;
the earlier packet qualification checked the package operands and two query
call sites but missed this opcode. The ordinary shipping profiler's own INFO/
READ16 implementation is separate and unchanged. Original hardware101 never
reached this packet because it stopped before guest LOAD/RUN.

Original Alexe353 ended by a normal owned Quit after observing that error;
runner's Unexpected-emulator-exit error records that manual stop, not a crash.
Frontend0/backend fault counters0, zero completed profiler records. All75
retrieved hashes verify and353 was released22:14:36UTC; actualnext VDPlet321c
was immediately notified. Original guest/profile/logs remain unchanged.

Build a separate hardware-guest02 with the shared query packet using named
protocol/INFO constants and globally identifiable packet labels. Require its
actual13 emitted bytes to equal `17 00 D8 08 00 01 04 00 00 01 00 11 00`.
Require same size and exactly one binary byte different from original fda77:
operation0→4. Verify that changing this byte back rejects the binary even when
package-size/call-count checks still pass. Run focused offline host/producer
checks under normal Pi FIFO; preserve original failures and outputs.

Then rejoin the Oryx FIFO with one separate Alexe02 profile and the same exact
runtime/firmware/ELF/module/assets/250-frame game test/300s bound/guards/cleanup
as ALEXE-PLAN. This is a concrete source correction under Smith's request to
try the profiler in Alexe, not a blind replay or emulator/firmware change. The
runner will stop promptly on an actual VDPL error rather than waiting for DONE.
No physical hardware contact or optimization-goal resumption is selected.
